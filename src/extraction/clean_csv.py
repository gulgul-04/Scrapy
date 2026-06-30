import pandas as pd
from pathlib import Path

# Paths
CSV_FILE = Path("data/interim/raw_pdf_sowing_data.csv")
CLEAN_CSV_FILE = Path("data/interim/cleaned_sowing_data.csv")

def clean_dataset():
    print("[*] Loading raw dataset...")
    df = pd.read_csv(CSV_FILE)
    
    # --- 1. Fix the Government Typos in Filenames ---
    # Dictionary mapping the typo to the correct State Name
    typo_map = {
        "Orissa": "Odisha",
        "Maharastra": "Maharashtra",
        "Uttarkhand": "Uttarakhand",
        "ArunchalPradesh": "Arunachal Pradesh",
        "AndamanAndNicobar": "Andaman Nicobar",
        "DadraAndNagarHaveli": "Dadra Nagar Haveli",
        "JammuAndKashmir": "Jammu Kashmir"
    }
    
    def fix_unknown_state(row):
        if row['State'] == 'Unknown_State':
            filename = str(row['District']) # The whole filename got dumped here
            
            for typo, correct_state in typo_map.items():
                if filename.startswith(typo):
                    # Extract the district by removing the typo length
                    district = filename[len(typo):]
                    # Add spaces before capital letters in district name
                    import re
                    clean_district = re.sub(r'(?<!^)(?=[A-Z])', ' ', district)
                    
                    return pd.Series([correct_state, clean_district])
                    
        return pd.Series([row['State'], row['District']])

    print("[*] Fixing 'Unknown_State' typos...")
    df[['State', 'District']] = df.apply(fix_unknown_state, axis=1)
    
    # --- 2. Remove Garbage Rows ---
    print("[*] Dropping rows with empty dates or malformed crop names...")
    garbage_windows = ['--', '---', 'na', 'n/a', 'nan']
    
    # Drop bad windows
    df = df[~df['Sowing Window'].astype(str).str.strip().str.lower().isin(garbage_windows)]
    df = df.dropna(subset=['Sowing Window'])
    
    # Drop long sentence "crops"
    df = df[df['Crop'].astype(str).str.len() <= 30]
    
    # --- 3. Final Polish ---
    # Drop duplicates just in case
    df = df.drop_duplicates()
    
    # Save the pristine dataset
    df.to_csv(CLEAN_CSV_FILE, index=False)
    
    print("\n[+] CLEANING COMPLETE!")
    print(f"[+] Pristine records saved: {len(df)}")
    print(f"[+] Saved to: {CLEAN_CSV_FILE.name}")

if __name__ == "__main__":
    clean_dataset()