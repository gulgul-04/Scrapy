import pandas as pd
import json
import re
from pathlib import Path
from datetime import datetime, timedelta

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
CLEAN_CSV = DATA_DIR / "interim" / "cleaned_sowing_data.csv"
UPAG_JSON = DATA_DIR / "master_duration_dict.json"
FINAL_DATASET = DATA_DIR / "final_crop_calendar_dataset.csv"

MONTHS = {
    'jan': 1, 'january': 1, 'feb': 2, 'february': 2, 'mar': 3, 'march': 3,
    'apr': 4, 'april': 4, 'may': 5, 'jun': 6, 'june': 6, 'jul': 7, 'july': 7,
    'aug': 8, 'august': 8, 'sep': 9, 'september': 9, 'oct': 10, 'october': 10,
    'nov': 11, 'november': 11, 'dec': 12, 'december': 12
}

# Enhanced Global Synonym Map to solve structural names
CROP_SYNONYMS = {
    "paddy": "rice", "jhum paddy": "rice", "trcwrc paddy": "rice", "wrca\ntrc paddy": "rice", "wrc/trc paddy": "rice",
    "redgram": "tur", "red gram": "tur", "pigeonpea": "tur", "pigeon pea": "tur",
    "blackgram": "urad", "black gram": "urad", "greengram": "moong", "green gram": "moong",
    "bengalgram": "gram", "bengal gram": "gram", "chickpea": "gram",
    "jowar": "sorghum", "kh jowar": "sorghum", "bajra": "pearl millet",
    "mustard": "rapeseed & mustard", "rapeseeds": "rapeseed & mustard", "rapeseed": "rapeseed & mustard",
    "pulses\nspecify": "pulses", "pulses": "gram", "vegetables": "potato"
}

def clean_season_name(season_str):
    s = str(season_str).lower()
    if "kharif" in s or "pre" in s or "autumn" in s or "monsoon" in s: return "Kharif"
    if "rabi" in s: return "Rabi"
    if "summer" in s or "zaid" in s: return "Summer"
    return "Kharif"

def parse_sowing_string_to_days(date_str):
    date_str = str(date_str).lower().strip()
    found_months = []
    for m_name, m_num in MONTHS.items():
        if m_name in date_str:
            if not any(m_name in existing for existing in found_months):
                found_months.append((date_str.index(m_name), m_num))
    found_months.sort()
    months_in_order = [m[1] for m in found_months]
    if not months_in_order: return None, None
    start_month = months_in_order[0]
    end_month = months_in_order[-1]
    
    def get_day_estimate(text_chunk, is_end_date=False):
        numbers = re.findall(r'\b\d{1,2}\b', text_chunk)
        if numbers:
            day = int(numbers[0])
            if 1 <= day <= 31: return day
        if any(w in text_chunk for w in ['early', 'first', '1st', 'start', 'beginning']): return 5
        if any(w in text_chunk for w in ['mid', '2nd', '3rd', 'middle']): return 15
        if any(w in text_chunk for w in ['late', 'last', '4th', 'end']): return 25
        return 28 if is_end_date else 1

    split_str = re.split(r'\s+to\s+|-|–', date_str)
    start_chunk = split_str[0]
    end_chunk = split_str[-1] if len(split_str) > 1 else split_str[0]
    start_day = get_day_estimate(start_chunk, False)
    end_day = get_day_estimate(end_chunk, True)

    try:
        start_date = datetime(2023, start_month, min(start_day, 28))
        end_date = datetime(2023, end_month, min(end_day, 28))
        if end_date < start_date: end_date = datetime(2024, end_month, min(end_day, 28))
        return start_date.timetuple().tm_yday, end_date.timetuple().tm_yday
    except ValueError:
        return None, None

def parse_upag_harvest_window(harvest_strings):
    if not harvest_strings: return None, None
    all_doys = []
    for hw in harvest_strings:
        parts = str(hw).lower().split('-')
        for p in parts:
            p = p.strip()
            month_str = p[:3]
            day_str = ''.join(filter(str.isdigit, p))
            if month_str in MONTHS and day_str:
                all_doys.append(datetime(2023, MONTHS[month_str], min(int(day_str), 28)).timetuple().tm_yday)
    if not all_doys: return None, None
    all_doys.sort()
    if all_doys[-1] - all_doys[0] > 200:
        wrapped = [d + 365 if d < 180 else d for d in all_doys]
        wrapped.sort()
        return wrapped[0], wrapped[-1]
    return all_doys[0], all_doys[-1]

def day_to_date_string(day_of_year):
    if day_of_year is None: return ""
    if day_of_year > 365: day_of_year -= 365
    dt = datetime(2023, 1, 1) + timedelta(days=int(day_of_year) - 1)
    month_str = dt.strftime('%b')
    if dt.day <= 10: mod = "Early"
    elif dt.day <= 20: mod = "Mid"
    else: mod = "Late"
    return f"{mod}-{month_str}"

def build_national_fallback(master_dict):
    """Generates an agronomic map across all states for missing entries."""
    fallback = {}
    for state, crops in master_dict.items():
        for crop, seasons in crops.items():
            if crop not in fallback: fallback[crop] = {}
            for season, data in seasons.items():
                if season not in fallback[crop]: fallback[crop][season] = []
                fallback[crop][season].extend(data.get('upag_harvest_window', []))
    
    cleaned_fallback = {}
    for crop, seasons in fallback.items():
        cleaned_fallback[crop] = {}
        for season, windows in seasons.items():
            if windows:
                cleaned_fallback[crop][season] = list(set(windows))
    return cleaned_fallback

def build_final_dataset():
    print("[*] Loading Data Systems...")
    df = pd.read_csv(CLEAN_CSV)
    with open(UPAG_JSON, 'r', encoding='utf-8') as f:
        master_dict = json.load(f)
        
    national_fallback = build_national_fallback(master_dict)
    final_records = []
    
    for index, row in df.iterrows():
        state = str(row['State']).strip().title()
        district = str(row['District']).strip().title()
        orig_crop = str(row['Crop']).strip().replace('\n', ' ')
        orig_season = str(row['Season']).strip()
        raw_sowing = str(row['Sowing Window'])
        
        # Normalize keys for searching
        norm_crop = orig_crop.lower().strip()
        search_crop = CROP_SYNONYMS.get(norm_crop, norm_crop).title()
        search_season = clean_season_name(orig_season)
        
        sow_start_doy, sow_end_doy = parse_sowing_string_to_days(raw_sowing)
        harvest_strings = None
        
        # Step 1: Direct State-Crop Match
        if state in master_dict and search_crop in master_dict[state]:
            season_data = master_dict[state][search_crop].get(search_season)
            if not season_data and master_dict[state][search_crop]:
                season_data = list(master_dict[state][search_crop].values())[0]
            if season_data:
                harvest_strings = season_data.get('upag_harvest_window')
                
        # Step 2: National Fallback Mechanism (Solves Arunachal/sparse profiles)
        if (not harvest_strings) and (search_crop in national_fallback):
            harvest_strings = national_fallback[search_crop].get(search_season)
            if not harvest_strings and national_fallback[search_crop]:
                harvest_strings = list(national_fallback[search_crop].values())[0]
                
        harv_start_doy, harv_end_doy = parse_upag_harvest_window(harvest_strings)
        min_dur, max_dur, med_dur = "", "", ""
        
        if sow_start_doy and sow_end_doy and harv_start_doy and harv_end_doy:
            adj_start = harv_start_doy + 365 if harv_start_doy < sow_start_doy else harv_start_doy
            adj_end = harv_end_doy + 365 if harv_end_doy < sow_start_doy else harv_end_doy
            if adj_end < adj_start: adj_end += 365
            min_dur = max(adj_start - sow_end_doy, 1)
            max_dur = adj_end - sow_start_doy
            med_dur = int((min_dur + max_dur) / 2)

        # Create combined Harvest Window column
        h_start_str = day_to_date_string(harv_start_doy)
        h_end_str = day_to_date_string(harv_end_doy)
        harvest_window_final = f"{h_start_str} to {h_end_str}" if h_start_str and h_end_str else "Data Unavailable"
        
        final_records.append({
            "State": state,
            "District": district,
            "Crop": orig_crop.title(),
            "Season": orig_season,
            "Sowing Window (Local)": raw_sowing,
            "Harvest Window (UPAg)": harvest_window_final,
            "Min Duration (Days)": min_dur,
            "Max Duration (Days)": max_dur,
            "Median Duration (Days)": med_dur
        })

    final_df = pd.DataFrame(final_records)
    final_df.sort_values(by=['State', 'District', 'Crop'], inplace=True)
    final_df.to_csv(FINAL_DATASET, index=False)
    
    matched = final_df['Harvest Window (UPAg)'].apply(lambda x: x != "Data Unavailable").sum()
    print("\n========================================")
    print("🏆 PIPELINE MATRIX AGGREGATION COMPLETE")
    print("========================================")
    print(f"Total Output Rows: {len(final_df)}")
    print(f"Successfully Synchronized Records: {matched} ({matched/len(final_df)*100:.1f}%)")

if __name__ == "__main__":
    build_final_dataset()