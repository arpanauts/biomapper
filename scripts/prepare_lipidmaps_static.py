#!/usr/bin/env python3
"""
Prepare static LIPID MAPS data for fast, reliable metabolite matching.

This script creates an optimized lookup structure from LIPID MAPS data,
enabling O(1) matching without any external dependencies.
"""

import pandas as pd
import json
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def generate_sample_lipidmaps_data():
    """
    Generate sample LIPID MAPS data for demonstration.
    In production, this would load from actual LIPID MAPS export.
    """
    # Sample data representing common lipids
    data = [
        # Sterols
        {"LM_ID": "LMST01010001", "COMMON_NAME": "Cholesterol", 
         "SYSTEMATIC_NAME": "cholest-5-en-3β-ol", "FORMULA": "C27H46O",
         "INCHIKEY": "HVYWMOMLDIMCQP-VXSCHHQBSA-N", "CATEGORY": "Sterol Lipids"},
        
        # Fatty Acids
        {"LM_ID": "LMFA01010001", "COMMON_NAME": "Palmitic acid",
         "SYSTEMATIC_NAME": "hexadecanoic acid", "FORMULA": "C16H32O2",
         "INCHIKEY": "IPCSVZSSVZVIGE-UHFFFAOYSA-N", "CATEGORY": "Fatty Acyls"},
        
        {"LM_ID": "LMFA01030002", "COMMON_NAME": "Oleic acid",
         "SYSTEMATIC_NAME": "(9Z)-octadecenoic acid", "FORMULA": "C18H34O2",
         "INCHIKEY": "ZQPPMHVWECSIRJ-KTKRTIGZSA-N", "CATEGORY": "Fatty Acyls"},
        
        {"LM_ID": "LMFA01030120", "COMMON_NAME": "Linoleic acid",
         "SYSTEMATIC_NAME": "(9Z,12Z)-octadecadienoic acid", "FORMULA": "C18H32O2",
         "INCHIKEY": "OYHQOLUKZRVURQ-HZJYTTRNSA-N", "CATEGORY": "Fatty Acyls",
         "SYNONYMS": "18:2n6;LA;18:2(9Z,12Z)"},
        
        {"LM_ID": "LMFA01030185", "COMMON_NAME": "DHA",
         "SYSTEMATIC_NAME": "(4Z,7Z,10Z,13Z,16Z,19Z)-docosahexaenoic acid", 
         "FORMULA": "C22H32O2", "CATEGORY": "Fatty Acyls",
         "SYNONYMS": "Docosahexaenoic acid;22:6n3;22:6(4Z,7Z,10Z,13Z,16Z,19Z)"},
        
        {"LM_ID": "LMFA01030841", "COMMON_NAME": "EPA",
         "SYSTEMATIC_NAME": "(5Z,8Z,11Z,14Z,17Z)-eicosapentaenoic acid",
         "FORMULA": "C20H30O2", "CATEGORY": "Fatty Acyls",
         "SYNONYMS": "Eicosapentaenoic acid;20:5n3;20:5(5Z,8Z,11Z,14Z,17Z)"},
        
        # Glycerolipids
        {"LM_ID": "LMGL03010001", "COMMON_NAME": "TAG(16:0/18:1/18:1)",
         "SYSTEMATIC_NAME": "1-palmitoyl-2,3-dioleoyl-glycerol", 
         "FORMULA": "C55H104O6", "CATEGORY": "Glycerolipids",
         "SYNONYMS": "TAG 52:2;Triacylglycerol(52:2)"},
        
        # Glycerophospholipids
        {"LM_ID": "LMGP01010001", "COMMON_NAME": "PC(16:0/18:1)",
         "SYSTEMATIC_NAME": "1-palmitoyl-2-oleoyl-sn-glycero-3-phosphocholine",
         "FORMULA": "C42H82NO8P", "CATEGORY": "Glycerophospholipids",
         "SYNONYMS": "PC(34:1);Phosphatidylcholine(34:1)"},
        
        {"LM_ID": "LMGP01050001", "COMMON_NAME": "LysoPC(18:0)",
         "SYSTEMATIC_NAME": "1-stearoyl-sn-glycero-3-phosphocholine",
         "FORMULA": "C26H54NO7P", "CATEGORY": "Glycerophospholipids",
         "SYNONYMS": "LPC(18:0);Lysophosphatidylcholine(18:0)"},
        
        # Sphingolipids
        {"LM_ID": "LMSP02010001", "COMMON_NAME": "Ceramide(d18:1/16:0)",
         "SYSTEMATIC_NAME": "N-palmitoyl-D-erythro-sphingosine",
         "FORMULA": "C34H67NO3", "CATEGORY": "Sphingolipids",
         "SYNONYMS": "Cer(d18:1/16:0);C16-Ceramide"},
        
        {"LM_ID": "LMSP03010001", "COMMON_NAME": "Sphingomyelin(d18:1/16:0)",
         "SYSTEMATIC_NAME": "N-palmitoyl-D-erythro-sphingosylphosphorylcholine",
         "FORMULA": "C39H79N2O6P", "CATEGORY": "Sphingolipids",
         "SYNONYMS": "SM(d18:1/16:0);SM(34:1)"},
        
        # Additional common metabolites
        {"LM_ID": "LMFA01010002", "COMMON_NAME": "Stearic acid",
         "SYSTEMATIC_NAME": "octadecanoic acid", "FORMULA": "C18H36O2",
         "CATEGORY": "Fatty Acyls", "SYNONYMS": "18:0"},
        
        {"LM_ID": "LMFA01030158", "COMMON_NAME": "Arachidonic acid",
         "SYSTEMATIC_NAME": "(5Z,8Z,11Z,14Z)-eicosatetraenoic acid",
         "FORMULA": "C20H32O2", "CATEGORY": "Fatty Acyls",
         "SYNONYMS": "AA;20:4n6;20:4(5Z,8Z,11Z,14Z)"},
    ]
    
    return pd.DataFrame(data)


def prepare_lipidmaps_indices(df: pd.DataFrame) -> dict:
    """
    Create optimized lookup indices from LIPID MAPS data.
    
    Returns multiple index types for different matching strategies:
    - exact_names: Direct name matches
    - normalized_names: Lowercase, stripped names
    - synonyms: Alternative names and notations
    - inchikeys: Chemical structure matching
    - formulas: Molecular formula matching
    """
    
    indices = {
        "exact_names": {},
        "normalized_names": {},
        "synonyms": {},
        "inchikeys": {},
        "formulas": {},
        "lipid_data": {}  # Store full records for matched IDs
    }
    
    for _, row in df.iterrows():
        lipid_id = row['LM_ID']
        
        # Store full record
        indices["lipid_data"][lipid_id] = row.to_dict()
        
        # Exact name index
        if pd.notna(row.get('COMMON_NAME')):
            name = row['COMMON_NAME']
            indices["exact_names"][name] = lipid_id
            
            # Normalized name (lowercase, stripped)
            normalized = name.lower().strip()
            indices["normalized_names"][normalized] = lipid_id
        
        # Systematic name as alternative
        if pd.notna(row.get('SYSTEMATIC_NAME')):
            sys_name = row['SYSTEMATIC_NAME']
            indices["synonyms"][sys_name] = lipid_id
            indices["normalized_names"][sys_name.lower().strip()] = lipid_id
        
        # Process synonyms
        if pd.notna(row.get('SYNONYMS')):
            for synonym in str(row['SYNONYMS']).split(';'):
                syn = synonym.strip()
                if syn:
                    indices["synonyms"][syn] = lipid_id
                    indices["normalized_names"][syn.lower()] = lipid_id
        
        # InChIKey index
        if pd.notna(row.get('INCHIKEY')):
            indices["inchikeys"][row['INCHIKEY']] = lipid_id
        
        # Formula index
        if pd.notna(row.get('FORMULA')):
            indices["formulas"][row['FORMULA']] = lipid_id
    
    return indices


def save_indices(indices: dict, output_dir: Path = Path("data")):
    """Save indices to JSON file for fast loading."""
    
    output_dir.mkdir(exist_ok=True)
    
    # Version the file by date
    version = datetime.now().strftime("%Y%m")
    output_file = output_dir / f"lipidmaps_static_{version}.json"
    
    # Save as JSON for portability
    with open(output_file, 'w') as f:
        json.dump(indices, f, indent=2)
    
    logger.info(f"Saved LIPID MAPS indices to {output_file}")
    
    # Also save statistics
    stats = {
        "version": version,
        "timestamp": datetime.now().isoformat(),
        "total_lipids": len(indices["lipid_data"]),
        "exact_names": len(indices["exact_names"]),
        "normalized_names": len(indices["normalized_names"]),
        "synonyms": len(indices["synonyms"]),
        "inchikeys": len(indices["inchikeys"]),
        "formulas": len(indices["formulas"])
    }
    
    stats_file = output_dir / f"lipidmaps_stats_{version}.json"
    with open(stats_file, 'w') as f:
        json.dump(stats, f, indent=2)
    
    logger.info(f"Statistics saved to {stats_file}")
    
    return output_file


def validate_indices(indices: dict):
    """Validate the prepared indices."""
    
    logger.info("Validating LIPID MAPS indices...")
    
    # Test exact match
    test_cases = [
        ("exact", "Cholesterol", "LMST01010001"),
        ("normalized", "cholesterol", "LMST01010001"),
        ("synonym", "18:2n6", "LMFA01030120"),
        ("synonym", "DHA", "LMFA01030185"),
    ]
    
    for match_type, query, expected_id in test_cases:
        if match_type == "exact":
            found_id = indices["exact_names"].get(query)
        elif match_type == "normalized":
            found_id = indices["normalized_names"].get(query)
        elif match_type == "synonym":
            found_id = indices["synonyms"].get(query)
        
        if found_id == expected_id:
            logger.info(f"✓ {match_type} match test passed: {query} -> {found_id}")
        else:
            logger.error(f"✗ {match_type} match test failed: {query} -> {found_id} (expected {expected_id})")


def main():
    """Main execution function."""
    
    logger.info("=" * 60)
    logger.info("Preparing Static LIPID MAPS Data")
    logger.info("=" * 60)
    
    # Step 1: Load or generate data
    logger.info("\n1. Loading LIPID MAPS data...")
    
    # Check if actual LIPID MAPS export exists
    lipidmaps_file = Path("LMSD_export.csv")
    if lipidmaps_file.exists():
        logger.info(f"Loading from {lipidmaps_file}")
        df = pd.read_csv(lipidmaps_file)
    else:
        logger.info("Using sample data (download actual LIPID MAPS export for production)")
        df = generate_sample_lipidmaps_data()
    
    logger.info(f"Loaded {len(df)} lipid records")
    
    # Step 2: Create indices
    logger.info("\n2. Creating lookup indices...")
    indices = prepare_lipidmaps_indices(df)
    
    logger.info(f"Created indices:")
    logger.info(f"  - Exact names: {len(indices['exact_names'])}")
    logger.info(f"  - Normalized names: {len(indices['normalized_names'])}")
    logger.info(f"  - Synonyms: {len(indices['synonyms'])}")
    logger.info(f"  - InChIKeys: {len(indices['inchikeys'])}")
    logger.info(f"  - Formulas: {len(indices['formulas'])}")
    
    # Step 3: Validate
    logger.info("\n3. Validating indices...")
    validate_indices(indices)
    
    # Step 4: Save
    logger.info("\n4. Saving indices...")
    output_file = save_indices(indices)
    
    logger.info("\n" + "=" * 60)
    logger.info("✅ Static LIPID MAPS data prepared successfully!")
    logger.info(f"Output: {output_file}")
    logger.info("=" * 60)
    
    # Performance test
    logger.info("\n5. Performance test...")
    import time
    
    test_queries = ["Cholesterol", "DHA", "18:2n6", "unknown_metabolite"] * 250  # 1000 queries
    
    start = time.time()
    for query in test_queries:
        # Simulate lookup
        _ = indices["exact_names"].get(query) or \
            indices["normalized_names"].get(query.lower()) or \
            indices["synonyms"].get(query)
    elapsed = time.time() - start
    
    logger.info(f"Processed {len(test_queries)} queries in {elapsed:.3f} seconds")
    logger.info(f"Average: {elapsed/len(test_queries)*1000:.2f} ms per query")
    logger.info(f"Throughput: {len(test_queries)/elapsed:.0f} queries/second")


if __name__ == "__main__":
    main()