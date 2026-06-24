# India District-Wise Crop Calendar Extractor

An automated data engineering pipeline designed to build a machine-readable, district-specific crop calendar dataset for Indian districts using official ICAR-CRIDA District Agriculture Contingency Plans.

## 🎯 Project Goal
To transition from localized, unstructured PDF contingency plans into a centralized, searchable JSON/CSV dataset detailing sowing periods, harvesting periods, and crop durations for 6–7 major crops per district.

## 🚀 Current Status: Phase 1 (Ingestion) Complete
The current pipeline successfully crawls the CRIDA database, extracts district metadata, and performs highly-resilient, idempotent downloads of all available PDF reports. 

**Features:**
* **Automated Link Extraction:** Parses the CRIDA DOM to map States and Districts to PDF URLs.
* **Idempotent Downloads:** Safely resumes interrupted downloads without duplicating files.
* **Resilient Requests:** Built-in retry adapters to handle government server timeouts and bad gateways.
* **Manifest Generation:** Outputs a clean `pdf_manifest.json` mapping local file paths to their source URLs.

*Note: Phase 2 (PDF text/table extraction and normalization) is currently in development.*

## 💻 Installation & Setup

**1. Clone the repository:**
```bash
git clone https://github.com/gulgul-04/Scrapy.git
cd Scrapy