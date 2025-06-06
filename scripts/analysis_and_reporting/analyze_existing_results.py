#!/usr/bin/env python
"""
Analyze the results of the name resolver on real metabolite data.

This script analyzes the three TSV files with name resolver results and
generates statistics on how well the resolver performed.
"""

import pandas as pd
import os

# Paths to the three output files
CHEMISTRIES_OUTPUT_PATH = "/home/ubuntu/biomapper/chemistries_metadata_with_resolver.tsv"
UKBB_NMR_OUTPUT_PATH = "/home/ubuntu/biomapper/UKBB_NMR_Meta_with_resolver.tsv"
METABOLOMICS_OUTPUT_PATH = "/home/ubuntu/biomapper/metabolomics_metadata_with_resolver.tsv"

# Results analysis summary path
ANALYSIS_REPORT_PATH = "/home/ubuntu/biomapper/name_resolver_analysis.md"

def analyze_resolver_results(file_path, name_column, existing_id_column=None):
    """
    Analyze the resolver results for a given file.
    
    Args:
        file_path: Path to the TSV file with resolver results
        name_column: Name of the column containing the entity names
        existing_id_column: Name of the column containing existing IDs, if any
        
    Returns:
        Dictionary with analysis results
    """
    print(f"Analyzing {file_path}...")
    
    # Read the file, handling commented lines if needed
    if "metabolomics" in file_path or "chemistries" in file_path:
        df = pd.read_csv(file_path, sep='\t', comment='#', quotechar='"')
    else:
        df = pd.read_csv(file_path, sep='\t')
    
    # Count total number of entities
    total = len(df)
    
    # Count successful resolutions for each target database
    results = {
        "file": os.path.basename(file_path),
        "total": total,
        "name_column": name_column,
        "target_dbs": {}
    }
    
    for target_db in ["PUBCHEM", "CHEBI", "HMDB"]:
        # Column names for the resolver results
        if "metabolomics" in file_path:
            id_column = f"{target_db}_Resolver_IDs"
            confidence_column = f"{target_db}_Resolver_Confidence"
        else:
            id_column = f"{target_db}_IDs"
            confidence_column = f"{target_db}_Confidence"
        
        # Check if columns exist
        if id_column not in df.columns or confidence_column not in df.columns:
            print(f"Warning: {id_column} or {confidence_column} not found in {file_path}")
            continue
        
        # Count non-empty results
        df[id_column] = df[id_column].fillna("")
        successful = df[id_column].str.len() > 0
        successful_count = successful.sum()
        
        # Calculate success rate
        success_rate = successful_count / total * 100
        
        # Calculate average number of IDs per successful mapping
        if successful_count > 0:
            # Handle comma-separated lists
            avg_ids = df[successful][id_column].apply(
                lambda x: len(x.split(',')) if pd.notna(x) and x else 0
            ).mean()
        else:
            avg_ids = 0
        
        # Calculate average confidence for successful mappings
        avg_confidence = df[successful][confidence_column].mean() if successful_count > 0 else 0
        
        # Gather results for this target database
        results["target_dbs"][target_db] = {
            "successful": successful_count,
            "success_rate": success_rate,
            "avg_ids": avg_ids,
            "avg_confidence": avg_confidence
        }
    
    # Analyze agreement with existing IDs if available
    if existing_id_column and existing_id_column in df.columns:
        for target_db in ["PUBCHEM", "CHEBI", "HMDB"]:
            # Skip if the existing ID column doesn't match this target DB
            if target_db.lower() not in existing_id_column.lower():
                continue
            
            # Column name for the resolver results
            if "metabolomics" in file_path:
                id_column = f"{target_db}_Resolver_IDs"
            else:
                id_column = f"{target_db}_IDs"
            
            # Skip if column doesn't exist
            if id_column not in df.columns:
                continue
            
            # Convert existing IDs to strings
            df[existing_id_column] = df[existing_id_column].astype(str)
            
            # Count agreements (where the existing ID is in the resolver results)
            agreements = 0
            for i, row in df.iterrows():
                existing_id = str(row[existing_id_column])
                resolved_ids = str(row[id_column])
                
                if existing_id and existing_id != "nan" and resolved_ids:
                    # Check if the existing ID is in the resolver results
                    if existing_id in resolved_ids.split(','):
                        agreements += 1
            
            # Calculate agreement rate
            has_existing_id = (df[existing_id_column] != "") & (df[existing_id_column] != "nan")
            existing_id_count = has_existing_id.sum()
            
            if existing_id_count > 0:
                agreement_rate = agreements / existing_id_count * 100
            else:
                agreement_rate = 0
            
            # Add agreement results
            results["target_dbs"][target_db]["agreements"] = agreements
            results["target_dbs"][target_db]["existing_id_count"] = existing_id_count
            results["target_dbs"][target_db]["agreement_rate"] = agreement_rate
    
    return results

def generate_markdown_report(results):
    """
    Generate a markdown report from the analysis results.
    
    Args:
        results: List of result dictionaries from analyze_resolver_results
        
    Returns:
        Markdown report as a string
    """
    report = "# Name Resolver Performance Analysis\n\n"
    
    for result in results:
        report += f"## File: {result['file']}\n"
        report += f"**Total entries:** {result['total']}  \n"
        report += f"**Name column:** {result['name_column']}\n\n"
        
        report += "### Target Database Results:\n\n"
        
        for target_db, stats in result["target_dbs"].items():
            report += f"#### {target_db}:\n"
            report += f"- Successful mappings: {stats['successful']} / {result['total']} ({stats['success_rate']:.1f}%)\n"
            report += f"- Average IDs per mapping: {stats['avg_ids']:.1f}\n"
            report += f"- Average confidence: {stats['avg_confidence']:.2f}\n"
            
            if "agreements" in stats:
                report += f"- Agreement with existing IDs: {stats['agreements']} / {stats['existing_id_count']} ({stats['agreement_rate']:.1f}%)\n"
            
            report += "\n"
        
        report += "---\n\n"
    
    return report

def main():
    """
    Main entry point for the script.
    """
    # Analyze results for each file
    results = []
    
    # Chemistries metadata
    chemistry_results = analyze_resolver_results(
        CHEMISTRIES_OUTPUT_PATH,
        "Name"
    )
    results.append(chemistry_results)
    
    # UKBB NMR metadata
    ukbb_results = analyze_resolver_results(
        UKBB_NMR_OUTPUT_PATH,
        "title"
    )
    results.append(ukbb_results)
    
    # Metabolomics metadata
    metabolomics_results = analyze_resolver_results(
        METABOLOMICS_OUTPUT_PATH,
        "BIOCHEMICAL_NAME",
        "PUBCHEM"
    )
    results.append(metabolomics_results)
    
    # Generate and save the markdown report
    report = generate_markdown_report(results)
    
    with open(ANALYSIS_REPORT_PATH, 'w') as f:
        f.write(report)
    
    print(f"Analysis report saved to {ANALYSIS_REPORT_PATH}")
    print("\nSummary:")
    print(report)

if __name__ == "__main__":
    main()