# Project Architecture

Scrapy/
├── .venv/                  # Virtual environment (ignored by Git)
├── .gitignore              # Files and folders omitted from version control
├── README.md               # Project overview and setup instructions
├── requirements.txt        # Python dependencies
├── structure.md            # This architecture map
├── data/                   # Local data storage (ignored by Git)
│   ├── raw_pdfs/           # Downloaded CRIDA PDF files
│   ├── interim/            # Intermediate parsed text/tables (Future)
│   └── processed/          # Final CSV/JSON datasets (Future)
└── src/                    # Source code
    ├── __init__.py
    ├── config.py           # Configuration variables, URLs, and file paths
    ├── ingestion/          # Scripts for scraping and downloading
    │   ├── __init__.py
    │   └── crida_scraper.py # Web crawler and idempotent PDF downloader
    ├── extraction/         # Scripts for parsing PDFs and NLP (Future)
    └── utils/              # Helper functions (logging, data cleaning)