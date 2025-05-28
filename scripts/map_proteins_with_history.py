#!/usr/bin/env python3
"""
Map proteins between endpoints using the full Biomapper framework.
This includes handling deprecated, merged, and demerged UniProt IDs.
"""

import argparse
import asyncio
import pandas as pd
import logging
import sys
from datetime import datetime
from biomapper.mapping.clients.hpa_protein_lookup_client import HPAProteinLookupClient
from biomapper.mapping.clients.qin_protein_lookup_client import QinProteinLookupClient
from biomapper.mapping.clients.uniprot_historical_resolver_client import UniProtHistoricalResolverClient
from biomapper.core.config import Config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

async def resolve_historical_ids(uniprot_ids):
    """Resolve historical UniProt IDs to current ones"""
    config = Config.get_instance()
    client = UniProtHistoricalResolverClient(config)
    
    results = {}
    for uniprot_id in uniprot_ids:
        try:
            result = await client.get_mapping(uniprot_id)
            if result and result.get('target_identifiers'):
                results[uniprot_id] = result['target_identifiers']
            else:
                results[uniprot_id] = [uniprot_id]  # Keep original if no mapping
        except Exception as e:
            logging.warning(f"Error resolving {uniprot_id}: {e}")
            results[uniprot_id] = [uniprot_id]
    
    return results

async def map_to_hpa(uniprot_ids):
    """Map UniProt IDs to HPA dataset"""
    config = Config.get_instance()
    # Load HPA data
    hpa_df = pd.read_csv('/home/ubuntu/biomapper/data/isb_osp/hpa_osps.csv')
    hpa_uniprot_set = set(hpa_df['uniprot'].dropna().unique())
    
    results = {}
    for uniprot_id in uniprot_ids:
        if uniprot_id in hpa_uniprot_set:
            results[uniprot_id] = {
                'found': True,
                'organs': hpa_df[hpa_df['uniprot'] == uniprot_id]['organ'].tolist(),
                'genes': hpa_df[hpa_df['uniprot'] == uniprot_id]['gene'].unique().tolist()
            }
        else:
            results[uniprot_id] = {'found': False}
    
    return results

async def map_to_qin(uniprot_ids):
    """Map UniProt IDs to QIN dataset"""
    config = Config.get_instance()
    # Load QIN data
    qin_df = pd.read_csv('/home/ubuntu/biomapper/data/isb_osp/qin_osps.csv')
    qin_uniprot_set = set(qin_df['uniprot'].dropna().unique())
    
    results = {}
    for uniprot_id in uniprot_ids:
        if uniprot_id in qin_uniprot_set:
            results[uniprot_id] = {
                'found': True,
                'organs': qin_df[qin_df['uniprot'] == uniprot_id]['organ'].tolist(),
                'genes': qin_df[qin_df['uniprot'] == uniprot_id]['gene'].unique().tolist()
            }
        else:
            results[uniprot_id] = {'found': False}
    
    return results

async def main():
    parser = argparse.ArgumentParser(description='Map proteins with historical ID resolution')
    parser.add_argument('input_file', help='Input TSV file')
    parser.add_argument('output_file', help='Output TSV file')
    parser.add_argument('--target', choices=['HPA', 'QIN'], required=True, help='Target dataset')
    parser.add_argument('--resolve-historical', action='store_true', help='Resolve historical UniProt IDs')
    parser.add_argument('--summary', action='store_true', help='Generate summary report')
    
    args = parser.parse_args()
    
    # Load input data
    logging.info(f"Loading input from {args.input_file}")
    df = pd.read_csv(args.input_file, sep='\t')
    
    # Get unique UniProt IDs
    uniprot_ids = df['UniProt'].dropna().unique().tolist()
    logging.info(f"Found {len(uniprot_ids)} unique UniProt IDs")
    
    # Resolve historical IDs if requested
    historical_mappings = {}
    if args.resolve_historical:
        logging.info("Resolving historical UniProt IDs...")
        historical_mappings = await resolve_historical_ids(uniprot_ids)
        
        # Count how many IDs were resolved to different ones
        resolved_count = sum(1 for orig, curr in historical_mappings.items() 
                           if curr != [orig])
        logging.info(f"Resolved {resolved_count} historical IDs")
    
    # Get all current IDs (original + resolved)
    all_current_ids = set()
    for orig_id in uniprot_ids:
        if orig_id in historical_mappings:
            all_current_ids.update(historical_mappings[orig_id])
        else:
            all_current_ids.add(orig_id)
    
    # Map to target dataset
    logging.info(f"Mapping to {args.target}...")
    if args.target == 'HPA':
        mapping_results = await map_to_hpa(list(all_current_ids))
        target_col = 'HPA_UniProtKB_AC'
        target_gene_col = 'HPA_gene'
        target_organ_col = 'HPA_organs'
    else:
        mapping_results = await map_to_qin(list(all_current_ids))
        target_col = 'QIN_UniProtKB_AC'
        target_gene_col = 'QIN_gene'
        target_organ_col = 'QIN_organs'
    
    # Add results to dataframe
    df[target_col] = ''
    df[target_gene_col] = ''
    df[target_organ_col] = ''
    df['mapping_confidence_score'] = ''
    df['mapping_path_details'] = ''
    df['historical_resolution'] = ''
    
    mapped_count = 0
    historical_resolved_count = 0
    
    for idx, row in df.iterrows():
        orig_id = row['UniProt']
        if pd.isna(orig_id):
            continue
            
        # Check if ID was historically resolved
        if args.resolve_historical and orig_id in historical_mappings:
            current_ids = historical_mappings[orig_id]
            if current_ids != [orig_id]:
                df.at[idx, 'historical_resolution'] = f"Resolved to: {', '.join(current_ids)}"
                historical_resolved_count += 1
        else:
            current_ids = [orig_id]
        
        # Check mapping for any of the current IDs
        found = False
        for curr_id in current_ids:
            if curr_id in mapping_results and mapping_results[curr_id]['found']:
                result = mapping_results[curr_id]
                df.at[idx, target_col] = curr_id
                df.at[idx, target_gene_col] = '|'.join(result['genes'])
                df.at[idx, target_organ_col] = '|'.join(result['organs'])
                df.at[idx, 'mapping_confidence_score'] = 1.0
                df.at[idx, 'mapping_path_details'] = 'Direct UniProtKB AC match' if curr_id == orig_id else f'Historical resolution: {orig_id} -> {curr_id}'
                found = True
                mapped_count += 1
                break
    
    # Write output
    logging.info(f"Writing results to {args.output_file}")
    df.to_csv(args.output_file, sep='\t', index=False)
    
    # Generate summary if requested
    if args.summary:
        summary_file = args.output_file.replace('.tsv', '_summary_report.txt')
        with open(summary_file, 'w') as f:
            f.write(f"# UKBB_Protein to {args.target}_Protein Mapping Summary Report\n\n")
            f.write(f"Input File: {args.input_file}\n")
            f.write(f"Output File: {args.output_file}\n")
            f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"## Overall Statistics\n")
            f.write(f"Total records: {len(df)}\n")
            f.write(f"Successfully mapped: {mapped_count} ({mapped_count/len(uniprot_ids)*100:.2f}%)\n")
            if args.resolve_historical:
                f.write(f"\n## Historical Resolution\n")
                f.write(f"Historical IDs resolved: {historical_resolved_count}\n")
        
        logging.info(f"Summary report written to {summary_file}")
    
    logging.info(f"Mapping complete. {mapped_count}/{len(uniprot_ids)} proteins mapped ({mapped_count/len(uniprot_ids)*100:.1f}%)")

if __name__ == '__main__':
    asyncio.run(main())