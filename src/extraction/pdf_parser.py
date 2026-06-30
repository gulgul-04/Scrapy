import pdfplumber
import pandas as pd
from pathlib import Path
from tqdm import tqdm
import logging
import re
import gc

# Import config
from src.config import RAW_PDF_DIR, RAW_SOWING_DATA, LOG_FILE

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class CridaPdfParser:
    def __init__(self):
        self.pdf_paths = list(RAW_PDF_DIR.glob("**/*.pdf"))
        self.extracted_records = []
        self.batch_size = 30
        
        self.indian_states = [
            "AndamanNicobar", "AndhraPradesh", "ArunachalPradesh", "Assam", "Bihar", "Chandigarh",
            "Chhattisgarh", "DadraNagarHaveli", "DamanDiu", "Delhi", "Goa", "Gujarat", "Haryana",
            "HimachalPradesh", "JammuKashmir", "Jharkhand", "Karnataka", "Kerala", "Ladakh", "Lakshadweep",
            "MadhyaPradesh", "Maharashtra", "Manipur", "Meghalaya", "Mizoram", "Nagaland", "Odisha",
            "Puducherry", "Punjab", "Rajasthan", "Sikkim", "TamilNadu", "Telangana", "Tripura",
            "UttarPradesh", "Uttarakhand", "WestBengal"
        ]

    def extract_state_district(self, filename):
        stem = Path(filename).stem
        for state in self.indian_states:
            if stem.startswith(state):
                district = stem[len(state):]
                clean_state = re.sub(r'(?<!^)(?=[A-Z])', ' ', state)
                clean_district = re.sub(r'(?<!^)(?=[A-Z])', ' ', district)
                return clean_state, clean_district
        return "Unknown_State", stem

    def parse_pdf(self, pdf_path):
        state, district = self.extract_state_district(pdf_path.name)
        
        try:
            with pdfplumber.open(pdf_path) as pdf:
                scan_range = pdf.pages[1:8] if len(pdf.pages) >= 8 else pdf.pages[1:]
                table_found = False
                
                for page in scan_range:
                    text = page.extract_text()
                    if not text:
                        continue
                        
                    if "sowing window" in text.lower():
                        tables = page.extract_tables()
                        
                        for table_data in tables:
                            table_string = str(table_data).lower()
                            if "sowing" in table_string:
                                self._process_table(table_data, state, district, pdf_path.name)
                                table_found = True
                                break 
                                
                    if table_found:
                        break 

                if not table_found:
                    logging.warning(f"Sowing table not found in {pdf_path.name}")

        except Exception as e:
            logging.error(f"Failed to parse {pdf_path.name}: {e}")

    def _process_table(self, table_data, state, district, filename):
        """Unified Matrix Mapping Logic based on visual Season vs Crop grid."""
        
        # 1. Clean the raw list-of-lists grid
        cleaned_table = [[str(cell).strip() if cell is not None else "" for cell in row] for row in table_data]

        if not cleaned_table:
            return

        header_row = []
        header_index = -1

        # 2. Identify the Header Row (Contains crop names)
        for i, row in enumerate(cleaned_table):
            row_str = " ".join(row).lower()
            if "sowing window" in row_str or "crop 1" in row_str:
                header_row = row
                header_index = i
                break

        if not header_row:
            return 

        # 3. Clean the Header Row to extract pure crop names
        clean_crops = []
        for cell in header_row:
            cell_lower = cell.lower()
            # Ignore the first few columns that just say "Sowing Window" or "1.12"
            if "sowing window" in cell_lower or "major crops" in cell_lower or "1.8" in cell_lower or "1.12" in cell_lower:
                clean_crops.append("") 
            else:
                # Strip out the boilerplate "crop 1 (Specify the crop):"
                crop_name = re.sub(r'crop \d+.*?:', '', cell, flags=re.IGNORECASE)
                # Remove punctuation and newlines
                crop_name = re.sub(r'[^a-zA-Z\s]', '', crop_name).strip().title()
                clean_crops.append(crop_name)

        seasons = ['kharif', 'rabi', 'summer', 'zaid']

        # 4. Iterate through the data rows below the header
        for row in cleaned_table[header_index + 1:]:
            row_season = "Unknown"
            
            # Identify the Season in the first 2 columns
            for cell in row[:3]:
                if any(s in cell.lower() for s in seasons):
                    row_season = cell.replace('\n', ' ').strip().title()
                    break
            
            if row_season == "Unknown":
                continue 

            # 5. The Matrix Intersection: Map dates to crops using the column index
            for col_idx in range(len(row)):
                if col_idx >= len(clean_crops):
                    break
                
                crop_name = clean_crops[col_idx]
                sowing_date = row[col_idx].replace('\n', ' ').strip()
                
                # Skip empty cells, hyphens, or columns without a crop name
                if not crop_name or not sowing_date or sowing_date == '-' or sowing_date.lower() in ['na', '---']:
                    continue
                
                # Skip if the date cell is just accidentally repeating the season name
                if any(s in sowing_date.lower() for s in seasons) and len(sowing_date) < 15:
                    continue

                self.extracted_records.append({
                    "State": state,
                    "District": district,
                    "Crop": crop_name,
                    "Season": row_season,
                    "Sowing Window": sowing_date
                })

    def run(self):
        total_pdfs = len(self.pdf_paths)
        batches = [self.pdf_paths[i:i + self.batch_size] for i in range(0, total_pdfs, self.batch_size)]
        
        print(f"[*] Starting Unified Matrix PDF Extraction: {total_pdfs} files across {len(batches)} batches.")
        
        for i, batch in enumerate(tqdm(batches, desc="Overall Progress", position=0)):
            for pdf_path in tqdm(batch, desc=f"Batch {i+1}", leave=False, position=1):
                self.parse_pdf(pdf_path)
            
            gc.collect()
            
        final_df = pd.DataFrame(self.extracted_records)
        final_df.drop_duplicates(inplace=True)
        final_df.to_csv(RAW_SOWING_DATA, index=False)
        
        print(f"\n[+] Extraction Complete.")
        print(f"[+] Total Clean Records Extracted: {len(final_df)}")
        print(f"[+] Saved to {RAW_SOWING_DATA.name}")

if __name__ == "__main__":
    parser = CridaPdfParser()
    parser.run()