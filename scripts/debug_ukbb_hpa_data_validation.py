#!/usr/bin/env python3
"""Debug script to validate UKBB to HPA mapping data overlap"""

import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# File paths
ukbb_file = "/procedure/data/local_data/HPP_PHENOAI_METADATA/UKBB_Protein_Meta.tsv"
hpa_file = "/home/ubuntu/biomapper/data/isb_osp/hpa_osps.csv"

try:
    # Read UKBB file (first 10 rows only, as the script does)
    logger.info("Reading UKBB file...")
    ukbb_df = pd.read_csv(ukbb_file, sep="\t", low_memory=False)
    ukbb_df = ukbb_df.head(10)
    logger.info(f"UKBB columns: {ukbb_df.columns.tolist()}")
    
    # Extract UniProt IDs from UKBB
    if 'UniProt' in ukbb_df.columns:
        ukbb_uniprot_ids = ukbb_df['UniProt'].dropna().unique().tolist()
        logger.info(f"\nFound {len(ukbb_uniprot_ids)} unique UniProt IDs in first 10 UKBB rows:")
        for i, uid in enumerate(ukbb_uniprot_ids[:10]):  # Show first 10
            logger.info(f"  {i+1}. '{uid}'")
    else:
        logger.error(f"ERROR: 'UniProt' column not found in UKBB file!")
        logger.info(f"Available columns: {ukbb_df.columns.tolist()}")
        exit(1)
    
    # Read HPA file
    logger.info("\n" + "="*60)
    logger.info("Reading HPA file...")
    hpa_df = pd.read_csv(hpa_file)
    logger.info(f"HPA columns: {hpa_df.columns.tolist()}")
    logger.info(f"Total HPA rows: {len(hpa_df)}")
    
    # Extract UniProt IDs from HPA
    if 'uniprot' in hpa_df.columns:
        hpa_uniprot_ids = set(hpa_df['uniprot'].dropna().unique())
        logger.info(f"Total unique UniProt IDs in HPA: {len(hpa_uniprot_ids)}")
        
        # Show first 10 HPA UniProt IDs
        logger.info("\nFirst 10 HPA UniProt IDs:")
        for i, uid in enumerate(list(hpa_uniprot_ids)[:10]):
            logger.info(f"  {i+1}. '{uid}'")
    else:
        logger.error(f"ERROR: 'uniprot' column not found in HPA file!")
        logger.info(f"Available columns: {hpa_df.columns.tolist()}")
        exit(1)
    
    # Check overlap
    logger.info("\n" + "="*60)
    logger.info("Checking overlap between UKBB and HPA UniProt IDs...")
    
    found_ids = []
    not_found_ids = []
    
    for ukbb_id in ukbb_uniprot_ids:
        if ukbb_id in hpa_uniprot_ids:
            found_ids.append(ukbb_id)
        else:
            not_found_ids.append(ukbb_id)
    
    logger.info(f"\nRESULTS:")
    logger.info(f"Total UKBB IDs checked: {len(ukbb_uniprot_ids)}")
    logger.info(f"Found in HPA: {len(found_ids)} ({len(found_ids)/len(ukbb_uniprot_ids)*100:.1f}%)")
    logger.info(f"NOT found in HPA: {len(not_found_ids)} ({len(not_found_ids)/len(ukbb_uniprot_ids)*100:.1f}%)")
    
    if found_ids:
        logger.info(f"\nUKBB IDs FOUND in HPA:")
        for uid in found_ids:
            logger.info(f"  ✓ '{uid}'")
    
    if not_found_ids:
        logger.info(f"\nUKBB IDs NOT FOUND in HPA:")
        for uid in not_found_ids:
            logger.info(f"  ✗ '{uid}'")
    
    # Additional check: case sensitivity and whitespace
    logger.info("\n" + "="*60)
    logger.info("Checking for potential data format issues...")
    
    # Convert both sets to lowercase for case-insensitive comparison
    hpa_uniprot_ids_lower = set(uid.lower() for uid in hpa_uniprot_ids if pd.notna(uid))
    
    case_mismatch_found = []
    for ukbb_id in not_found_ids:
        if ukbb_id.lower() in hpa_uniprot_ids_lower:
            case_mismatch_found.append(ukbb_id)
    
    if case_mismatch_found:
        logger.info(f"\nPotential CASE MISMATCH issues found for {len(case_mismatch_found)} IDs:")
        for uid in case_mismatch_found:
            logger.info(f"  ! '{uid}' (check case sensitivity)")
    
    # Check for whitespace issues
    whitespace_issues = []
    for ukbb_id in ukbb_uniprot_ids:
        if ukbb_id != ukbb_id.strip():
            whitespace_issues.append(f"'{ukbb_id}' has whitespace")
    
    if whitespace_issues:
        logger.info(f"\nWhitespace issues in UKBB IDs:")
        for issue in whitespace_issues:
            logger.info(f"  ! {issue}")
            
    # Sample some actual HPA values to understand format
    logger.info("\n" + "="*60)
    logger.info("Sample HPA data to understand format:")
    sample_hpa = hpa_df.head(5)
    logger.info("\n" + sample_hpa.to_string())

except Exception as e:
    logger.error(f"Error: {e}")
    import traceback
    traceback.print_exc()