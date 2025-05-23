#!/usr/bin/env python3
"""Analyze overlap between HMDB and ChEBI PubChem CIDs."""

import logging
import xml.sax
import gzip
import zipfile
from pathlib import Path

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HMDBHandler(xml.sax.ContentHandler):
    """SAX handler for HMDB XML parsing."""
    
    def __init__(self):
        self.in_metabolite = False
        self.in_pubchem_compound_id = False
        self.current_content = ""
        self.pubchem_cids = set()
        self.metabolite_count = 0
        
    def startElement(self, name, attrs):
        if name == "metabolite":
            self.in_metabolite = True
            self.metabolite_count += 1
            if self.metabolite_count % 20000 == 0:
                logger.info(f"Processed {self.metabolite_count} metabolites...")
                
        elif name == "pubchem_compound_id" and self.in_metabolite:
            self.in_pubchem_compound_id = True
            
    def endElement(self, name):
        if name == "metabolite":
            self.in_metabolite = False
            
        elif name == "pubchem_compound_id":
            self.in_pubchem_compound_id = False
            if self.current_content.isdigit():
                self.pubchem_cids.add(self.current_content)
                
        self.current_content = ""
        
    def characters(self, content):
        self.current_content += content.strip()

def extract_hmdb_cids():
    """Extract PubChem CIDs from HMDB."""
    hmdb_path = Path("/home/ubuntu/biomapper/data/hmdb/hmdb_metabolites.zip")
    
    logger.info("Processing HMDB...")
    handler = HMDBHandler()
    
    with zipfile.ZipFile(hmdb_path, 'r') as zf:
        with zf.open('hmdb_metabolites.xml') as xml_file:
            parser = xml.sax.make_parser()
            parser.setContentHandler(handler)
            parser.parse(xml_file)
    
    logger.info(f"Extracted {len(handler.pubchem_cids)} unique PubChem CIDs from HMDB")
    return handler.pubchem_cids

def extract_chebi_cids():
    """Extract PubChem CIDs from ChEBI."""
    chebi_path = Path("/home/ubuntu/biomapper/data/chebi/ChEBI_complete_3star.sdf.gz")
    
    logger.info("Processing ChEBI...")
    pubchem_cids = set()
    
    with gzip.open(chebi_path, 'rt') as f:
        current_cid = None
        for line in f:
            line = line.strip()
            if line.startswith("> <ChEBI ID>"):
                current_cid = None
            elif line.startswith("> <Pubchem Database Links>"):
                # Next line should contain the PubChem CID
                next_line = next(f, "").strip()
                if next_line.startswith("CID:"):
                    cid = next_line.replace("CID:", "").strip()
                    if cid.isdigit():
                        pubchem_cids.add(cid)
    
    logger.info(f"Extracted {len(pubchem_cids)} unique PubChem CIDs from ChEBI")
    return pubchem_cids

def main():
    """Main function to analyze overlap."""
    # Extract CIDs from both sources
    hmdb_cids = extract_hmdb_cids()
    chebi_cids = extract_chebi_cids()
    
    # Calculate overlap
    overlap = hmdb_cids & chebi_cids
    only_hmdb = hmdb_cids - chebi_cids
    only_chebi = chebi_cids - hmdb_cids
    all_cids = hmdb_cids | chebi_cids
    
    # Print statistics
    logger.info("\n=== CID Overlap Analysis ===")
    logger.info(f"HMDB CIDs: {len(hmdb_cids):,}")
    logger.info(f"ChEBI CIDs: {len(chebi_cids):,}")
    logger.info(f"Overlap: {len(overlap):,} ({len(overlap)/len(all_cids)*100:.1f}% of total)")
    logger.info(f"Only in HMDB: {len(only_hmdb):,}")
    logger.info(f"Only in ChEBI: {len(only_chebi):,}")
    logger.info(f"Total unique CIDs: {len(all_cids):,}")
    
    # Show some examples of overlapping CIDs
    if overlap:
        logger.info(f"\nFirst 10 overlapping CIDs: {sorted(list(overlap))[:10]}")

if __name__ == "__main__":
    main()
