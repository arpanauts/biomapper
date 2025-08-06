#!/usr/bin/env python3
"""Test XML parsing with namespace handling."""

import xml.etree.ElementTree as ET
import time

xml_path = "/home/ubuntu/biomapper/data/hmdb_metabolites.xml"

print("Testing XML parsing with namespace...")

# Register namespace
ET.register_namespace('', 'http://www.hmdb.ca')

count = 0
start = time.time()

try:
    for event, elem in ET.iterparse(xml_path, events=("end",)):
        # Handle namespace - look for elements ending with 'metabolite'
        if event == "end" and elem.tag.endswith("metabolite"):
            count += 1
            
            # Get name and ID handling namespace
            name_elem = elem.find(".//{http://www.hmdb.ca}name")
            id_elem = elem.find(".//{http://www.hmdb.ca}accession")
            
            if count == 1:
                print(f"First metabolite:")
                if name_elem is not None:
                    print(f"  Name: {name_elem.text}")
                if id_elem is not None:
                    print(f"  ID: {id_elem.text}")
            
            # Clear memory
            elem.clear()
            while elem.getprevious() is not None:
                del elem.getparent()[0]
                
            if count % 100 == 0:
                elapsed = time.time() - start
                print(f"Processed {count} metabolites in {elapsed:.1f}s")
                
            if count >= 500:
                break
                
except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()

print(f"\nFound {count} metabolites in {time.time() - start:.1f}s")