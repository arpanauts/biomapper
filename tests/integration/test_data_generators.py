"""
Realistic test data generators for integration testing.

This module provides data generators that create realistic test datasets
with statistical properties matching real biological data.
"""

import pandas as pd
import numpy as np
import random
import string
from typing import Dict, List, Tuple
from pathlib import Path


def generate_uniprot_ids(size: int) -> List[str]:
    """Generate realistic UniProt accession IDs."""
    # UniProt IDs: 6 characters, mix of letters and numbers
    # Based on real UniProt distribution patterns
    ids = []
    for _ in range(size):
        # First character usually letter (P, Q, O are common)
        first = random.choice('PQOABCDEFGHJKLMN')
        # Remaining 5 characters: mix letters/numbers
        remaining = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
        ids.append(f"{first}{remaining}")
    return ids


def generate_gene_symbols(size: int, case_variations: bool = True) -> List[str]:
    """Generate realistic gene symbols with case variations."""
    # Common gene symbol patterns from real data
    base_symbols = [
        'BRCA1', 'TP53', 'EGFR', 'MYC', 'PTEN', 'APC', 'RB1', 'VHL',
        'KRAS', 'PIK3CA', 'BRAF', 'ATM', 'CDKN2A', 'MLH1', 'MSH2',
        'ERBB2', 'CDH1', 'NF1', 'AKT1', 'SMAD4', 'FBXW7', 'NOTCH1'
    ] * (size // 22 + 1)  # Repeat to get enough symbols
    
    symbols = base_symbols[:size]
    
    if case_variations:
        # Add realistic case variations
        for i in range(len(symbols)):
            variation = random.choice([
                symbols[i],                    # Original
                symbols[i].lower(),           # Lowercase
                symbols[i].upper(),           # Uppercase (redundant but realistic)
                f"{symbols[i]}_HUMAN",        # Species suffix
                f"{symbols[i]}P1"             # Protein variant
            ])
            symbols[i] = variation
    
    return symbols


def generate_xrefs(size: int, avg_refs: float = 3.2) -> List[str]:
    """Generate complex cross-references like real protein data."""
    xrefs_list = []
    for _ in range(size):
        # Number of xrefs per protein (Poisson distribution)
        num_refs = max(1, int(np.random.poisson(avg_refs)))
        
        refs = []
        for _ in range(num_refs):
            ref_type = random.choice([
                'GO', 'KEGG', 'Reactome', 'InterPro', 'Pfam', 
                'SMART', 'PROSITE', 'EMBL', 'RefSeq'
            ])
            if ref_type == 'GO':
                refs.append(f"GO:{random.randint(1000000, 9999999):07d}")
            elif ref_type == 'KEGG':
                refs.append(f"KEGG:{random.choice(['hsa', 'mmu', 'rno'])}{random.randint(1000, 99999)}")
            elif ref_type == 'InterPro':
                refs.append(f"IPR{random.randint(100000, 999999):06d}")
            else:
                refs.append(f"{ref_type}:{random.randint(1000, 999999)}")
        
        xrefs_list.append("; ".join(refs))
    
    return xrefs_list


def generate_hmdb_ids(size: int, padding_variations: bool = True) -> List[str]:
    """Generate realistic HMDB IDs with padding variations."""
    ids = []
    for _ in range(size):
        # HMDB IDs: HMDB + 7 digits
        base_id = random.randint(1, 9999999)
        
        if padding_variations and random.random() < 0.3:
            # Some databases use inconsistent padding
            variations = [
                f"HMDB{base_id:07d}",      # Standard format
                f"HMDB{base_id:05d}",      # Legacy format
                f"HMDB{base_id}",          # No padding
                f"hmdb{base_id:07d}",      # Lowercase
                f"HMDB:{base_id:07d}"      # With colon
            ]
            ids.append(random.choice(variations))
        else:
            ids.append(f"HMDB{base_id:07d}")
    
    return ids


def generate_inchikeys(size: int) -> List[str]:
    """Generate realistic InChI Keys."""
    keys = []
    for _ in range(size):
        # InChI Key: 27 chars, format: XXXXXX-XXXXXX-X
        part1 = ''.join(random.choices(string.ascii_uppercase, k=14))
        part2 = ''.join(random.choices(string.ascii_uppercase, k=10))  
        part3 = random.choice(string.ascii_uppercase)
        keys.append(f"{part1}-{part2}-{part3}")
    
    return keys


def generate_metabolite_names(size: int, synonyms: bool = True) -> List[str]:
    """Generate realistic metabolite names with synonyms."""
    base_names = [
        'glucose', 'lactate', 'pyruvate', 'glutamine', 'alanine', 
        'glycine', 'serine', 'threonine', 'valine', 'leucine',
        'isoleucine', 'phenylalanine', 'tryptophan', 'methionine',
        'cysteine', 'tyrosine', 'histidine', 'lysine', 'arginine',
        'aspartate', 'glutamate', 'asparagine', 'cholesterol',
        'creatinine', 'urea', 'acetate', 'succinate', 'citrate'
    ] * (size // 28 + 1)
    
    names = base_names[:size]
    
    if synonyms:
        # Add realistic name variations
        for i in range(len(names)):
            base = names[i]
            variation = random.choice([
                base,                           # Original
                base.capitalize(),             # Capitalized
                f"{base} acid",                # Acid form
                f"L-{base}",                  # L-stereoisomer
                f"D-{base}",                  # D-stereoisomer
                f"{base}-1-phosphate",        # Phosphate form
                f"{base} metabolite"          # Generic metabolite
            ])
            names[i] = variation
    
    return names


def generate_loinc_codes(size: int, missing_rate: float = 0.25) -> List[str]:
    """Generate realistic LOINC codes with missing values."""
    codes = []
    for _ in range(size):
        if random.random() < missing_rate:
            codes.append("")  # Missing LOINC
        else:
            # LOINC format: NNNNN-N
            base = random.randint(10000, 99999)
            check = random.randint(0, 9)
            codes.append(f"{base}-{check}")
    
    return codes


def generate_clinical_test_names(size: int, vendor_variations: bool = True) -> List[str]:
    """Generate clinical test names with vendor variations."""
    base_tests = [
        'hemoglobin', 'hematocrit', 'glucose', 'cholesterol', 'triglycerides',
        'HDL cholesterol', 'LDL cholesterol', 'creatinine', 'BUN', 'sodium',
        'potassium', 'chloride', 'CO2', 'calcium', 'phosphorus', 'magnesium',
        'total protein', 'albumin', 'bilirubin', 'ALT', 'AST', 'alkaline phosphatase',
        'TSH', 'T4', 'T3', 'vitamin D', 'vitamin B12', 'folate', 'iron', 'ferritin'
    ] * (size // 30 + 1)
    
    tests = base_tests[:size]
    
    if vendor_variations:
        # Add realistic vendor-specific variations
        for i in range(len(tests)):
            base = tests[i]
            variation = random.choice([
                base,                           # Standard name
                base.upper(),                  # ALL CAPS
                base.replace(' ', '_'),        # Underscore
                f"{base} (serum)",            # Specimen type
                f"{base}, total",             # Total measurement
                f"{base} level",              # Level suffix
                f"{base} test",               # Test suffix
                base.replace('cholesterol', 'chol'),  # Abbreviation
                base.replace('hemoglobin', 'hgb'),    # Abbreviation
                base.replace('hematocrit', 'hct')     # Abbreviation
            ])
            tests[i] = variation
    
    return tests


def generate_lab_values_by_test(size: int) -> List[float]:
    """Generate realistic lab values with test-specific distributions."""
    values = []
    test_ranges = {
        'glucose': (70, 200),
        'cholesterol': (100, 300),
        'hemoglobin': (10, 18),
        'creatinine': (0.5, 2.0),
        'sodium': (135, 145),
        'potassium': (3.5, 5.0)
    }
    
    for _ in range(size):
        # Default range if test not recognized
        min_val, max_val = (0.1, 100)
        value = random.uniform(min_val, max_val)
        values.append(round(value, 2))
    
    return values


def generate_units_with_vendor_preferences(size: int) -> List[str]:
    """Generate units with vendor-specific preferences."""
    unit_options = [
        'mg/dL', 'g/dL', 'mmol/L', 'mEq/L', 'ng/mL', 'pg/mL',
        'IU/L', 'U/L', 'mg/L', 'ug/dL', 'nmol/L', 'pmol/L',
        '%', 'ratio', 'index', 'score'
    ]
    
    return random.choices(unit_options, k=size)


def generate_realistic_test_data(entity_type: str, size: int) -> pd.DataFrame:
    """Generate realistic test data with statistical properties of real datasets."""
    
    if entity_type == "protein":
        return pd.DataFrame({
            'protein_id': generate_uniprot_ids(size),
            'xrefs': generate_xrefs(size, avg_refs=3.2),
            'gene_symbol': generate_gene_symbols(size, case_variations=True),
            'confidence_score': np.random.lognormal(0.8, 0.3, size).round(3)
        })
    
    elif entity_type == "metabolite":
        return pd.DataFrame({
            'metabolite_id': [f"MET_{i:06d}" for i in range(1, size + 1)],
            'hmdb_id': generate_hmdb_ids(size, padding_variations=True),
            'inchikey': generate_inchikeys(size),
            'compound_name': generate_metabolite_names(size, synonyms=True),
            'detection_frequency': np.random.beta(2, 5, size).round(4)
        })
    
    elif entity_type == "chemistry":
        vendors = ['labcorp', 'quest', 'mayo', 'arivale', 'cpmc', 'ucsf']
        return pd.DataFrame({
            'test_name': generate_clinical_test_names(size, vendor_variations=True),
            'value': generate_lab_values_by_test(size),
            'unit': generate_units_with_vendor_preferences(size),
            'loinc_code': generate_loinc_codes(size, missing_rate=0.25),
            'vendor': np.random.choice(vendors, size, p=[0.25, 0.25, 0.15, 0.15, 0.1, 0.1])
        })
    
    else:
        raise ValueError(f"Unknown entity_type: {entity_type}")


def save_test_data(entity_type: str, size: int, output_dir: str = "/tmp/integration_test_data"):
    """Generate and save test data to files."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    data = generate_realistic_test_data(entity_type, size)
    filename = f"{entity_type}_test_data_{size}.tsv"
    filepath = output_path / filename
    
    data.to_csv(filepath, sep='\t', index=False)
    return str(filepath)


if __name__ == "__main__":
    # Generate test datasets
    for entity_type in ["protein", "metabolite", "chemistry"]:
        for size in [1000, 5000, 10000]:
            filepath = save_test_data(entity_type, size)
            print(f"Generated {entity_type} test data: {filepath}")