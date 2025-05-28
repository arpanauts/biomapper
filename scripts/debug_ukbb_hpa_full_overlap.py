#!/usr/bin/env python3
"""Check full overlap between UKBB and HPA UniProt IDs"""

import pandas as pd
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# File paths
ukbb_file = "/procedure/data/local_data/HPP_PHENOAI_METADATA/UKBB_Protein_Meta.tsv"
hpa_file = "/home/ubuntu/biomapper/data/isb_osp/hpa_osps.csv"

try:
    # Read full UKBB file
    logger.info("Reading full UKBB file...")
    ukbb_df = pd.read_csv(ukbb_file, sep="\t", low_memory=False)
    logger.info(f"Total UKBB rows: {len(ukbb_df)}")
    
    # Extract all UniProt IDs from UKBB
    ukbb_uniprot_ids = set(ukbb_df['UniProt'].dropna().unique())
    logger.info(f"Total unique UniProt IDs in UKBB: {len(ukbb_uniprot_ids)}")
    
    # Read HPA file
    logger.info("\nReading HPA file...")
    hpa_df = pd.read_csv(hpa_file)
    logger.info(f"Total HPA rows: {len(hpa_df)}")
    
    # Extract UniProt IDs from HPA
    hpa_uniprot_ids = set(hpa_df['uniprot'].dropna().unique())
    logger.info(f"Total unique UniProt IDs in HPA: {len(hpa_uniprot_ids)}")
    
    # Find overlap
    logger.info("\n" + "="*60)
    logger.info("Analyzing overlap...")
    
    overlap = ukbb_uniprot_ids.intersection(hpa_uniprot_ids)
    ukbb_only = ukbb_uniprot_ids - hpa_uniprot_ids
    hpa_only = hpa_uniprot_ids - ukbb_uniprot_ids
    
    logger.info(f"\nOVERLAP STATISTICS:")
    logger.info(f"IDs in both UKBB and HPA: {len(overlap)} ({len(overlap)/len(ukbb_uniprot_ids)*100:.1f}% of UKBB)")
    logger.info(f"IDs only in UKBB: {len(ukbb_only)}")
    logger.info(f"IDs only in HPA: {len(hpa_only)}")
    
    if overlap:
        logger.info(f"\nFirst 20 overlapping IDs:")
        for i, uid in enumerate(sorted(list(overlap))[:20]):
            logger.info(f"  {i+1}. {uid}")
    else:
        logger.info("\nNO OVERLAP FOUND between UKBB and HPA UniProt IDs!")
        
    # Show some examples from each dataset
    logger.info("\n" + "="*60)
    logger.info("Sample IDs from each dataset:")
    logger.info("\nFirst 10 UKBB UniProt IDs:")
    for i, uid in enumerate(sorted(list(ukbb_uniprot_ids))[:10]):
        logger.info(f"  {uid}")
        
    logger.info("\nFirst 10 HPA UniProt IDs:")
    for i, uid in enumerate(sorted(list(hpa_uniprot_ids))[:10]):
        logger.info(f"  {uid}")

except Exception as e:
    logger.error(f"Error: {e}")
    import traceback
    traceback.print_exc()