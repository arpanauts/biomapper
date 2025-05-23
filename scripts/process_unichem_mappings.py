#!/usr/bin/env python3
"""
Process UniChem reference mappings to extract PubChem CIDs for biologically relevant sources.
Memory-efficient version that processes the file in a streaming fashion.
"""

import gzip
import logging
from pathlib import Path
from typing import Set
import tempfile
import os

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Define biologically relevant source IDs from UniChem
BIOLOGICAL_SOURCE_IDS = {
    1: "ChEMBL",
    2: "DrugBank", 
    4: "Guide to Pharmacology",
    6: "KEGG Ligand",
    14: "FDA/USP SRS",
    17: "PharmGKB",
    18: "HMDB",
    27: "Recon",
    33: "LipidMaps",
    34: "DrugCentral",
    36: "Metabolights",
    38: "Rhea",
    41: "SwissLipids"
}

# PubChem source ID in UniChem
PUBCHEM_SOURCE_ID = 22

def process_unichem_reference_memory_efficient(
    unichem_file: Path,
    existing_allowlist: Path,
    output_file: Path
) -> None:
    """
    Process UniChem reference file to extract PubChem CIDs in a memory-efficient way.
    
    Strategy:
    1. First pass: Extract all UCIs that belong to biological sources, save to temp file
    2. Second pass: For UCIs in temp file, extract their PubChem CIDs
    
    Args:
        unichem_file: Path to reference.tsv.gz from UniChem
        existing_allowlist: Path to existing bio_relevant_cids.txt
        output_file: Path to write expanded allowlist
    """
    # Load existing CIDs
    existing_cids = set()
    if existing_allowlist.exists():
        logger.info(f"Loading existing CIDs from {existing_allowlist}")
        with open(existing_allowlist, 'r') as f:
            for line in f:
                cid = line.strip()
                if cid.isdigit():
                    existing_cids.add(cid)
        logger.info(f"Loaded {len(existing_cids):,} existing CIDs")
    
    # Create temporary directory for intermediate files
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_uci_file = Path(temp_dir) / "biological_ucis.txt"
        
        # First pass: Find UCIs from biological sources
        logger.info("First pass: Finding UCIs from biological sources...")
        biological_ucis = set()
        line_count = 0
        bio_source_counts = {src_id: 0 for src_id in BIOLOGICAL_SOURCE_IDS}
        
        with gzip.open(unichem_file, 'rt') as f:
            # Skip header
            next(f)
            
            for line in f:
                line_count += 1
                if line_count % 5000000 == 0:
                    logger.info(f"Processed {line_count:,} lines (first pass)...")
                
                parts = line.strip().split('\t')
                if len(parts) < 4:
                    continue
                
                uci = parts[0]
                src_id = int(parts[1]) if parts[1].isdigit() else None
                assignment = parts[3]
                
                # Only process assigned mappings from biological sources
                if src_id in BIOLOGICAL_SOURCE_IDS and assignment == '1':
                    biological_ucis.add(uci)
                    bio_source_counts[src_id] += 1
                    
                    # Write to temp file periodically to manage memory
                    if len(biological_ucis) >= 100000:
                        with open(temp_uci_file, 'a') as tmp:
                            for u in biological_ucis:
                                tmp.write(f"{u}\n")
                        biological_ucis.clear()
        
        # Write remaining UCIs
        if biological_ucis:
            with open(temp_uci_file, 'a') as tmp:
                for u in biological_ucis:
                    tmp.write(f"{u}\n")
        
        logger.info(f"First pass complete: processed {line_count:,} lines")
        for src_id, src_name in sorted(BIOLOGICAL_SOURCE_IDS.items()):
            count = bio_source_counts.get(src_id, 0)
            logger.info(f"  {src_name}: {count:,} compounds")
        
        # Load biological UCIs into a set for fast lookup
        logger.info("Loading biological UCIs for second pass...")
        biological_ucis_set = set()
        if temp_uci_file.exists():
            with open(temp_uci_file, 'r') as f:
                for line in f:
                    biological_ucis_set.add(line.strip())
        logger.info(f"Loaded {len(biological_ucis_set):,} unique biological UCIs")
        
        # Second pass: Extract PubChem CIDs for biological UCIs
        logger.info("Second pass: Extracting PubChem CIDs for biological compounds...")
        new_pubchem_cids = set()
        line_count = 0
        pubchem_count = 0
        matched_count = 0
        
        with gzip.open(unichem_file, 'rt') as f:
            # Skip header
            next(f)
            
            for line in f:
                line_count += 1
                if line_count % 5000000 == 0:
                    logger.info(f"Processed {line_count:,} lines (second pass), found {matched_count:,} biological PubChem CIDs...")
                
                parts = line.strip().split('\t')
                if len(parts) < 4:
                    continue
                
                uci = parts[0]
                src_id = int(parts[1]) if parts[1].isdigit() else None
                compound_id = parts[2]
                assignment = parts[3]
                
                # Check if this is a PubChem entry for a biological UCI
                if src_id == PUBCHEM_SOURCE_ID and assignment == '1':
                    pubchem_count += 1
                    if uci in biological_ucis_set and compound_id.isdigit():
                        new_pubchem_cids.add(compound_id)
                        matched_count += 1
                        
                        # Write in batches to manage memory
                        if len(new_pubchem_cids) >= 50000:
                            logger.info(f"Writing batch of {len(new_pubchem_cids):,} CIDs...")
                            with open(output_file, 'a') as out:
                                for cid in sorted(new_pubchem_cids, key=int):
                                    if cid not in existing_cids:
                                        out.write(f"{cid}\n")
                            new_pubchem_cids.clear()
        
        logger.info(f"Second pass complete: found {matched_count:,} biological PubChem CIDs")
        logger.info(f"Total PubChem entries processed: {pubchem_count:,}")
    
    # Combine with existing CIDs and write final output
    logger.info("Finalizing allowlist...")
    
    # Write any remaining new CIDs
    if new_pubchem_cids:
        with open(output_file, 'a') as out:
            for cid in sorted(new_pubchem_cids, key=int):
                if cid not in existing_cids:
                    out.write(f"{cid}\n")
    
    # Now read all CIDs and write sorted final list
    all_cids = existing_cids.copy()
    if output_file.exists():
        with open(output_file, 'r') as f:
            for line in f:
                cid = line.strip()
                if cid.isdigit():
                    all_cids.add(cid)
    
    # Write final sorted list
    logger.info(f"Writing final sorted allowlist with {len(all_cids):,} CIDs...")
    with open(output_file, 'w') as f:
        for cid in sorted(all_cids, key=int):
            f.write(f"{cid}\n")
    
    new_count = len(all_cids) - len(existing_cids)
    logger.info(f"\nComplete! Added {new_count:,} new CIDs from UniChem")
    logger.info(f"Total unique CIDs in allowlist: {len(all_cids):,}")


def main():
    """Main function."""
    # Define paths
    unichem_file = Path("/home/ubuntu/biomapper/data/unichem/reference.tsv.gz")
    existing_allowlist = Path("/home/ubuntu/biomapper/data/bio_relevant_cids.txt")
    output_file = Path("/home/ubuntu/biomapper/data/bio_relevant_cids_expanded.txt")
    
    # Check if UniChem file exists
    if not unichem_file.exists():
        logger.error(f"UniChem file not found at {unichem_file}")
        logger.info("Please download from: https://ftp.ebi.ac.uk/pub/databases/chembl/UniChem/data/table_dumps/reference.tsv.gz")
        return
    
    # Process the mappings
    process_unichem_reference_memory_efficient(unichem_file, existing_allowlist, output_file)


if __name__ == "__main__":
    main()
