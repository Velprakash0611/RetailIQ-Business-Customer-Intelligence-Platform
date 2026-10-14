"""
Download or generate development benchmark dataset for RetailIQ.
Attempts to fetch UCI Online Retail dataset if requested, or falls back to
the synthetic benchmark generator.
"""

import argparse
import os

import requests
from build_benchmark import generate_benchmark_dataset

UCI_URL = "https://archive.ics.uci.edu/static/public/352/online+retail.zip"


def download_uci_dataset(dest_dir: str = "data/raw") -> bool:
    """Attempts to download the official UCI Online Retail archive."""
    os.makedirs(dest_dir, exist_ok=True)
    zip_path = os.path.join(dest_dir, "online_retail.zip")
    print(f"Connecting to UCI repository: {UCI_URL}...")
    try:
        resp = requests.get(UCI_URL, timeout=15)
        if resp.status_code == 200:
            with open(zip_path, "wb") as f:
                f.write(resp.content)
            print(f"Downloaded UCI Online Retail zip to {zip_path}")
            return True
        else:
            print(f"Server returned status {resp.status_code}. Generating benchmark dataset instead.")
            return False
    except Exception as e:
        print(f"Could not connect to external UCI server ({e}). Using benchmark generator.")
        return False


def main():
    parser = argparse.ArgumentParser(description="Download or generate RetailIQ development data")
    parser.add_argument("--download-uci", action="store_true", help="Attempt downloading official UCI archive")
    args = parser.parse_args()

    if args.download_uci:
        success = download_uci_dataset()
        if not success:
            generate_benchmark_dataset()
    else:
        generate_benchmark_dataset()


if __name__ == "__main__":
    main()
