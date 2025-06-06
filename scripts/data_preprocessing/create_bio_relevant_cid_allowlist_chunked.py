#!/usr/bin/env python3
"""
Memory-efficient version of the PubChem CID extraction script.
Processes files in chunks to avoid memory issues.
"""

import gzip
import zipfile
import xml.sax
from pathlib import Path
import logging
from typing import Set, Optional
import re

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class HMDBHandler(xml.sax.ContentHandler):
    """SAX handler for HMDB XML parsing - much more memory efficient than DOM/ElementTree."""
    
    def __init__(self, output_file, batch_size=10000):
        self.output_file = output_file
        self.current_element = ""
        self.current_content = ""
        self.in_metabolite = False
        self.in_secondary_accessions = False
        self.in_database_link = False
        self.in_pubchem_compound_id = False
        self.current_db_name = ""
        self.pubchem_cids = set()
        self.metabolite_count = 0
        self.batch_size = batch_size
        
    def startElement(self, name, attrs):
        self.current_element = name
        self.current_content = ""
        
        if name == "metabolite":
            self.in_metabolite = True
            self.metabolite_count += 1
            if self.metabolite_count % 10000 == 0:
                logger.info(f"Processed {self.metabolite_count} metabolites...")
                
        elif name == "secondary_accessions" and self.in_metabolite:
            self.in_secondary_accessions = True
            
        elif name == "database_link" and self.in_metabolite:
            self.in_database_link = True
            
        elif name == "pubchem_compound_id" and self.in_metabolite:
            self.in_pubchem_compound_id = True
            
    def endElement(self, name):
        if name == "metabolite":
            self.in_metabolite = False
            # Write batch to disk
            if len(self.pubchem_cids) >= self.batch_size:
                self._write_batch()
                
        elif name == "secondary_accessions":
            self.in_secondary_accessions = False
            
        elif name == "database_link":
            self.in_database_link = False
            self.current_db_name = ""
            
        elif name == "pubchem_compound_id":
            self.in_pubchem_compound_id = False
            if self.current_content.isdigit():
                self.pubchem_cids.add(self.current_content)
                
        elif name == "accession" and self.in_secondary_accessions:
            if self.current_content.startswith("PUBCHEM:"):
                cid = self.current_content.replace("PUBCHEM:", "").strip()
                if cid.isdigit():
                    self.pubchem_cids.add(cid)
                    
        elif name == "database" and self.in_database_link:
            self.current_db_name = self.current_content
            
        elif name == "database_id" and self.in_database_link:
            if self.current_db_name == "PubChem Compound" and self.current_content.isdigit():
                self.pubchem_cids.add(self.current_content)
                
        self.current_content = ""
        
    def characters(self, content):
        self.current_content += content.strip()
        
    def _write_batch(self):
        """Write current batch of CIDs to file."""
        with open(self.output_file, 'a') as f:
            for cid in sorted(self.pubchem_cids, key=int):
                f.write(f"{cid}\n")
        self.pubchem_cids.clear()
        
    def endDocument(self):
        """Write any remaining CIDs."""
        if self.pubchem_cids:
            self._write_batch()
        logger.info(f"Finished processing {self.metabolite_count} metabolites")


def extract_hmdb_pubchem_cids_sax(hmdb_zip_path: Path, temp_output: Path) -> int:
    """
    Extract PubChem CIDs from HMDB using SAX parser (memory efficient).
    Returns count of CIDs found.
    """
    cid_count = 0
    
    # Clear temp output file
    if temp_output.exists():
        temp_output.unlink()
    
    try:
        with zipfile.ZipFile(hmdb_zip_path, 'r') as zip_file:
            xml_files = [f for f in zip_file.namelist() if f.endswith('.xml')]
            
            if not xml_files:
                logger.error("No XML files found in HMDB zip")
                return 0
            
            xml_file = xml_files[0]
            logger.info(f"Processing HMDB XML file: {xml_file} using SAX parser")
            
            with zip_file.open(xml_file) as xml_data:
                handler = HMDBHandler(temp_output)
                parser = xml.sax.make_parser()
                parser.setContentHandler(handler)
                parser.parse(xml_data)
                
        # Count unique CIDs
        if temp_output.exists():
            with open(temp_output, 'r') as f:
                cids = set(line.strip() for line in f if line.strip())
                cid_count = len(cids)
                
    except Exception as e:
        logger.error(f"Error processing HMDB file: {e}")
    
    logger.info(f"Extracted {cid_count} unique PubChem CIDs from HMDB")
    return cid_count


def extract_chebi_pubchem_cids_chunked(chebi_sdf_gz_path: Path, temp_output: Path) -> int:
    """
    Extract PubChem CIDs from ChEBI SDF file in chunks.
    Returns count of CIDs found.
    """
    pubchem_cids = set()
    chunk_size = 10000  # Process 10k molecules at a time
    molecule_count = 0
    
    # Clear temp output file
    if temp_output.exists():
        temp_output.unlink()
    
    try:
        with gzip.open(chebi_sdf_gz_path, 'rt', encoding='utf-8') as f:
            current_properties = {}
            in_properties = False
            
            for line in f:
                line = line.strip()
                
                # Start of a property field
                if line.startswith('> <'):
                    property_name = line[3:-1]
                    in_properties = True
                    current_properties[property_name] = []
                
                # End of molecule record
                elif line == '$$$$':
                    molecule_count += 1
                    
                    # Check for PubChem references
                    for prop_name, prop_values in current_properties.items():
                        if 'pubchem' in prop_name.lower():
                            for value in prop_values:
                                match = re.search(r'\b(\d+)\b', value)
                                if match:
                                    pubchem_cids.add(match.group(1))
                    
                    # Reset for next molecule
                    current_properties = {}
                    in_properties = False
                    
                    # Write chunk to disk
                    if len(pubchem_cids) >= chunk_size:
                        with open(temp_output, 'a') as out:
                            for cid in sorted(pubchem_cids, key=int):
                                out.write(f"{cid}\n")
                        pubchem_cids.clear()
                        logger.info(f"Processed {molecule_count} ChEBI molecules...")
                
                # Property value
                elif in_properties and line and not line.startswith('>'):
                    if current_properties:
                        last_prop = list(current_properties.keys())[-1]
                        current_properties[last_prop].append(line)
                
                # Empty line ends property values
                elif not line and in_properties:
                    in_properties = False
                    
        # Write remaining CIDs
        if pubchem_cids:
            with open(temp_output, 'a') as out:
                for cid in sorted(pubchem_cids, key=int):
                    out.write(f"{cid}\n")
                    
    except Exception as e:
        logger.error(f"Error processing ChEBI file: {e}")
    
    # Count unique CIDs
    cid_count = 0
    if temp_output.exists():
        with open(temp_output, 'r') as f:
            cids = set(line.strip() for line in f if line.strip())
            cid_count = len(cids)
    
    logger.info(f"Extracted {cid_count} unique PubChem CIDs from ChEBI")
    return cid_count


def merge_and_deduplicate(hmdb_temp: Path, chebi_temp: Path, output_path: Path) -> None:
    """Merge and deduplicate CIDs from temporary files."""
    all_cids = set()
    
    # Read HMDB CIDs
    if hmdb_temp.exists():
        with open(hmdb_temp, 'r') as f:
            hmdb_cids = set(line.strip() for line in f if line.strip())
            all_cids.update(hmdb_cids)
            logger.info(f"Read {len(hmdb_cids)} CIDs from HMDB temp file")
    
    # Read ChEBI CIDs  
    if chebi_temp.exists():
        with open(chebi_temp, 'r') as f:
            chebi_cids = set(line.strip() for line in f if line.strip())
            all_cids.update(chebi_cids)
            logger.info(f"Read {len(chebi_cids)} CIDs from ChEBI temp file")
    
    # Write final deduplicated list
    logger.info(f"Total unique PubChem CIDs: {len(all_cids)}")
    
    sorted_cids = sorted(all_cids, key=lambda x: int(x))
    with open(output_path, 'w') as f:
        for cid in sorted_cids:
            f.write(f"{cid}\n")
    
    logger.info(f"Final allowlist written to: {output_path}")
    
    # Clean up temp files
    if hmdb_temp.exists():
        hmdb_temp.unlink()
    if chebi_temp.exists():
        chebi_temp.unlink()


def main():
    """Main execution function."""
    # Define paths
    data_dir = Path("/home/ubuntu/biomapper/data")
    hmdb_path = data_dir / "hmdb" / "hmdb_metabolites.zip"
    chebi_path = data_dir / "chebi" / "ChEBI_complete_3star.sdf.gz"
    output_path = data_dir / "bio_relevant_cids.txt"
    
    # Temporary files
    hmdb_temp = data_dir / "hmdb_cids_temp.txt"
    chebi_temp = data_dir / "chebi_cids_temp.txt"
    
    # Check if input files exist
    if not hmdb_path.exists():
        logger.error(f"HMDB file not found: {hmdb_path}")
        return
    
    if not chebi_path.exists():
        logger.error(f"ChEBI file not found: {chebi_path}")
        return
    
    # Process HMDB
    logger.info("Processing HMDB (this may take a while)...")
    extract_hmdb_pubchem_cids_sax(hmdb_path, hmdb_temp)
    
    # Process ChEBI
    logger.info("Processing ChEBI...")
    extract_chebi_pubchem_cids_chunked(chebi_path, chebi_temp)
    
    # Merge and deduplicate
    logger.info("Merging and deduplicating CIDs...")
    merge_and_deduplicate(hmdb_temp, chebi_temp, output_path)


if __name__ == "__main__":
    main()
