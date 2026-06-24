import requests
import json
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
UPAG_FILE = DATA_DIR / "upag_master_calander.json"

def fetch_upag_calendar():
    print("[*] Contacting UPAg API...")
    
    url = "https://api-prd.upag.gov.in/v1/upagapi/cropcalender/domesticcropcalender"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Origin": "https://upag.gov.in",
        "Referer": "https://upag.gov.in/"
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        data = response.json()
        
        # FIX: Dig into the double-envelope structure
        # Use .get() safely in case the API structure changes slightly
        records_envelope = data.get("records", {})
        crop_list = records_envelope.get("records", [])
        
        print(f"[+] Successfully fetched {len(crop_list)} actual crop records from UPAg.")
        
        with open(UPAG_FILE, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"[+] Saved to {UPAG_FILE.name}")
        
        # Analysis: Find all unique indicators inside the month arrays
        unique_indicators = set()
        months = ['jan', 'feb', 'mar', 'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec']
        
        for record in crop_list:
            for month in months:
                # Some months might be null or empty, so we default to an empty list
                month_data = record.get(month) or []
                for item in month_data:
                    unique_indicators.add(item)
                    
        print("\n[*] Unique Indicators (Colors/Text) found in the dataset:")
        for indicator in sorted(unique_indicators):
            print(f"  - {indicator}")
            
    except requests.exceptions.RequestException as e:
        print(f"[-] API Request Failed: {e}")

if __name__ == "__main__":
    fetch_upag_calendar()