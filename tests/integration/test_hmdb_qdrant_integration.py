"""Integration tests for HMDB Qdrant loading and search - Written FIRST for TDD."""

import pytest
from pathlib import Path
import tempfile
import xml.etree.ElementTree as ET
from typing import List, Dict, Any
from qdrant_client import QdrantClient
from qdrant_client.http import models


def create_test_hmdb_xml(num_metabolites: int = 10) -> Path:
    """Create a test HMDB XML file with sample metabolites."""
    # Sample metabolites with real-world-like data
    test_metabolites = [
        {
            'accession': 'HMDB0000001',
            'name': 'Spermidine',
            'description': 'Spermidine is a polyamine compound found in ribosomes and living tissues.',
            'chemical_formula': 'C7H19N3',
            'iupac_name': 'N-(3-aminopropyl)butane-1,4-diamine',
            'traditional_iupac': 'spermidine',
            'cas_registry_number': '124-20-9',
            'synonyms': ['1,5,10-Triazadecane', 'N-(3-Aminopropyl)-1,4-butanediamine']
        },
        {
            'accession': 'HMDB0006528',
            'name': '12,13-DiHOME',
            'description': '12,13-Dihydroxy-9Z-octadecenoic acid is an epoxy fatty acid.',
            'chemical_formula': 'C18H34O4',
            'iupac_name': '12,13-dihydroxyoctadec-9-enoic acid',
            'traditional_iupac': '12,13-DiHOME',
            'cas_registry_number': '263399-35-5',
            'synonyms': ['12,13-DHOME', '12,13-dihydroxy-9-octadecenoic acid']
        },
        {
            'accession': 'HMDB0003411',
            'name': 'S-1-Pyrroline-5-carboxylate',
            'description': 'S-1-Pyrroline-5-carboxylate is a metabolite in proline metabolism.',
            'chemical_formula': 'C5H7NO2',
            'iupac_name': '(S)-1-pyrroline-5-carboxylate',
            'traditional_iupac': 'S-1-pyrroline-5-carboxylate',
            'cas_registry_number': '2906-39-0',
            'synonyms': ['L-1-Pyrroline-5-carboxylate', 'S-P5C']
        },
        {
            'accession': 'HMDB0000875',
            'name': '1-Methylnicotinamide',
            'description': '1-Methylnicotinamide is a metabolite of nicotinamide.',
            'chemical_formula': 'C7H9N2O+',
            'iupac_name': '1-methylpyridin-1-ium-3-carboxamide',
            'traditional_iupac': '1-methylnicotinamide',
            'cas_registry_number': '114-33-0',
            'synonyms': ['N-Methylnicotinamide', 'Trigonellamide']
        },
        {
            'accession': 'HMDB0000067',
            'name': 'Cholesterol',
            'description': 'Cholesterol is a sterol and a lipid found in cell membranes.',
            'chemical_formula': 'C27H46O',
            'iupac_name': '(3β)-cholest-5-en-3-ol',
            'traditional_iupac': 'cholesterol',
            'cas_registry_number': '57-88-5',
            'synonyms': ['Cholesterin', 'Cholest-5-en-3β-ol']
        }
    ]
    
    # Create XML structure
    root = ET.Element("hmdb")
    
    # Add more metabolites if requested
    for i in range(num_metabolites):
        metabolite_data = test_metabolites[i % len(test_metabolites)].copy()
        if i >= len(test_metabolites):
            # Modify data for additional metabolites
            metabolite_data['accession'] = f'HMDB{i:07d}'
            metabolite_data['name'] = f"{metabolite_data['name']} variant {i}"
        
        metabolite = ET.SubElement(root, "metabolite")
        
        # Add all fields
        for field, value in metabolite_data.items():
            if field == 'synonyms':
                synonyms_elem = ET.SubElement(metabolite, "synonyms")
                for syn in value:
                    syn_elem = ET.SubElement(synonyms_elem, "synonym")
                    syn_elem.text = syn
            else:
                elem = ET.SubElement(metabolite, field)
                elem.text = value
    
    # Write to temporary file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False)
    tree = ET.ElementTree(root)
    tree.write(temp_file.name, encoding='unicode', xml_declaration=True)
    temp_file.close()
    
    return Path(temp_file.name)


@pytest.mark.integration
class TestHMDBQdrantIntegration:
    """Integration tests with real Qdrant instance - WRITE FIRST!"""
    
    @pytest.fixture
    async def setup_test_collection(self):
        """Setup test collection with sample data."""
        client = QdrantClient("localhost:6333")
        collection_name = "test_hmdb_metabolites"
        
        # Cleanup
        try:
            client.delete_collection(collection_name)
        except:
            pass
            
        yield collection_name
        
        # Cleanup after test
        try:
            client.delete_collection(collection_name)
        except:
            pass
    
    @pytest.mark.asyncio
    async def test_end_to_end_loading(self, setup_test_collection):
        """Test complete loading pipeline with small dataset."""
        from biomapper.processors.hmdb import HMDBProcessor
        from biomapper.loaders.hmdb_qdrant_loader import HMDBQdrantLoader
        
        # Create test XML with 10 metabolites
        test_xml = create_test_hmdb_xml(num_metabolites=10)
        
        try:
            # Initialize components
            processor = HMDBProcessor(test_xml)
            loader = HMDBQdrantLoader(
                processor=processor,
                collection_name=setup_test_collection
            )
            
            # Setup collection
            await loader.setup_collection()
            
            # Load data
            stats = await loader.load_metabolites()
            
            # Verify stats
            assert stats['total_processed'] == 10
            assert stats['total_errors'] == 0
            
            # Verify data was loaded
            client = QdrantClient("localhost:6333")
            collection_info = client.get_collection(setup_test_collection)
            assert collection_info.points_count == 10
            # This test should FAIL initially
            
        finally:
            # Cleanup temp file
            test_xml.unlink()
    
    @pytest.mark.asyncio
    async def test_arivale_compound_matching(self, setup_test_collection):
        """Test matching Arivale compounds against HMDB."""
        from biomapper.processors.hmdb import HMDBProcessor
        from biomapper.loaders.hmdb_qdrant_loader import HMDBQdrantLoader
        from biomapper.rag.metabolite_search import MetaboliteSearcher
        
        # Create test XML with our test metabolites
        test_xml = create_test_hmdb_xml(num_metabolites=5)
        
        try:
            # Load test data
            processor = HMDBProcessor(test_xml)
            loader = HMDBQdrantLoader(
                processor=processor,
                collection_name=setup_test_collection
            )
            await loader.setup_collection()
            await loader.load_metabolites()
            
            # Test data from metabolomics_mvp_progressive_enhancement.md
            arivale_compounds = [
                "spermidine",
                "12,13-DiHOME",
                "S-1-pyrroline-5-carboxylate",
                "1-methylnicotinamide"
            ]
            
            searcher = MetaboliteSearcher(collection_name=setup_test_collection)
            
            for compound in arivale_compounds:
                results = await searcher.search_by_name(compound)
                
                # Should find at least one match for known compounds
                assert len(results) > 0, f"No matches found for {compound}"
                
                # Top match should have reasonable score
                assert results[0]['score'] > 0.5, f"Low score for {compound}"
                
                # Verify correct match (case-insensitive)
                top_match_name = results[0]['name'].lower()
                query_lower = compound.lower()
                assert query_lower in top_match_name or top_match_name in query_lower, \
                    f"Unexpected match: {compound} -> {results[0]['name']}"
            # This test should FAIL initially
            
        finally:
            test_xml.unlink()
    
    @pytest.mark.asyncio
    async def test_search_quality_metrics(self, setup_test_collection):
        """Test search quality with various query types."""
        from biomapper.processors.hmdb import HMDBProcessor
        from biomapper.loaders.hmdb_qdrant_loader import HMDBQdrantLoader
        from biomapper.rag.metabolite_search import MetaboliteSearcher
        
        test_xml = create_test_hmdb_xml(num_metabolites=5)
        
        try:
            # Setup
            processor = HMDBProcessor(test_xml)
            loader = HMDBQdrantLoader(
                processor=processor,
                collection_name=setup_test_collection
            )
            await loader.setup_collection()
            await loader.load_metabolites()
            
            searcher = MetaboliteSearcher(collection_name=setup_test_collection)
            
            # Test exact match
            results = await searcher.search_by_name("Cholesterol")
            assert len(results) > 0
            assert results[0]['name'] == "Cholesterol"
            assert results[0]['score'] > 0.95  # Should be very high for exact match
            
            # Test synonym match
            results = await searcher.search_by_name("Cholesterin")  # Synonym of cholesterol
            assert len(results) > 0
            assert results[0]['name'] == "Cholesterol"
            assert results[0]['score'] > 0.85  # Should still be high
            
            # Test partial match
            results = await searcher.search_by_name("pyrroline")  # Part of S-1-Pyrroline-5-carboxylate
            assert len(results) > 0
            found_pyrroline = any("pyrroline" in r['name'].lower() for r in results)
            assert found_pyrroline
            
            # Test no match
            results = await searcher.search_by_name("completely-unknown-metabolite-xyz")
            assert len(results) == 0 or results[0]['score'] < 0.5
            # This test should FAIL initially
            
        finally:
            test_xml.unlink()
    
    @pytest.mark.asyncio
    async def test_batch_loading_performance(self, setup_test_collection):
        """Test that batch loading is efficient."""
        from biomapper.processors.hmdb import HMDBProcessor
        from biomapper.loaders.hmdb_qdrant_loader import HMDBQdrantLoader
        import time
        
        # Create larger test dataset
        test_xml = create_test_hmdb_xml(num_metabolites=100)
        
        try:
            processor = HMDBProcessor(test_xml)
            loader = HMDBQdrantLoader(
                processor=processor,
                collection_name=setup_test_collection,
                batch_size=50  # Test with specific batch size
            )
            
            await loader.setup_collection()
            
            start_time = time.time()
            stats = await loader.load_metabolites()
            load_time = time.time() - start_time
            
            # Should process all metabolites
            assert stats['total_processed'] == 100
            
            # Should be reasonably fast (less than 10 seconds for 100 metabolites)
            assert load_time < 10.0, f"Loading took {load_time:.2f}s"
            
            # Verify batch processing worked
            client = QdrantClient("localhost:6333")
            collection_info = client.get_collection(setup_test_collection)
            assert collection_info.points_count == 100
            # This test should FAIL initially
            
        finally:
            test_xml.unlink()
    
    @pytest.mark.asyncio
    async def test_error_recovery_during_loading(self, setup_test_collection):
        """Test that loader handles errors gracefully."""
        from biomapper.processors.hmdb import HMDBProcessor
        from biomapper.loaders.hmdb_qdrant_loader import HMDBQdrantLoader
        
        # Create XML with some invalid data
        root = ET.Element("hmdb")
        
        # Valid metabolite
        metabolite1 = ET.SubElement(root, "metabolite")
        ET.SubElement(metabolite1, "accession").text = "HMDB0000001"
        ET.SubElement(metabolite1, "name").text = "Valid Metabolite"
        
        # Invalid metabolite (missing required fields)
        metabolite2 = ET.SubElement(root, "metabolite")
        # No accession or name
        
        # Another valid metabolite
        metabolite3 = ET.SubElement(root, "metabolite")
        ET.SubElement(metabolite3, "accession").text = "HMDB0000003"
        ET.SubElement(metabolite3, "name").text = "Another Valid"
        
        # Write to temp file
        temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False)
        tree = ET.ElementTree(root)
        tree.write(temp_file.name, encoding='unicode', xml_declaration=True)
        temp_file.close()
        test_xml = Path(temp_file.name)
        
        try:
            processor = HMDBProcessor(test_xml)
            loader = HMDBQdrantLoader(
                processor=processor,
                collection_name=setup_test_collection
            )
            
            await loader.setup_collection()
            stats = await loader.load_metabolites()
            
            # Should process valid metabolites and track errors
            assert stats['total_processed'] == 2  # Two valid metabolites
            assert stats['total_errors'] >= 1  # At least one error
            
            # Verify only valid data was loaded
            client = QdrantClient("localhost:6333")
            collection_info = client.get_collection(setup_test_collection)
            assert collection_info.points_count == 2
            # This test should FAIL initially
            
        finally:
            test_xml.unlink()