#!/usr/bin/env python3
"""
Create a more flexible version of the mapping script that accepts property names as arguments.
This allows mapping between any endpoints without hardcoding property names.
"""

import shutil

def create_flexible_mapping_script():
    """Create a flexible version of map_ukbb_to_hpa.py that accepts property names as arguments."""
    
    original_script = "/home/ubuntu/biomapper/scripts/map_ukbb_to_hpa.py"
    flexible_script = "/home/ubuntu/biomapper/scripts/map_endpoints_flexible.py"
    
    # Copy the original script
    shutil.copy2(original_script, flexible_script)
    
    # Read the content
    with open(flexible_script, 'r') as f:
        content = f.read()
    
    # Replace the hardcoded property section with a flexible version
    old_section = """# Source and target property names - these are what the endpoints expose
# UKBB_Protein uses "PrimaryIdentifier", HPA_Protein uses "UniProtAccession"
# These should match the property_name in EndpointPropertyConfig table
SOURCE_PROPERTY_NAME = "PrimaryIdentifier"  # UKBB_Protein primary property
TARGET_PROPERTY_NAME = "UniProtAccession"   # HPA_Protein primary property"""
    
    new_section = """# Source and target property names will be set from command line arguments
# These must match the property_name values in EndpointPropertyConfig table
SOURCE_PROPERTY_NAME = None  # Will be set from args.source_property_name
TARGET_PROPERTY_NAME = None  # Will be set from args.target_property_name"""
    
    content = content.replace(old_section, new_section)
    
    # Add new arguments to the argument parser section
    # Find the section with argument definitions
    args_insertion_point = '    parser.add_argument(\n        "--target_ontology_name",\n        required=True,\n        help="Ontology name for the target identifiers (e.g., ARIVALE_PROTEIN_ID)"\n    )'
    
    new_args = '''    parser.add_argument(
        "--target_ontology_name",
        required=True,
        help="Ontology name for the target identifiers (e.g., ARIVALE_PROTEIN_ID)"
    )
    parser.add_argument(
        "--source_property_name",
        required=True,
        help="Property name for the source endpoint (e.g., PrimaryIdentifier)"
    )
    parser.add_argument(
        "--target_property_name", 
        required=True,
        help="Property name for the target endpoint (e.g., UniProtAccession)"
    )'''
    
    content = content.replace(args_insertion_point, new_args)
    
    # Update the main function signature
    old_main_sig = '''async def main(
    input_file_path: str, 
    output_file_path: str, 
    try_reverse_mapping_param: bool,
    source_endpoint_name: str,
    target_endpoint_name: str,
    input_id_column_name: str,        # e.g., "UniProt" or "uniprot"
    input_primary_key_column_name: str, # e.g., "Assay" or "name"
    output_mapped_id_column_name: str, # e.g., "ARIVALE_PROTEIN_ID" or "UKBB_ASSAY_ID"
    source_ontology_name: str,        # e.g., "UNIPROTKB_AC"
    target_ontology_name: str         # e.g., "ARIVALE_PROTEIN_ID"
):'''
    
    new_main_sig = '''async def main(
    input_file_path: str, 
    output_file_path: str, 
    try_reverse_mapping_param: bool,
    source_endpoint_name: str,
    target_endpoint_name: str,
    input_id_column_name: str,        # e.g., "UniProt" or "uniprot"
    input_primary_key_column_name: str, # e.g., "Assay" or "name"
    output_mapped_id_column_name: str, # e.g., "ARIVALE_PROTEIN_ID" or "UKBB_ASSAY_ID"
    source_ontology_name: str,        # e.g., "UNIPROTKB_AC"
    target_ontology_name: str,        # e.g., "ARIVALE_PROTEIN_ID"
    source_property_name: str,        # e.g., "PrimaryIdentifier"
    target_property_name: str         # e.g., "UniProtAccession"
):'''
    
    content = content.replace(old_main_sig, new_main_sig)
    
    # Update the global variable assignment inside main
    old_assignment = '''            source_property_name=SOURCE_PROPERTY_NAME, # Property name (PrimaryIdentifier), not the ontology type
            target_property_name=TARGET_PROPERTY_NAME, # Property name (PrimaryIdentifier), not the ontology type'''
    
    new_assignment = '''            source_property_name=source_property_name, # Property name from command line args
            target_property_name=target_property_name, # Property name from command line args'''
    
    content = content.replace(old_assignment, new_assignment)
    
    # Update the asyncio.run call
    old_run = '''    asyncio.run(main(
        args.input_file, 
        args.output_file, 
        args.reverse,
        args.source_endpoint,
        args.target_endpoint,
        args.input_id_column_name,
        args.input_primary_key_column_name,
        args.output_mapped_id_column_name,
        args.source_ontology_name,
        args.target_ontology_name
    ))'''
    
    new_run = '''    asyncio.run(main(
        args.input_file, 
        args.output_file, 
        args.reverse,
        args.source_endpoint,
        args.target_endpoint,
        args.input_id_column_name,
        args.input_primary_key_column_name,
        args.output_mapped_id_column_name,
        args.source_ontology_name,
        args.target_ontology_name,
        args.source_property_name,
        args.target_property_name
    ))'''
    
    content = content.replace(old_run, new_run)
    
    # Write the modified content
    with open(flexible_script, 'w') as f:
        f.write(content)
    
    # Make it executable
    import os
    os.chmod(flexible_script, 0o755)
    
    print(f"✅ Created flexible mapping script: {flexible_script}")
    print("\nExample usage:")
    print("  python scripts/map_endpoints_flexible.py \\")
    print("    input.tsv output.tsv \\")
    print("    --source_endpoint UKBB_Protein \\")
    print("    --target_endpoint HPA_Protein \\")
    print("    --input_id_column_name uniprot \\")
    print("    --input_primary_key_column_name name \\")
    print("    --output_mapped_id_column_name HPA_PROTEIN_ID \\")
    print("    --source_ontology_name UNIPROTKB_AC \\")
    print("    --target_ontology_name UNIPROTKB_AC \\")
    print("    --source_property_name PrimaryIdentifier \\")
    print("    --target_property_name UniProtAccession")

if __name__ == "__main__":
    create_flexible_mapping_script()