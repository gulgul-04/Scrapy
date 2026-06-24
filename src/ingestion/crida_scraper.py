import json
import logging
from urllib.parse import urljoin
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from src.config import (
    CRIDA_TARGET_URL,
    RAW_PDF_DIR,
    INDEX_FILE,
    MANIFEST_FILE,
    PDF_MAGIC_BYTES
)

class CropCalendarPipeline:
    def __init__(self):
        self.session = self._configure_session()

    def _configure_session(self):
        session = requests.Session()
        retries = Retry(
            total=3,
            backoff_factor=1, 
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        adapter = HTTPAdapter(max_retries=retries)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        return session
    
    def format_filename(self, state, district):
        clean_state = ''.join(e for e in state.title() if e.isalnum())
        clean_district = ''.join(e for e in district.title() if e.isalnum)

        # Fallback
        if not clean_state: clean_state = "UnknownState"
        if not clean_district: clean_district = "UnknownDistrict"

        return f"{clean_state}{clean_district}.pdf"
    
    def extract_links(self):
        print("[*] Step 1: Extracting PDF links from source...")
        response = self.session.get(CRIDA_TARGET_URL)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')

        extracted_data = []

        cards = soup.find_all('div', class_='card')
        
        for card in cards:
            # 1. Extract State Name from the header
            header = card.find('div', class_='card-header')
            if not header:
                continue
                
            state_link = header.find('a')
            if not state_link:
                continue
                
            state_name = state_link.text.strip()
            
            # 2. Extract District links from the body
            body = card.find('div', class_='card-body')
            if not body:
                continue
                
            for link in body.find_all('a', href=True):
                href = link['href']
                
                if href.lower().endswith('.pdf'):
                    full_url = urljoin(CRIDA_TARGET_URL, href)
                    
                    # Clean up the trailing pipe '|' character found in the HTML source
                    district_name = link.text.replace('|', '').strip()
                    
                    if district_name:
                        extracted_data.append({
                            "state": state_name,
                            "district": district_name,
                            "pdf_url": full_url
                        })

        with open(INDEX_FILE, 'w', encoding='utf-8') as f:
            json.dump(extracted_data, f, indent=2, ensure_ascii=False)
            
        print(f"[+] Extracted {len(extracted_data)} district links.")
        return extracted_data

    def download_pdfs(self, index_data):
        print("\n[*] Step 2: Downloading PDFs...")
        manifest_data = []

        for item in tqdm(index_data, desc="Downloading Contingency Plans"):
            filename = self.format_filename(item['state'], item['district'])
            pdf_path = RAW_PDF_DIR / filename
            url = item['pdf_url']

            # Idempotency check: Skip if file exists and isn't empty
            if pdf_path.exists() and pdf_path.stat().st_size > 0:
                self._append_to_manifest(manifest_data, item['state'], item['district'], pdf_path, url)
                continue

            # Download the file
            try:
                with self.session.get(url, stream=True, timeout=15) as response:
                    response.raise_for_status()
                    
                    iterator = response.iter_content(chunk_size=8192)
                    
                    try:
                        first_chunk = next(iterator)
                    except StopIteration:
                        logging.warning(f"File at {url} was completely empty.")
                        continue
                    
                    # SECURITY CHECK: Validate against our hex/magic bytes in config
                    if not first_chunk.startswith(PDF_MAGIC_BYTES):
                        logging.warning(f"SECURITY: Invalid magic bytes. Skipped malicious/corrupt file at {url}")
                        continue
                    
                    with open(pdf_path, 'wb') as f:
                        f.write(first_chunk) 
                        for chunk in iterator:
                            if chunk:
                                f.write(chunk)
                                
                self._append_to_manifest(manifest_data, item['state'], item['district'], pdf_path, url)
                
            except requests.exceptions.RequestException as e:
                logging.error(f"Failed to download {filename} from {url}. Error: {str(e)}")

        self.generate_manifest(manifest_data)

    def _append_to_manifest(self, manifest_list, state, district, path, url):
        manifest_list.append({
            "state": state,
            "district": district,
            "pdf_path": str(path.relative_to(RAW_PDF_DIR.parent.parent).as_posix()), 
            "source_url": url
        })

    def generate_manifest(self, manifest_data):
        print(f"\n[*] Step 3: Generating Metadata Manifest...")
        with open(MANIFEST_FILE, 'w', encoding='utf-8') as f:
            json.dump(manifest_data, f, indent=2, ensure_ascii=False)
        print(f"[+] Manifest created with {len(manifest_data)} verified entries.")

    def run(self):
        if INDEX_FILE.exists():
            print(f"[*] Found existing index. Loading data...")
            with open(INDEX_FILE, 'r', encoding='utf-8') as f:
                index_data = json.load(f)
        else:
            index_data = self.extract_links()

        if index_data:
            self.download_pdfs(index_data)
        else:
            print("[-] No data to process. Pipeline halted.")

if __name__ == "__main__":
    pipeline = CropCalendarPipeline()
    pipeline.run()