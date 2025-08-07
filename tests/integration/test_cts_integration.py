import pytest
import asyncio
from biomapper.mapping.clients.cts_client import CTSClient, ScoringAlgorithm


@pytest.mark.integration
@pytest.mark.asyncio
class TestCTSIntegration:
    """Integration tests with real CTS API - WRITE FIRST!"""
    
    @pytest.fixture
    async def client(self):
        """Create real CTS client."""
        client = CTSClient({
            'rate_limit_per_second': 5,  # Respectful rate limit for tests
            'timeout_seconds': 30
        })
        await client.initialize()
        yield client
        await client.close()
    
    async def test_real_conversion_inchikey_to_name(self, client):
        """Test real conversion from InChIKey to Chemical Name."""
        # L-Alanine InChIKey
        result = await client.convert(
            "QNAYBMKLOCPYGJ-REOHCLBHSA-N",
            "InChIKey",
            "Chemical Name"
        )
        
        assert "L-Alanine" in result
        # This test should FAIL initially
    
    async def test_real_batch_conversion(self, client):
        """Test real batch conversion with metabolites."""
        # Common metabolites
        identifiers = ["HMDB0000177", "HMDB0000691"]  # L-Histidine, Malonic acid
        
        results = await client.convert_batch(
            identifiers,
            "HMDB",
            ["Chemical Name", "InChIKey", "KEGG"]
        )
        
        # Verify we got results for both
        assert len(results) == 2
        assert all(id in results for id in identifiers)
        
        # Check L-Histidine
        assert "L-Histidine" in results["HMDB0000177"].get("Chemical Name", [])
        # This test should FAIL initially
    
    async def test_real_scoring_algorithm(self, client):
        """Test real InChIKey scoring."""
        scores = await client.score_inchikeys(
            "glucose",
            "Chemical Name",
            algorithm=ScoringAlgorithm.BIOLOGICAL
        )
        
        assert len(scores) > 0
        assert all(0 <= score.score <= 1 for score in scores)
        # Scores should be descending
        assert all(scores[i].score >= scores[i+1].score for i in range(len(scores)-1))
        # This test should FAIL initially
    
    async def test_real_biological_counts(self, client):
        """Test real biological database counts."""
        # L-Alanine InChIKey
        counts = await client.count_biological_ids("QNAYBMKLOCPYGJ-REOHCLBHSA-N")
        
        assert counts.total > 0
        assert counts.kegg >= 0
        assert counts.hmdb >= 0
        # This test should FAIL initially
    
    async def test_metabolomics_use_case(self, client):
        """Test real-world metabolomics identifier conversion."""
        # Arivale metabolite examples
        test_cases = [
            ("HMDB0000161", "HMDB"),  # L-Alanine
            ("C00041", "KEGG"),        # L-Alanine
            ("5793", "PubChem CID")    # L-Alanine
        ]
        
        for identifier, id_type in test_cases:
            # Convert to multiple formats
            result = await client.enrich_metabolite(
                identifier,
                id_type,
                ["Chemical Name", "InChIKey", "HMDB", "KEGG", "PubChem CID"]
            )
            
            # Should get at least the chemical name
            assert "Chemical Name" in result["conversions"]
            assert len(result["conversions"]["Chemical Name"]) > 0
            
            # Should have consistent InChIKey
            if "InChIKey" in result["conversions"]:
                inchikeys = result["conversions"]["InChIKey"]
                assert all("QNAYBMKLOCPYGJ" in key for key in inchikeys)
        # This test should FAIL initially