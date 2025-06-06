#!/usr/bin/env python3
"""
Extract PubChem CIDs from HMDB and ChEBI databases to create an allowlist
of biologically relevant compounds for filtering PubChem embeddings.

This script parses:
1. HMDB metabolites data (XML format)
2. ChEBI complete data (SDF format)

And outputs a deduplicated list of PubChem CIDs.
"""

import gzip
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import logging
from typing import Set, Optional
import re
from collections import defaultdict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def extract_hmdb_pubchem_cids(hmdb_zip_path: Path) -> Set[str]:
    """
    Extract PubChem CIDs from HMDB metabolites XML file.
    
    HMDB XML structure typically includes PubChem CID in the metabolite entries.
    """
    pubchem_cids = set()
    
    try:
        with zipfile.ZipFile(hmdb_zip_path, 'r') as zip_file:
            # List files in the zip
            file_list = zip_file.namelist()
            logger.info(f"Files in HMDB zip: {file_list}")
            
            # Find the XML file (usually named hmdb_metabolites.xml or similar)
            xml_files = [f for f in file_list if f.endswith('.xml')]
            
            if not xml_files:
                logger.error("No XML files found in HMDB zip")
                return pubchem_cids
            
            # Process the first XML file
            xml_file = xml_files[0]
            logger.info(f"Processing HMDB XML file: {xml_file}")
            
            with zip_file.open(xml_file) as xml_data:
                # Parse XML incrementally to handle large files
                for event, elem in ET.iterparse(xml_data, events=('start', 'end')):
                    if event == 'end' and elem.tag == 'metabolite':
                        # Look for PubChem CID in the metabolite entry
                        # Common locations: secondary_accessions, database_cross_references
                        
                        # Check secondary accessions
                        secondary_accessions = elem.find('secondary_accessions')
                        if secondary_accessions is not None:
                            for accession in secondary_accessions.findall('accession'):
                                if accession.text and accession.text.startswith('PUBCHEM:'):
                                    cid = accession.text.replace('PUBCHEM:', '').strip()
                                    if cid.isdigit():
                                        pubchem_cids.add(cid)
                        
                        # Check database cross references
                        # Look for PubChem compound references
                        for db_link in elem.findall('.//database_link'):
                            db_name = db_link.find('database')
                            if db_name is not None and db_name.text == 'PubChem Compound':
                                db_id = db_link.find('database_id')
                                if db_id is not None and db_id.text and db_id.text.isdigit():
                                    pubchem_cids.add(db_id.text)
                        
                        # Clear the element to save memory
                        elem.clear()
                        
    except Exception as e:
        logger.error(f"Error processing HMDB file: {e}")
    
    logger.info(f"Extracted {len(pubchem_cids)} PubChem CIDs from HMDB")
    return pubchem_cids


def extract_chebi_pubchem_cids(chebi_sdf_gz_path: Path) -> Set[str]:
    """
    Extract PubChem CIDs from ChEBI SDF file.
    
    ChEBI SDF files contain cross-references in the property fields.
    """
    pubchem_cids = set()
    
    try:
        with gzip.open(chebi_sdf_gz_path, 'rt', encoding='utf-8') as f:
            current_properties = {}
            in_properties = False
            
            for line in f:
                line = line.strip()
                
                # Start of a property field
                if line.startswith('> <'):
                    property_name = line[3:-1]  # Extract property name
                    in_properties = True
                    current_properties[property_name] = []
                
                # End of molecule record
                elif line == '$$$$':
                    # Check if we have PubChem references
                    for prop_name, prop_values in current_properties.items():
                        if 'pubchem' in prop_name.lower():
                            for value in prop_values:
                                # Extract numeric CID
                                match = re.search(r'\b(\d+)\b', value)
                                if match:
                                    pubchem_cids.add(match.group(1))
                    
                    # Reset for next molecule
                    current_properties = {}
                    in_properties = False
                
                # Property value
                elif in_properties and line and not line.startswith('>'):
                    # Add to current property
                    if current_properties:
                        last_prop = list(current_properties.keys())[-1]
                        current_properties[last_prop].append(line)
                
                # Empty line ends property values
                elif not line and in_properties:
                    in_properties = False
                    
    except Exception as e:
        logger.error(f"Error processing ChEBI file: {e}")
    
    logger.info(f"Extracted {len(pubchem_cids)} PubChem CIDs from ChEBI")
    return pubchem_cids


def create_allowlist(
    hmdb_path: Path,
    chebi_path: Path,
    output_path: Path
) -> None:
    """
    Create a combined allowlist of PubChem CIDs from HMDB and ChEBI.
    """
    logger.info("Starting PubChem CID extraction...")
    
    # Extract from HMDB
    logger.info(f"Processing HMDB file: {hmdb_path}")
    hmdb_cids = extract_hmdb_pubchem_cids(hmdb_path)
    
    # Extract from ChEBI
    logger.info(f"Processing ChEBI file: {chebi_path}")
    chebi_cids = extract_chebi_pubchem_cids(chebi_path)
    
    # Combine and deduplicate
    all_cids = hmdb_cids.union(chebi_cids)
    logger.info(f"Total unique PubChem CIDs: {len(all_cids)}")
    logger.info(f"HMDB only: {len(hmdb_cids - chebi_cids)}")
    logger.info(f"ChEBI only: {len(chebi_cids - hmdb_cids)}")
    logger.info(f"Overlap: {len(hmdb_cids.intersection(chebi_cids))}")
    
    # Sort CIDs numerically for consistent output
    sorted_cids = sorted(all_cids, key=lambda x: int(x))
    
    # Write to output file
    with open(output_path, 'w') as f:
        for cid in sorted_cids:
            f.write(f"{cid}\n")
    
    logger.info(f"Allowlist written to: {output_path}")
    
    # Write summary statistics
    summary_path = output_path.with_suffix('.summary.txt')
    with open(summary_path, 'w') as f:
        f.write("PubChem CID Allowlist Summary\n")
        f.write("=" * 40 + "\n")
        f.write(f"Total unique CIDs: {len(all_cids)}\n")
        f.write(f"From HMDB: {len(hmdb_cids)}\n")
        f.write(f"From ChEBI: {len(chebi_cids)}\n")
        f.write(f"HMDB only: {len(hmdb_cids - chebi_cids)}\n")
        f.write(f"ChEBI only: {len(chebi_cids - hmdb_cids)}\n")
        f.write(f"Overlap: {len(hmdb_cids.intersection(chebi_cids))}\n")
    
    logger.info(f"Summary written to: {summary_path}")


def main():
    """Main execution function."""
    # Define paths
    data_dir = Path("/home/ubuntu/biomapper/data")
    hmdb_path = data_dir / "hmdb" / "hmdb_metabolites.zip"
    chebi_path = data_dir / "chebi" / "ChEBI_complete_3star.sdf.gz"
    output_path = data_dir / "bio_relevant_cids.txt"
    
    # Check if input files exist
    if not hmdb_path.exists():
        logger.error(f"HMDB file not found: {hmdb_path}")
        return
    
    if not chebi_path.exists():
        logger.error(f"ChEBI file not found: {chebi_path}")
        return
    
    # Create allowlist
    create_allowlist(hmdb_path, chebi_path, output_path)


if __name__ == "__main__":
    main()
