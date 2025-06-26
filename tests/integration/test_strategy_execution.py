"""Integration test for UKBB-HPA strategy execution via API endpoint."""

import pytest
import httpx
from typing import Dict, Any


BASE_URL = "http://localhost:8000"


@pytest.mark.asyncio
@pytest.mark.skip(reason="Requires running server at localhost:8000")
async def test_ukbb_hpa_overlap_strategy():
    """Test the UKBB_HPA_PROTEIN_OVERLAP_ANALYSIS strategy through the API."""
    
    # Define sample data with overlapping and unique protein identifiers
    sample_data = {
        "ukbb_protein_ids": [
            "P12345",  # Overlapping
            "Q67890",  # Overlapping
            "P98765",  # Unique to UKBB
            "Q11111",  # Unique to UKBB
            "P22222",  # Overlapping
        ],
        "hpa_protein_ids": [
            "P12345",  # Overlapping
            "Q67890",  # Overlapping
            "P33333",  # Unique to HPA
            "Q44444",  # Unique to HPA
            "P22222",  # Overlapping
            "P55555",  # Unique to HPA
        ]
    }
    
    # Expected overlapping proteins
    expected_overlap = {"P12345", "Q67890", "P22222"}
    
    # Create the request payload
    request_payload = {
        "context": sample_data
    }
    
    # Make the API request
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/strategies/UKBB_HPA_PROTEIN_OVERLAP_ANALYSIS/execute",
            json=request_payload
        )
    
    # Assert successful response
    assert response.status_code == 200, f"Expected status 200, got {response.status_code}: {response.text}"
    
    # Parse the response
    response_data = response.json()
    
    # Assert that results contain overlap_results
    assert "results" in response_data, "Response should contain 'results' key"
    assert "overlap_results" in response_data["results"], "Results should contain 'overlap_results' key"
    
    overlap_results = response_data["results"]["overlap_results"]
    
    # Assert the structure of overlap_results
    assert "overlapping_proteins" in overlap_results, "overlap_results should contain 'overlapping_proteins'"
    assert "ukbb_unique_proteins" in overlap_results, "overlap_results should contain 'ukbb_unique_proteins'"
    assert "hpa_unique_proteins" in overlap_results, "overlap_results should contain 'hpa_unique_proteins'"
    assert "statistics" in overlap_results, "overlap_results should contain 'statistics'"
    
    # Verify overlapping proteins
    overlapping_proteins = set(overlap_results["overlapping_proteins"])
    assert overlapping_proteins == expected_overlap, f"Expected overlap {expected_overlap}, got {overlapping_proteins}"
    
    # Verify unique proteins
    ukbb_unique = set(overlap_results["ukbb_unique_proteins"])
    hpa_unique = set(overlap_results["hpa_unique_proteins"])
    
    expected_ukbb_unique = {"P98765", "Q11111"}
    expected_hpa_unique = {"P33333", "Q44444", "P55555"}
    
    assert ukbb_unique == expected_ukbb_unique, f"Expected UKBB unique {expected_ukbb_unique}, got {ukbb_unique}"
    assert hpa_unique == expected_hpa_unique, f"Expected HPA unique {expected_hpa_unique}, got {hpa_unique}"
    
    # Verify statistics
    stats = overlap_results["statistics"]
    assert stats["total_ukbb_proteins"] == 5, f"Expected 5 UKBB proteins, got {stats['total_ukbb_proteins']}"
    assert stats["total_hpa_proteins"] == 6, f"Expected 6 HPA proteins, got {stats['total_hpa_proteins']}"
    assert stats["overlapping_count"] == 3, f"Expected 3 overlapping proteins, got {stats['overlapping_count']}"
    assert stats["ukbb_unique_count"] == 2, f"Expected 2 UKBB unique proteins, got {stats['ukbb_unique_count']}"
    assert stats["hpa_unique_count"] == 3, f"Expected 3 HPA unique proteins, got {stats['hpa_unique_count']}"
    
    # Verify overlap percentage is calculated correctly
    expected_ukbb_overlap_pct = (3 / 5) * 100
    expected_hpa_overlap_pct = (3 / 6) * 100
    
    assert abs(stats["ukbb_overlap_percentage"] - expected_ukbb_overlap_pct) < 0.01, \
        f"Expected UKBB overlap percentage ~{expected_ukbb_overlap_pct:.2f}, got {stats['ukbb_overlap_percentage']}"
    assert abs(stats["hpa_overlap_percentage"] - expected_hpa_overlap_pct) < 0.01, \
        f"Expected HPA overlap percentage ~{expected_hpa_overlap_pct:.2f}, got {stats['hpa_overlap_percentage']}"