import json
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"

# Auto-detect file name (handles your previous typo)
UPAG_FILE = DATA_DIR / "upag_master_calendar.json"
if not UPAG_FILE.exists():
    UPAG_FILE = DATA_DIR / "upag_master_calander.json"
    
NORMALIZED_FILE = DATA_DIR / "master_duration_dict.json"

# Known Hex Codes from UPAg API (Case Insensitive)
SOWING_HEX = "#318789"
HARVEST_HEX = "#9AC23C"

MONTHS = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']

# Standard days in a month for range calculation
MONTH_DAYS = {
    'jan': 31, 'feb': 28, 'mar': 31, 'apr': 30, 'may': 31, 'jun': 30,
    'jul': 31, 'aug': 31, 'sep': 30, 'oct': 31, 'nov': 30, 'dec': 31
}

def transform_to_date_range(month, modifiers):
    """
    Transforms UPAg labels (E, M, L, B) into approximate date ranges.
    """
    month_title = month.title()
    end_day = MONTH_DAYS[month]
    
    # Check for modifiers
    if "E" in modifiers or "B" in modifiers:
        return f"{month_title} 01 - {month_title} 10"
    elif "M" in modifiers:
        return f"{month_title} 11 - {month_title} 20"
    elif "L" in modifiers:
        return f"{month_title} 21 - {month_title} {end_day}"
    else:
        # If no modifier is present, assume the whole month
        return f"{month_title} 01 - {month_title} {end_day}"

def build_master_dictionary():
    print("[*] Translating UPAg Master Calendar into Date Ranges...")
    
    with open(UPAG_FILE, 'r', encoding='utf-8') as f:
        raw_data = json.load(f)
        
    crop_list = raw_data.get("records", {}).get("records", [])
    master_dict = {}
    
    for record in crop_list:
        state = record.get("state", "").strip().title()
        crop = record.get("crops", "").strip().title()
        season = record.get("season", "").strip().title()
        
        if not state or not crop:
            continue
            
        sowing_ranges = []
        harvest_ranges = []
        
        for month in MONTHS:
            # UPAg arrays can contain strings like "E", "M", "#9AC23C"
            raw_month_data = record.get(month) or []
            
            # Normalize to uppercase for safe checking
            month_data = [str(item).upper() for item in raw_month_data]
            
            # Extract modifiers (E, M, L, B) if they exist for this month
            modifiers = [item for item in month_data if item in ["E", "M", "L", "B"]]
            
            # Check for Sowing or Harvesting Colors
            if SOWING_HEX in month_data:
                sowing_ranges.append(transform_to_date_range(month, modifiers))
            
            if HARVEST_HEX in month_data:
                harvest_ranges.append(transform_to_date_range(month, modifiers))
                
        # Only save crops that actually have data
        if sowing_ranges or harvest_ranges:
            if state not in master_dict:
                master_dict[state] = {}
            if crop not in master_dict[state]:
                master_dict[state][crop] = {}
                
            master_dict[state][crop][season] = {
                "upag_sowing_window": sowing_ranges,
                "upag_harvest_window": harvest_ranges
            }
            
    with open(NORMALIZED_FILE, 'w', encoding='utf-8') as f:
        json.dump(master_dict, f, indent=2)
        
    print(f"[+] Normalization complete. Dictionary contains data for {len(master_dict)} states.")
    print(f"[+] Saved to {NORMALIZED_FILE.name}")

if __name__ == "__main__":
    build_master_dictionary()