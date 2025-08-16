"""Generate synthetic biological data for testing."""

import pandas as pd
import random
import string
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta


class BiologicalDataGenerator:
    """Generate realistic synthetic biological data for testing.
    
    Creates test datasets that mimic real biological data patterns including:
    - UniProt accessions with proper format
    - Gene symbols and names
    - Cross-references (xrefs) with various database prefixes
    - Metabolite identifiers (HMDB, CHEBI, InChIKey)
    - Clinical test codes (LOINC)
    """
    
    # Realistic database prefixes
    PROTEIN_DB_PREFIXES = ['UniProtKB:', 'PR:', 'ENSEMBL:', 'RefSeq:', 'NCBIGene:']
    METABOLITE_DB_PREFIXES = ['HMDB:', 'CHEBI:', 'KEGG:', 'PubChem:']
    
    # Gene name patterns
    GENE_PREFIXES = ['SLC', 'ATP', 'GATA', 'MYC', 'TP', 'BRCA', 'EGFR', 'KRAS']
    
    @staticmethod
    def generate_uniprot_ids(count: int, 
                           include_isoforms: bool = True,
                           include_obsolete: bool = False) -> List[str]:
        """Generate realistic UniProt accession numbers.
        
        Args:
            count: Number of IDs to generate
            include_isoforms: Whether to include isoform variants (e.g., P12345-2)
            include_obsolete: Whether to include obsolete patterns
            
        Returns:
            List of UniProt accession numbers
        """
        ids = []
        
        for i in range(count):
            # UniProt pattern: [OPQ][0-9][A-Z0-9]{3}[0-9]
            # Or newer: [OPQ][0-9][A-Z0-9]{4}[0-9]
            prefix = random.choice(['O', 'P', 'Q'])
            
            # Occasionally generate the longer new format
            if random.random() < 0.2:
                # New format: 10 characters
                id_str = f"{prefix}{random.randint(0,9)}"
                id_str += ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=4))
                id_str += str(random.randint(0,9))
            else:
                # Classic format: 6 characters
                id_str = f"{prefix}{random.randint(0,9)}"
                id_str += ''.join(random.choices('ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=3))
                id_str += str(random.randint(0,9))
            
            # Add isoforms occasionally
            if include_isoforms and random.random() < 0.15:
                id_str += f"-{random.randint(1,5)}"
            
            # Simulate obsolete entries
            if include_obsolete and random.random() < 0.05:
                id_str = f"OBSOLETE_{id_str}"
            
            ids.append(id_str)
        
        return ids
    
    @staticmethod
    def generate_gene_symbols(count: int) -> List[str]:
        """Generate realistic gene symbols.
        
        Args:
            count: Number of gene symbols to generate
            
        Returns:
            List of gene symbols
        """
        symbols = []
        
        for i in range(count):
            if random.random() < 0.7:
                # Use known prefix pattern
                prefix = random.choice(BiologicalDataGenerator.GENE_PREFIXES)
                suffix = random.choice(['', str(random.randint(1,20)), 
                                      random.choice(['A', 'B', 'C']) + str(random.randint(1,5))])
                symbols.append(f"{prefix}{suffix}")
            else:
                # Generate random pattern
                length = random.randint(3, 6)
                symbol = ''.join(random.choices(string.ascii_uppercase, k=length))
                if random.random() < 0.3:
                    symbol += str(random.randint(1, 9))
                symbols.append(symbol)
        
        return symbols
    
    @staticmethod
    def generate_xrefs_field(identifiers: List[str], 
                           separator: str = '||',
                           include_empty: float = 0.2) -> str:
        """Generate realistic cross-references field.
        
        Args:
            identifiers: List of identifiers to include
            separator: Separator between references
            include_empty: Probability of returning empty string
            
        Returns:
            Formatted xrefs string
        """
        if random.random() < include_empty:
            return ''
        
        # Select random subset of identifiers
        num_refs = min(len(identifiers), random.randint(1, 4))
        selected = random.sample(identifiers, num_refs)
        
        # Add database prefixes
        parts = []
        for idx in selected:
            prefix = random.choice(BiologicalDataGenerator.PROTEIN_DB_PREFIXES)
            parts.append(f"{prefix}{idx}")
        
        return separator.join(parts)
    
    @staticmethod
    def generate_metabolite_ids(count: int, id_type: str = 'mixed') -> List[str]:
        """Generate metabolite identifiers.
        
        Args:
            count: Number of IDs to generate
            id_type: Type of IDs ('hmdb', 'chebi', 'inchikey', 'mixed')
            
        Returns:
            List of metabolite identifiers
        """
        ids = []
        
        for i in range(count):
            if id_type == 'hmdb' or (id_type == 'mixed' and random.random() < 0.3):
                # HMDB format: HMDB0000001
                ids.append(f"HMDB{random.randint(0, 999999):07d}")
            elif id_type == 'chebi' or (id_type == 'mixed' and random.random() < 0.5):
                # CHEBI format: CHEBI:12345
                ids.append(f"CHEBI:{random.randint(1, 999999)}")
            else:
                # InChIKey format (simplified)
                part1 = ''.join(random.choices(string.ascii_uppercase, k=14))
                part2 = ''.join(random.choices(string.ascii_uppercase, k=10))
                ids.append(f"{part1}-{part2}-N")
        
        return ids
    
    @staticmethod
    def generate_test_dataset(rows: int, 
                            dataset_type: str = 'source',
                            include_nulls: bool = True) -> pd.DataFrame:
        """Generate complete test dataset.
        
        Args:
            rows: Number of rows to generate
            dataset_type: Type of dataset ('source', 'target', 'metabolite')
            include_nulls: Whether to include null values
            
        Returns:
            DataFrame with test data
        """
        if dataset_type == 'source':
            uniprot_ids = BiologicalDataGenerator.generate_uniprot_ids(rows)
            gene_symbols = BiologicalDataGenerator.generate_gene_symbols(rows)
            
            df = pd.DataFrame({
                'uniprot': uniprot_ids,
                'gene_name': gene_symbols,
                'description': [f"Protein {i} description - {gene}" 
                              for i, gene in enumerate(gene_symbols)],
                'organism': random.choices(['Homo sapiens', 'Mus musculus', 
                                          'Rattus norvegicus'], k=rows),
                'length': [random.randint(50, 5000) for _ in range(rows)]
            })
            
        elif dataset_type == 'target':
            # Generate target dataset with xrefs
            uniprot_pool = BiologicalDataGenerator.generate_uniprot_ids(rows // 2)
            
            df = pd.DataFrame({
                'id': [f"NCBIGene:{random.randint(1, 999999)}" for _ in range(rows)],
                'name': [f"Entity {i}" for i in range(rows)],
                'xrefs': [
                    BiologicalDataGenerator.generate_xrefs_field(
                        random.sample(uniprot_pool, min(3, len(uniprot_pool)))
                    ) for _ in range(rows)
                ],
                'category': random.choices(['protein', 'gene', 'complex'], k=rows),
                'synonyms': [
                    '|'.join(random.sample(
                        BiologicalDataGenerator.generate_gene_symbols(5), 
                        random.randint(0, 3)
                    )) for _ in range(rows)
                ]
            })
            
        elif dataset_type == 'metabolite':
            metabolite_ids = BiologicalDataGenerator.generate_metabolite_ids(rows)
            
            df = pd.DataFrame({
                'id': metabolite_ids,
                'name': [f"Metabolite {i}" for i in range(rows)],
                'formula': [f"C{random.randint(1,50)}H{random.randint(1,100)}O{random.randint(0,20)}" 
                           for _ in range(rows)],
                'mass': [random.uniform(50, 1000) for _ in range(rows)],
                'category': random.choices(['Amino acid', 'Lipid', 'Carbohydrate', 
                                          'Nucleotide', 'Cofactor'], k=rows)
            })
        
        else:
            raise ValueError(f"Unknown dataset_type: {dataset_type}")
        
        # Introduce some null values
        if include_nulls and rows > 10:
            null_columns = random.sample(list(df.columns), min(2, len(df.columns) - 1))
            for col in null_columns:
                null_indices = random.sample(range(rows), max(1, rows // 20))
                df.loc[null_indices, col] = None
        
        return df
    
    @staticmethod
    def generate_edge_cases() -> Dict[str, pd.DataFrame]:
        """Generate datasets with known edge cases.
        
        Returns:
            Dictionary of DataFrames with edge cases
        """
        return {
            'empty': pd.DataFrame(),
            
            'single_row': pd.DataFrame({
                'id': ['P12345'],
                'name': ['Single protein']
            }),
            
            'duplicates': pd.DataFrame({
                'id': ['P12345', 'P12345', 'Q67890', 'Q67890'],
                'name': ['Protein A', 'Protein A', 'Protein B', 'Protein B']
            }),
            
            'special_chars': pd.DataFrame({
                'id': ['P12345-1', 'Q6EMK4', 'O15*#', 'P99999_HUMAN'],
                'name': ["Protein with-dash", "Special case", 
                        "With*special#chars", "With_underscore"]
            }),
            
            'missing_values': pd.DataFrame({
                'id': ['P12345', None, 'Q67890', ''],
                'name': ['Protein A', 'Protein B', None, 'Protein D'],
                'xrefs': ['UniProtKB:P12345', '', None, '||']
            }),
            
            'malformed_xrefs': pd.DataFrame({
                'id': ['1', '2', '3', '4'],
                'xrefs': [
                    'UniProtKB:P12345||UniProtKB:Q67890',  # Normal
                    'UniProtKBP12345',  # Missing colon
                    '||UniProtKB:P12345||',  # Extra separators
                    'UniProtKB:P12345||:Q67890||PR'  # Incomplete entries
                ]
            }),
            
            'isoforms': pd.DataFrame({
                'id': ['P12345', 'P12345-1', 'P12345-2', 'Q67890', 'Q67890-1'],
                'name': ['Main form', 'Isoform 1', 'Isoform 2', 
                         'Another main', 'Another isoform']
            }),
            
            'obsolete': pd.DataFrame({
                'id': ['P12345', 'OBSOLETE_Q67890', 'DEPRECATED_O11111', 'A0A000'],
                'status': ['active', 'obsolete', 'deprecated', 'active']
            })
        }
    
    @staticmethod
    def generate_performance_test_data(sizes: List[int]) -> Dict[int, pd.DataFrame]:
        """Generate datasets of increasing sizes for performance testing.
        
        Args:
            sizes: List of dataset sizes to generate
            
        Returns:
            Dictionary mapping size to DataFrame
        """
        datasets = {}
        
        for size in sizes:
            # Generate with consistent properties for fair comparison
            datasets[size] = BiologicalDataGenerator.generate_test_dataset(
                size, 
                'source',
                include_nulls=False  # Avoid nulls for performance testing
            )
        
        return datasets