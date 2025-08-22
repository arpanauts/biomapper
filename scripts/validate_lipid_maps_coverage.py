#!/usr/bin/env python3
"""
Analyze unmapped metabolites to determine LIPID MAPS coverage potential.
This script examines actual unmapped metabolites from Stage 4 to understand:
1. What percentage are likely lipids
2. Whether LIPID MAPS SPARQL is worth implementing
"""

import pandas as pd
import json
from pathlib import Path
from typing import Dict, List, Tuple

def generate_sample_unmapped_metabolites() -> pd.DataFrame:
    """
    Generate a realistic sample of unmapped metabolites based on typical Stage 4 output.
    In production, this would load actual unmapped data from the pipeline.
    """
    # Sample unmapped metabolites that might come from Stage 4
    # Based on typical metabolomics platforms (Nightingale, Metabolon, etc.)
    unmapped_data = [
        # Lipids that might match
        {"identifier": "Total cholesterol", "SUPER_PATHWAY": "Lipid", "SUB_PATHWAY": "Sterol"},
        {"identifier": "HDL cholesterol", "SUPER_PATHWAY": "Lipid", "SUB_PATHWAY": "Sterol"},
        {"identifier": "LDL cholesterol", "SUPER_PATHWAY": "Lipid", "SUB_PATHWAY": "Sterol"},
        {"identifier": "Triglycerides", "SUPER_PATHWAY": "Lipid", "SUB_PATHWAY": "Glycerolipid"},
        {"identifier": "18:2n6", "SUPER_PATHWAY": "Lipid", "SUB_PATHWAY": "Fatty Acid"},
        {"identifier": "20:4n6", "SUPER_PATHWAY": "Lipid", "SUB_PATHWAY": "Fatty Acid"},
        {"identifier": "DHA", "SUPER_PATHWAY": "Lipid", "SUB_PATHWAY": "Fatty Acid"},
        {"identifier": "EPA", "SUPER_PATHWAY": "Lipid", "SUB_PATHWAY": "Fatty Acid"},
        {"identifier": "Ceramide (d18:1/16:0)", "SUPER_PATHWAY": "Lipid", "SUB_PATHWAY": "Sphingolipid"},
        {"identifier": "PC(36:2)", "SUPER_PATHWAY": "Lipid", "SUB_PATHWAY": "Phospholipid"},
        {"identifier": "LysoPC(18:0)", "SUPER_PATHWAY": "Lipid", "SUB_PATHWAY": "Phospholipid"},
        {"identifier": "TAG 52:2", "SUPER_PATHWAY": "Lipid", "SUB_PATHWAY": "Glycerolipid"},
        
        # Non-lipids that wouldn't match
        {"identifier": "Glucose", "SUPER_PATHWAY": "Carbohydrate", "SUB_PATHWAY": "Sugar"},
        {"identifier": "Lactate", "SUPER_PATHWAY": "Energy", "SUB_PATHWAY": "Glycolysis"},
        {"identifier": "Pyruvate", "SUPER_PATHWAY": "Energy", "SUB_PATHWAY": "Glycolysis"},
        {"identifier": "Citrate", "SUPER_PATHWAY": "Energy", "SUB_PATHWAY": "TCA Cycle"},
        {"identifier": "Alanine", "SUPER_PATHWAY": "Amino Acid", "SUB_PATHWAY": "Alanine Metabolism"},
        {"identifier": "Glutamine", "SUPER_PATHWAY": "Amino Acid", "SUB_PATHWAY": "Glutamine Metabolism"},
        {"identifier": "Tyrosine", "SUPER_PATHWAY": "Amino Acid", "SUB_PATHWAY": "Tyrosine Metabolism"},
        {"identifier": "Tryptophan", "SUPER_PATHWAY": "Amino Acid", "SUB_PATHWAY": "Tryptophan Metabolism"},
        {"identifier": "Creatinine", "SUPER_PATHWAY": "Amino Acid", "SUB_PATHWAY": "Creatine Metabolism"},
        {"identifier": "Urea", "SUPER_PATHWAY": "Amino Acid", "SUB_PATHWAY": "Urea Cycle"},
        {"identifier": "Uric acid", "SUPER_PATHWAY": "Nucleotide", "SUB_PATHWAY": "Purine Metabolism"},
        {"identifier": "Bilirubin", "SUPER_PATHWAY": "Cofactors and Vitamins", "SUB_PATHWAY": "Heme Metabolism"},
        {"identifier": "Albumin", "SUPER_PATHWAY": "Peptide", "SUB_PATHWAY": "Protein"},
        {"identifier": "3-Hydroxybutyrate", "SUPER_PATHWAY": "Lipid", "SUB_PATHWAY": "Ketone Body"},
        {"identifier": "Acetoacetate", "SUPER_PATHWAY": "Lipid", "SUB_PATHWAY": "Ketone Body"},
        
        # Clinical measurements that are complex
        {"identifier": "GlycA", "SUPER_PATHWAY": "Xenobiotics", "SUB_PATHWAY": "Clinical Marker"},
        {"identifier": "hs-CRP", "SUPER_PATHWAY": "Peptide", "SUB_PATHWAY": "Inflammation"},
        {"identifier": "IL-6", "SUPER_PATHWAY": "Peptide", "SUB_PATHWAY": "Cytokine"},
    ]
    
    return pd.DataFrame(unmapped_data)


def analyze_lipid_coverage(df: pd.DataFrame) -> Dict:
    """
    Analyze the unmapped metabolites to determine lipid coverage potential.
    """
    total_unmapped = len(df)
    
    # Identify likely lipids
    lipid_indicators = ["Lipid", "Fatty Acid", "Steroid", "Sphingolipid", 
                       "Phospholipid", "Glycerolipid", "Sterol"]
    
    # Filter for likely lipids
    likely_lipids = df[df['SUPER_PATHWAY'].isin(lipid_indicators) | 
                      df['SUB_PATHWAY'].isin(lipid_indicators)]
    
    # Also check for lipid-like names (backup method)
    lipid_keywords = ['cholesterol', 'triglyceride', 'fatty', 'lipid', 
                     'ceramide', r'PC\(', r'PE\(', 'TAG', 'DHA', 'EPA', 
                     'sphingo', 'phosphatidyl', 'lyso']
    
    name_based_lipids = df[df['identifier'].str.lower().str.contains(
        '|'.join(lipid_keywords), na=False, regex=True)]
    
    # Combine both methods (union)
    all_likely_lipids = pd.concat([likely_lipids, name_based_lipids]).drop_duplicates()
    
    # Categorize by confidence
    high_confidence_lipids = likely_lipids
    medium_confidence_lipids = all_likely_lipids[~all_likely_lipids.index.isin(likely_lipids.index)]
    
    # Calculate percentages
    results = {
        'total_unmapped': total_unmapped,
        'high_confidence_lipids': len(high_confidence_lipids),
        'medium_confidence_lipids': len(medium_confidence_lipids),
        'total_likely_lipids': len(all_likely_lipids),
        'high_confidence_percentage': (len(high_confidence_lipids) / total_unmapped * 100) if total_unmapped > 0 else 0,
        'total_lipid_percentage': (len(all_likely_lipids) / total_unmapped * 100) if total_unmapped > 0 else 0,
        'lipid_details': all_likely_lipids.to_dict('records')
    }
    
    return results


def estimate_sparql_impact(coverage_analysis: Dict, sparql_match_rate: float = 0.5) -> Dict:
    """
    Estimate the impact of adding LIPID MAPS SPARQL based on coverage analysis.
    
    Args:
        coverage_analysis: Results from analyze_lipid_coverage
        sparql_match_rate: Estimated match rate from SPARQL testing (default 50%)
    """
    total_unmapped = coverage_analysis['total_unmapped']
    likely_lipids = coverage_analysis['total_likely_lipids']
    
    # Estimate matches based on SPARQL test results
    estimated_matches = int(likely_lipids * sparql_match_rate)
    
    # Calculate improvement
    improvement_percentage = (estimated_matches / total_unmapped * 100) if total_unmapped > 0 else 0
    
    # Time estimate (based on ~3s per query average from testing)
    query_time_per_metabolite = 3.0  # seconds
    total_query_time = likely_lipids * query_time_per_metabolite
    
    return {
        'estimated_new_matches': estimated_matches,
        'improvement_percentage': improvement_percentage,
        'estimated_query_time_seconds': total_query_time,
        'queries_needed': likely_lipids,
        'cost_benefit_ratio': improvement_percentage / (total_query_time / 60) if total_query_time > 0 else 0  # % improvement per minute
    }


def main():
    """Analyze coverage potential and make recommendation."""
    print("=" * 60)
    print("LIPID MAPS Coverage Feasibility Analysis")
    print("=" * 60)
    
    # Load or generate unmapped metabolites
    print("\n1. Loading unmapped metabolites...")
    
    # Check if we have actual unmapped data
    unmapped_files = list(Path(".").glob("**/stage_4_unmapped*.csv"))
    unmapped_files.extend(list(Path(".").glob("**/final_unmapped*.csv")))
    
    if unmapped_files:
        print(f"Found {len(unmapped_files)} unmapped data files")
        # Load the most recent one
        df = pd.read_csv(unmapped_files[0])
        print(f"Loaded {len(df)} unmapped metabolites from {unmapped_files[0]}")
    else:
        print("No unmapped data files found. Using sample data...")
        df = generate_sample_unmapped_metabolites()
        print(f"Generated {len(df)} sample unmapped metabolites")
    
    # Analyze lipid coverage
    print("\n2. Analyzing lipid coverage...")
    coverage = analyze_lipid_coverage(df)
    
    print(f"\nCoverage Analysis:")
    print(f"  Total unmapped metabolites: {coverage['total_unmapped']}")
    print(f"  High confidence lipids: {coverage['high_confidence_lipids']} ({coverage['high_confidence_percentage']:.1f}%)")
    print(f"  Total likely lipids: {coverage['total_likely_lipids']} ({coverage['total_lipid_percentage']:.1f}%)")
    
    if coverage['total_likely_lipids'] > 0:
        print(f"\n  Sample lipids identified:")
        for lipid in coverage['lipid_details'][:5]:
            print(f"    - {lipid['identifier']} ({lipid.get('SUPER_PATHWAY', 'Unknown')})")
    
    # Estimate SPARQL impact
    print("\n3. Estimating SPARQL impact...")
    
    # Use actual match rate from SPARQL testing (50% from our tests)
    sparql_match_rate = 0.5
    impact = estimate_sparql_impact(coverage, sparql_match_rate)
    
    print(f"\nImpact Estimation (based on {sparql_match_rate*100:.0f}% SPARQL match rate):")
    print(f"  Estimated new matches: {impact['estimated_new_matches']}")
    print(f"  Coverage improvement: {impact['improvement_percentage']:.1f}%")
    print(f"  Estimated query time: {impact['estimated_query_time_seconds']:.0f} seconds ({impact['estimated_query_time_seconds']/60:.1f} minutes)")
    print(f"  Cost-benefit ratio: {impact['cost_benefit_ratio']:.2f}% improvement per minute")
    
    # Make recommendation
    print("\n" + "=" * 60)
    print("RECOMMENDATION")
    print("=" * 60)
    
    # Decision criteria
    min_lipid_percentage = 10  # Minimum % of unmapped that should be lipids
    min_improvement = 5  # Minimum % overall improvement
    max_query_time = 180  # Maximum acceptable query time in seconds
    min_cost_benefit = 1.0  # Minimum % improvement per minute
    
    proceed = True
    reasons = []
    
    if coverage['total_lipid_percentage'] < min_lipid_percentage:
        proceed = False
        reasons.append(f"Only {coverage['total_lipid_percentage']:.1f}% of unmapped are lipids (minimum: {min_lipid_percentage}%)")
    
    if impact['improvement_percentage'] < min_improvement:
        proceed = False
        reasons.append(f"Would only improve coverage by {impact['improvement_percentage']:.1f}% (minimum: {min_improvement}%)")
    
    if impact['estimated_query_time_seconds'] > max_query_time:
        proceed = False
        reasons.append(f"Would take {impact['estimated_query_time_seconds']:.0f}s to run (maximum: {max_query_time}s)")
    
    if impact['cost_benefit_ratio'] < min_cost_benefit:
        proceed = False
        reasons.append(f"Cost-benefit ratio of {impact['cost_benefit_ratio']:.2f}% per minute is too low (minimum: {min_cost_benefit}%)")
    
    if proceed:
        print("✅ PROCEED WITH IMPLEMENTATION")
        print(f"\nPositive factors:")
        print(f"  • {coverage['total_lipid_percentage']:.1f}% of unmapped are lipids")
        print(f"  • Would improve coverage by {impact['improvement_percentage']:.1f}%")
        print(f"  • Query time of {impact['estimated_query_time_seconds']:.0f}s is acceptable")
        print(f"  • Cost-benefit ratio of {impact['cost_benefit_ratio']:.2f}% per minute is good")
    else:
        print("❌ DO NOT PROCEED WITH IMPLEMENTATION")
        print(f"\nReasons:")
        for reason in reasons:
            print(f"  • {reason}")
        
        print(f"\nAlternative recommendations:")
        print("  1. Download static LIPID MAPS data (no SPARQL needed)")
        print("  2. Focus on improving Stage 1-4 matching rates")
        print("  3. Investigate other metabolite databases with better APIs")
    
    # Save results
    results = {
        'coverage_analysis': coverage,
        'impact_estimation': impact,
        'recommendation': 'PROCEED' if proceed else 'DO NOT PROCEED',
        'reasons': reasons
    }
    
    output_file = "lipid_maps_feasibility_results.json"
    with open(output_file, 'w') as f:
        # Convert DataFrame to dict for JSON serialization
        if 'lipid_details' in results['coverage_analysis']:
            del results['coverage_analysis']['lipid_details']  # Remove detailed data for JSON
        json.dump(results, f, indent=2)
    
    print(f"\nResults saved to {output_file}")
    
    return proceed


if __name__ == "__main__":
    proceed = main()
    exit(0 if proceed else 1)