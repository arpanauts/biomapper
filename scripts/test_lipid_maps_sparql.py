#!/usr/bin/env python3
"""
Test LIPID MAPS SPARQL endpoint to validate feasibility.
This script tests actual SPARQL queries against the LIPID MAPS endpoint
to understand capabilities, performance, and coverage potential.
"""

import time
import json
import requests
from typing import Dict, List, Tuple
import statistics

# LIPID MAPS SPARQL endpoint
SPARQL_ENDPOINT = "https://lipidmaps.org/sparql"

def execute_sparql_query(query: str, timeout: int = 10) -> Tuple[Dict, float]:
    """
    Execute a SPARQL query and return results with timing.
    
    Returns:
        Tuple of (results_dict, elapsed_time_seconds)
    """
    headers = {
        "Content-Type": "application/sparql-query",
        "Accept": "application/sparql-results+json"
    }
    
    start_time = time.time()
    try:
        response = requests.post(
            SPARQL_ENDPOINT, 
            data=query.encode('utf-8'),
            headers=headers,
            timeout=timeout
        )
        elapsed = time.time() - start_time
        
        if response.status_code == 200:
            return response.json(), elapsed
        else:
            print(f"Error {response.status_code}: {response.text[:200]}")
            return {"error": response.status_code}, elapsed
    except requests.Timeout:
        elapsed = time.time() - start_time
        print(f"Query timed out after {elapsed:.2f} seconds")
        return {"error": "timeout"}, elapsed
    except Exception as e:
        elapsed = time.time() - start_time
        print(f"Query failed: {e}")
        return {"error": str(e)}, elapsed


def test_basic_connectivity():
    """Test 1: Basic connectivity and simple query."""
    print("\n=== Test 1: Basic Connectivity ===")
    
    # Very simple query to test connectivity
    query = """
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?s ?label WHERE {
        ?s rdfs:label ?label .
    } LIMIT 1
    """
    
    result, elapsed = execute_sparql_query(query)
    
    if "error" not in result:
        print(f"✓ Connection successful! Query took {elapsed:.2f} seconds")
        if "results" in result and "bindings" in result["results"]:
            print(f"  Found {len(result['results']['bindings'])} result(s)")
            if result['results']['bindings']:
                first = result['results']['bindings'][0]
                print(f"  Sample: {first.get('label', {}).get('value', 'N/A')}")
    else:
        print(f"✗ Connection failed: {result['error']}")
    
    return elapsed if "error" not in result else None


def test_exact_name_match():
    """Test 2: Exact name matching for known compounds."""
    print("\n=== Test 2: Exact Name Matching ===")
    
    test_compounds = [
        "cholesterol",
        "palmitic acid",
        "oleic acid",
        "sphingomyelin",
        "phosphatidylcholine"
    ]
    
    times = []
    matches = 0
    
    for compound in test_compounds:
        # Note: Using STR() to convert to string and LCASE for case-insensitive
        query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?lipid ?label WHERE {{
            ?lipid rdfs:label ?label .
            FILTER(LCASE(STR(?label)) = LCASE("{compound}"))
        }} LIMIT 1
        """
        
        result, elapsed = execute_sparql_query(query)
        times.append(elapsed)
        
        if "error" not in result:
            bindings = result.get("results", {}).get("bindings", [])
            if bindings:
                matches += 1
                print(f"✓ '{compound}': Found match in {elapsed:.2f}s")
                print(f"    Result: {bindings[0].get('label', {}).get('value', 'N/A')}")
            else:
                print(f"✗ '{compound}': No match found ({elapsed:.2f}s)")
        else:
            print(f"✗ '{compound}': Query failed - {result['error']}")
    
    if times:
        print(f"\nSummary: {matches}/{len(test_compounds)} compounds matched")
        print(f"Average query time: {statistics.mean(times):.2f}s")
        print(f"Min/Max: {min(times):.2f}s / {max(times):.2f}s")
    
    return times


def test_fuzzy_matching():
    """Test 3: Fuzzy/partial matching capabilities."""
    print("\n=== Test 3: Fuzzy/Partial Matching ===")
    
    test_patterns = [
        ("cholest", "cholesterol variants"),
        ("palmit", "palmitic acid variants"),
        ("18:2", "linoleic acid notation"),
        ("sphingo", "sphingolipids"),
        ("PC(", "phosphatidylcholine notation")
    ]
    
    times = []
    
    for pattern, description in test_patterns:
        query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?lipid ?label WHERE {{
            ?lipid rdfs:label ?label .
            FILTER(CONTAINS(LCASE(STR(?label)), LCASE("{pattern}")))
        }} LIMIT 5
        """
        
        result, elapsed = execute_sparql_query(query)
        times.append(elapsed)
        
        if "error" not in result:
            bindings = result.get("results", {}).get("bindings", [])
            print(f"Pattern '{pattern}' ({description}): {len(bindings)} results in {elapsed:.2f}s")
            for binding in bindings[:2]:  # Show first 2 results
                print(f"  - {binding.get('label', {}).get('value', 'N/A')}")
        else:
            print(f"Pattern '{pattern}': Query failed - {result['error']}")
    
    if times:
        print(f"\nAverage fuzzy query time: {statistics.mean(times):.2f}s")
    
    return times


def test_batch_vs_individual():
    """Test 4: Compare batch UNION queries vs individual queries."""
    print("\n=== Test 4: Batch vs Individual Query Performance ===")
    
    test_compounds = ["cholesterol", "palmitic acid", "oleic acid"]
    
    # Test individual queries
    print("Testing individual queries...")
    individual_start = time.time()
    individual_results = []
    
    for compound in test_compounds:
        query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?lipid ?label WHERE {{
            ?lipid rdfs:label ?label .
            FILTER(LCASE(STR(?label)) = LCASE("{compound}"))
        }} LIMIT 1
        """
        result, _ = execute_sparql_query(query)
        if "error" not in result:
            individual_results.append(len(result.get("results", {}).get("bindings", [])))
    
    individual_time = time.time() - individual_start
    print(f"Individual queries total: {individual_time:.2f}s")
    
    # Test batch UNION query
    print("\nTesting batch UNION query...")
    union_parts = []
    for compound in test_compounds:
        union_parts.append(f"""
        {{
            ?lipid rdfs:label ?label .
            FILTER(LCASE(STR(?label)) = LCASE("{compound}"))
        }}
        """)
    
    batch_query = f"""
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    SELECT ?lipid ?label WHERE {{
        {" UNION ".join(union_parts)}
    }} LIMIT 10
    """
    
    batch_result, batch_time = execute_sparql_query(batch_query)
    
    if "error" not in batch_result:
        batch_count = len(batch_result.get("results", {}).get("bindings", []))
        print(f"Batch query: {batch_count} results in {batch_time:.2f}s")
    else:
        print(f"Batch query failed: {batch_result['error']}")
        batch_time = float('inf')
    
    # Compare
    print(f"\nComparison:")
    print(f"  Individual: {individual_time:.2f}s total")
    print(f"  Batch: {batch_time:.2f}s")
    if batch_time < individual_time:
        print(f"  Batch is {individual_time/batch_time:.1f}x faster")
    else:
        print(f"  Individual queries are {batch_time/individual_time:.1f}x faster")
    
    return individual_time, batch_time


def test_realistic_metabolite_names():
    """Test 5: Test with realistic metabolite names from actual data."""
    print("\n=== Test 5: Realistic Metabolite Names ===")
    
    # These are examples of actual metabolite names that might come from Stage 4
    realistic_names = [
        "Total cholesterol",  # Common variant
        "HDL cholesterol",    # Specific cholesterol type
        "Linoleic acid (18:2n6)",  # With notation
        "Arachidonic acid (20:4n6)",  # Fatty acid
        "Ceramide (d18:1/16:0)",  # Complex lipid notation
        "PC(36:2)",  # Phospholipid shorthand
        "LysoPC(18:0)",  # Lysophospholipid
        "TAG 52:2",  # Triacylglycerol
        "DHA",  # Common abbreviation
        "EPA",  # Common abbreviation
    ]
    
    times = []
    exact_matches = 0
    fuzzy_matches = 0
    
    for name in realistic_names:
        # Try exact match first
        exact_query = f"""
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT ?lipid ?label WHERE {{
            ?lipid rdfs:label ?label .
            FILTER(LCASE(STR(?label)) = LCASE("{name}"))
        }} LIMIT 1
        """
        
        result, elapsed = execute_sparql_query(exact_query)
        times.append(elapsed)
        
        if "error" not in result and result.get("results", {}).get("bindings"):
            exact_matches += 1
            print(f"✓ '{name}': Exact match in {elapsed:.2f}s")
        else:
            # Try fuzzy match
            # Extract core name (before parentheses)
            core_name = name.split('(')[0].strip()
            fuzzy_query = f"""
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            SELECT ?lipid ?label WHERE {{
                ?lipid rdfs:label ?label .
                FILTER(CONTAINS(LCASE(STR(?label)), LCASE("{core_name}")))
            }} LIMIT 3
            """
            
            result, elapsed = execute_sparql_query(fuzzy_query)
            times.append(elapsed)
            
            if "error" not in result and result.get("results", {}).get("bindings"):
                fuzzy_matches += 1
                print(f"≈ '{name}': Fuzzy match for '{core_name}' in {elapsed:.2f}s")
                for binding in result["results"]["bindings"][:1]:
                    print(f"    Found: {binding.get('label', {}).get('value', 'N/A')}")
            else:
                print(f"✗ '{name}': No match found")
    
    print(f"\n=== Summary ===")
    print(f"Exact matches: {exact_matches}/{len(realistic_names)} ({exact_matches/len(realistic_names)*100:.1f}%)")
    print(f"Fuzzy matches: {fuzzy_matches}/{len(realistic_names)} ({fuzzy_matches/len(realistic_names)*100:.1f}%)")
    total_matches = exact_matches + fuzzy_matches
    print(f"Total matches: {total_matches}/{len(realistic_names)} ({total_matches/len(realistic_names)*100:.1f}%)")
    
    if times:
        print(f"Average query time: {statistics.mean(times):.2f}s")
        print(f"Total time for {len(times)} queries: {sum(times):.2f}s")
    
    return exact_matches, fuzzy_matches, times


def main():
    """Run all tests and provide final assessment."""
    print("=" * 60)
    print("LIPID MAPS SPARQL Endpoint Validation")
    print("=" * 60)
    
    # Track overall results
    all_times = []
    
    # Test 1: Basic connectivity
    basic_time = test_basic_connectivity()
    if basic_time is None:
        print("\n❌ CRITICAL: Cannot connect to LIPID MAPS SPARQL endpoint")
        print("Recommendation: DO NOT PROCEED with implementation")
        return
    
    # Test 2: Exact matching
    exact_times = test_exact_name_match()
    all_times.extend(exact_times)
    
    # Test 3: Fuzzy matching
    fuzzy_times = test_fuzzy_matching()
    all_times.extend(fuzzy_times)
    
    # Test 4: Batch vs individual
    individual_time, batch_time = test_batch_vs_individual()
    
    # Test 5: Realistic names
    exact_matches, fuzzy_matches, realistic_times = test_realistic_metabolite_names()
    all_times.extend(realistic_times)
    
    # Final assessment
    print("\n" + "=" * 60)
    print("FINAL ASSESSMENT")
    print("=" * 60)
    
    if all_times:
        avg_time = statistics.mean(all_times)
        max_time = max(all_times)
        
        print(f"\nPerformance Metrics:")
        print(f"  Average query time: {avg_time:.2f}s")
        print(f"  Maximum query time: {max_time:.2f}s")
        print(f"  Total queries tested: {len(all_times)}")
        
        print(f"\nBatch Processing:")
        if batch_time < individual_time:
            print(f"  ✓ Batch queries are faster ({batch_time:.2f}s vs {individual_time:.2f}s)")
        else:
            print(f"  ✗ Individual queries are faster ({individual_time:.2f}s vs {batch_time:.2f}s)")
        
        print(f"\nCoverage Potential:")
        total_realistic = 10  # Number of realistic names tested
        total_matched = exact_matches + fuzzy_matches
        coverage_rate = total_matched / total_realistic * 100
        print(f"  Realistic name match rate: {coverage_rate:.1f}%")
        
        print(f"\n{'='*40}")
        print("GO/NO-GO DECISION CRITERIA:")
        print(f"{'='*40}")
        
        # Decision logic
        go_decision = True
        
        if avg_time > 2.0:
            print(f"  ✗ Average query time {avg_time:.2f}s > 2s threshold")
            go_decision = False
        else:
            print(f"  ✓ Average query time {avg_time:.2f}s < 2s threshold")
        
        if coverage_rate < 30:
            print(f"  ✗ Coverage rate {coverage_rate:.1f}% < 30% minimum")
            go_decision = False
        else:
            print(f"  ✓ Coverage rate {coverage_rate:.1f}% > 30% minimum")
        
        if max_time > 5.0:
            print(f"  ⚠ Warning: Max query time {max_time:.2f}s > 5s")
        
        print(f"\n{'='*40}")
        if go_decision:
            print("✅ RECOMMENDATION: PROCEED with implementation")
            print("   - Queries are responsive enough")
            print("   - Coverage potential justifies effort")
        else:
            print("❌ RECOMMENDATION: DO NOT PROCEED")
            print("   - Performance and/or coverage insufficient")
            print("   Consider alternative approaches:")
            print("   1. Static LIPID MAPS data export")
            print("   2. Focus on improving existing stages")
    
    else:
        print("❌ No successful queries - DO NOT PROCEED")


if __name__ == "__main__":
    main()