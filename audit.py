import pandas as pd
from pathlib import Path

# Path to your CSV
CSV_FILE = Path("data/interim/raw_pdf_sowing_data.csv")

def audit_dataset():
    print("[*] Loading CSV for Audit...")
    df = pd.read_csv(CSV_FILE)
    total_rows = len(df)
    
    # --- RULE 1: Unknown or Bad States ---
    unknown_states = df[df['State'] == 'Unknown_State']
    
    # --- RULE 2: Invalid Seasons ---
    # A valid season should contain at least one of these keywords
    valid_season_keywords = ['kharif', 'rabi', 'summer', 'zaid', 'pre']
    
    def check_season(s):
        s_lower = str(s).lower()
        return any(keyword in s_lower for keyword in valid_season_keywords)
        
    invalid_seasons = df[~df['Season'].apply(check_season)]
    
    # --- RULE 3: Empty or Garbage Sowing Windows ---
    garbage_windows = ['--', '---', 'na', 'n/a', 'nan']
    invalid_windows = df[
        df['Sowing Window'].astype(str).str.strip().str.lower().isin(garbage_windows) | 
        df['Sowing Window'].isna()
    ]
    
    # --- RULE 4: Crop Names that look like sentences ---
    # If a crop name is over 30 characters, it's likely a sentence that bled into the column
    long_crops = df[df['Crop'].astype(str).str.len() > 30]

    # Calculate Total Unique Bad Rows (a row might violate multiple rules)
    bad_indices = set(unknown_states.index) | set(invalid_seasons.index) | \
                  set(invalid_windows.index) | set(long_crops.index)
                  
    total_bad = len(bad_indices)
    good_rows = total_rows - total_bad
    
    print("\n" + "="*40)
    print("📊 DATASET AUDIT REPORT")
    print("="*40)
    print(f"Total Rows Extracted: {total_rows}")
    print(f"Pristine Rows:        {good_rows} ({good_rows/total_rows*100:.1f}%)")
    print(f"Rows with Errors:     {total_bad} ({total_bad/total_rows*100:.1f}%)")
    
    print("\n⚠️ ERROR BREAKDOWN:")
    print(f"  - 'Unknown_State' mapping errors: {len(unknown_states)}")
    print(f"  - Invalid/Weird Season labels:    {len(invalid_seasons)}")
    print(f"  - Blank/Garbage Sowing Windows:   {len(invalid_windows)}")
    print(f"  - Malformed Crop Names:           {len(long_crops)}")
    
    print("\n🔍 SAMPLE OF UNKNOWN STATES (Filenames that need fixing):")
    # Show the unique districts that failed the state extraction
    print(unknown_states['District'].unique()[:10])

if __name__ == "__main__":
    audit_dataset()