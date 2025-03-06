#!/usr/bin/env python3
"""
Script to download PubChem Compound data in XML format.
Downloads files in parallel and verifies MD5 checksums.
Includes retry logic and rate limiting for reliability.
"""

import os
import sys
import json
import time
import random
import hashlib
import asyncio
import aiohttp
import logging
from pathlib import Path
from typing import List, Tuple, Dict
from tqdm.asyncio import tqdm
from dataclasses import dataclass

@dataclass
class PubchemFile:
    base_name: str
    url: str
    md5_url: str
    size: int  # in bytes
    downloaded: bool = False
    attempts: int = 0
    last_attempt: float = 0

# Data directories
BASE_DATA_DIR = Path("/home/ubuntu/data")
PUBCHEM_DATA_DIR = BASE_DATA_DIR / "pubchem"
DOWNLOAD_DIR = PUBCHEM_DATA_DIR / "compounds"
PROGRESS_FILE = PUBCHEM_DATA_DIR / "progress.json"
LOG_FILE = PUBCHEM_DATA_DIR / "download.log"

# Create all necessary directories
BASE_DATA_DIR.mkdir(exist_ok=True)
PUBCHEM_DATA_DIR.mkdir(exist_ok=True)
DOWNLOAD_DIR.mkdir(exist_ok=True)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

# Constants
MAX_RETRIES = 5
MIN_RETRY_DELAY = 10  # seconds
MAX_RETRY_DELAY = 300  # seconds
CONCURRENT_DOWNLOADS = 2  # reduced from 4

PUBCHEM_BASE_URL = "https://ftp.ncbi.nlm.nih.gov/pubchem/Compound/CURRENT-Full/XML"
CHUNK_SIZE = 1024 * 1024  # 1MB chunks

def calculate_retry_delay(attempts: int) -> float:
    """Calculate exponential backoff delay."""
    delay = min(MAX_RETRY_DELAY, MIN_RETRY_DELAY * (2 ** attempts))
    return delay + (random.random() * 5)  # Add jitter

def save_progress(files: List[PubchemFile]):
    """Save download progress to file."""
    progress = {
        f.base_name: {
            'downloaded': f.downloaded,
            'attempts': f.attempts,
            'last_attempt': f.last_attempt
        } for f in files
    }
    with open(PROGRESS_FILE, 'w') as f:
        json.dump(progress, f)

def load_progress(files: List[PubchemFile]):
    """Load download progress from file."""
    if not os.path.exists(PROGRESS_FILE):
        return
    
    with open(PROGRESS_FILE, 'r') as f:
        progress = json.load(f)
    
    for file in files:
        if file.base_name in progress:
            p = progress[file.base_name]
            file.downloaded = p['downloaded']
            file.attempts = p['attempts']
            file.last_attempt = p['last_attempt']

async def verify_existing_file(session: aiohttp.ClientSession,
                            file: PubchemFile,
                            output_path: Path,
                            files: List[PubchemFile]) -> bool:
    """Verify if existing file is valid using MD5 checksum."""
    if not output_path.exists():
        return False
        
    try:
        # Get expected MD5
        async with session.get(file.md5_url) as response:
            if response.status != 200:
                return False
            expected_md5 = (await response.text()).strip().split()[0]
        
        # Calculate actual MD5
        md5_hash = hashlib.md5()
        with open(output_path, 'rb') as f:
            for chunk in iter(lambda: f.read(CHUNK_SIZE), b''):
                md5_hash.update(chunk)
        actual_md5 = md5_hash.hexdigest()
        
        if actual_md5 == expected_md5:
            file.downloaded = True
            save_progress(files)  # Save progress after verification
            return True
            
        logging.info(f"MD5 mismatch for existing file {file.base_name}, will redownload")
        return False
        
    except Exception as e:
        logging.error(f"Error verifying existing file {file.base_name}: {str(e)}")
        return False

async def download_file(session: aiohttp.ClientSession, 
                       file: PubchemFile, 
                       output_dir: Path,
                       progress_bar: tqdm) -> bool:
    """Download a single file and verify its MD5 checksum."""
    output_path = output_dir / file.base_name
    
    # Check if file exists and is valid
    if output_path.exists():
        if await verify_existing_file(session, file, output_path):
            progress_bar.update(file.size)
            return True
        else:
            # File exists but is invalid, remove it
            os.remove(output_path)
    
    # Skip if already downloaded successfully (but file was removed)
    if file.downloaded:
        file.downloaded = False  # Reset if file doesn't exist
    
    # Check if we should retry
    if file.attempts >= MAX_RETRIES:
        logging.error(f"Max retries exceeded for {file.base_name}")
        return False
    
    # Respect rate limiting
    time_since_last = time.time() - file.last_attempt
    if time_since_last < calculate_retry_delay(file.attempts):
        return False
    
    file.attempts += 1
    file.last_attempt = time.time()
    
    try:
        # Download main file
        async with session.get(file.url) as response:
            if response.status != 200:
                logging.error(f"Failed to download {file.base_name}: {response.status}")
                return False
            
            with open(output_path, 'wb') as f:
                async for chunk in response.content.iter_chunked(CHUNK_SIZE):
                    f.write(chunk)
                    progress_bar.update(len(chunk))
        
        # Download and verify MD5
        async with session.get(file.md5_url) as response:
            if response.status != 200:
                logging.error(f"Failed to download MD5 for {file.base_name}")
                return False
            expected_md5 = (await response.text()).strip().split()[0]
        
        # Calculate actual MD5
        md5_hash = hashlib.md5()
        with open(output_path, 'rb') as f:
            for chunk in iter(lambda: f.read(CHUNK_SIZE), b''):
                md5_hash.update(chunk)
        actual_md5 = md5_hash.hexdigest()
        
        if actual_md5 != expected_md5:
            logging.error(f"MD5 mismatch for {file.base_name}")
            os.remove(output_path)
            return False
        
        file.downloaded = True
        save_progress(files)  # Save progress after successful download
        return True
    
    except Exception as e:
        logging.error(f"Error downloading {file.base_name}: {str(e)}")
        if output_path.exists():
            os.remove(output_path)
        return False

def get_compound_files() -> List[PubchemFile]:
    """Return list of compound files to download."""
    files = []
    # Pattern: Compound_000000001_000500000.xml.gz
    for i in range(0, 56500000, 500000):  # Adjust range based on latest compound count
        start_id = str(i + 1).zfill(9)
        end_id = str(min(i + 500000, 56500000)).zfill(9)
        base_name = f"Compound_{start_id}_{end_id}.xml.gz"
        url = f"{PUBCHEM_BASE_URL}/{base_name}"
        files.append(PubchemFile(
            base_name=base_name,
            url=url,
            md5_url=f"{url}.md5",
            size=0  # Will be updated when downloading
        ))
    return files

async def verify_all_existing_files(session: aiohttp.ClientSession,
                                files: List[PubchemFile],
                                output_dir: Path) -> None:
    """Verify all existing files before starting downloads."""
    logging.info("Verifying existing files...")
    existing_files = [f for f in files if (output_dir / f.base_name).exists()]
    
    if not existing_files:
        return
        
    with tqdm(total=len(existing_files), desc="Verifying") as progress_bar:
        for file in existing_files:
            await verify_existing_file(session, file, output_dir / file.base_name, files)
            progress_bar.update(1)
    
    verified_count = sum(1 for f in existing_files if f.downloaded)
    logging.info(f"Verified {verified_count}/{len(existing_files)} existing files")

async def main():
    
    files = get_compound_files()
    load_progress(files)  # Load previous progress
    
    async with aiohttp.ClientSession() as session:
        await verify_all_existing_files(session, files, DOWNLOAD_DIR)
        
        total_size = sum(f.size for f in files)
        remaining_files = [f for f in files if not f.downloaded]
        
        if not remaining_files:
            logging.info("All files already downloaded successfully!")
            return
        
        # Continue with same session for downloads
        with tqdm(total=total_size, unit='B', unit_scale=True, desc="Downloading") as progress_bar:
            while remaining_files:
                # Take a batch of files to try downloading
                batch = remaining_files[:CONCURRENT_DOWNLOADS]
                
                tasks = [
                    asyncio.create_task(download_file(session, file, DOWNLOAD_DIR, progress_bar))
                    for file in batch
                ]
                
                results = await asyncio.gather(*tasks)
                
                # Remove successfully downloaded files from remaining_files
                remaining_files = [
                    f for i, f in enumerate(batch) if not results[i]
                ] + remaining_files[CONCURRENT_DOWNLOADS:]
                
                if remaining_files:
                    delay = calculate_retry_delay(min(f.attempts for f in remaining_files))
                    logging.info(f"Waiting {delay:.1f}s before next attempt...")
                    await asyncio.sleep(delay)

if __name__ == "__main__":
    asyncio.run(main())
