#!/usr/bin/env python3
"""
Fix script to update map_ukbb_to_hpa.py to use correct property names.

The issue: map_ukbb_to_hpa.py uses hardcoded "PrimaryIdentifier" for both 
source and target properties, but HPA_Protein uses "UniProtAccession" as its 
primary property name.
"""

import sys

def fix_mapping_script():
    script_path = "/home/ubuntu/biomapper/scripts/map_ukbb_to_hpa.py"
    
    # Read the current script
    with open(script_path, 'r') as f:
        content = f.read()
    
    # Replace the hardcoded property names section
    old_section = """# Source and target property names - these are what the endpoints expose
# These are assumed to be 'PrimaryIdentifier' for now, but could be made configurable if needed.
SOURCE_PROPERTY_NAME = "PrimaryIdentifier"
TARGET_PROPERTY_NAME = "PrimaryIdentifier\""""
    
    new_section = """# Source and target property names - these are what the endpoints expose
# UKBB_Protein uses "PrimaryIdentifier", HPA_Protein uses "UniProtAccession"
# These should match the property_name in EndpointPropertyConfig table
SOURCE_PROPERTY_NAME = "PrimaryIdentifier"  # UKBB_Protein primary property
TARGET_PROPERTY_NAME = "UniProtAccession"   # HPA_Protein primary property"""
    
    if old_section in content:
        content = content.replace(old_section, new_section)
        
        # Write back the fixed content
        with open(script_path, 'w') as f:
            f.write(content)
        
        print(f"✅ Successfully updated {script_path}")
        print("Changed TARGET_PROPERTY_NAME from 'PrimaryIdentifier' to 'UniProtAccession'")
        return True
    else:
        print("❌ Could not find the expected section to replace.")
        print("The script may have already been modified or has a different structure.")
        return False

if __name__ == "__main__":
    success = fix_mapping_script()
    sys.exit(0 if success else 1)