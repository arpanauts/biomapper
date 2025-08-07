#!/usr/bin/env python3
"""Test XML parsing to debug issues."""

import xml.etree.ElementTree as ET
import time
from pathlib import Path
import pytest

xml_path = Path("/home/ubuntu/biomapper/data/hmdb_metabolites.xml")

# Skip test if XML file doesn't exist
if not xml_path.exists():
    pytest.skip(f"XML file not found: {xml_path}", allow_module_level=True)

print("Testing XML parsing...")
print(f"File size: {xml_path.stat().st_size / 1024 / 1024 / 1024:.1f} GB")

# Test 1: Can we parse at all?
print("\n1. Testing basic iterparse...")
start = time.time()
count = 0
try:
    for event, elem in ET.iterparse(xml_path, events=("start", "end")):
        if event == "end" and elem.tag == "metabolite":
            count += 1
            if count == 1:
                print("   Found first metabolite!")
                # Print some info about it
                name = elem.find("name")
                if name is not None and name.text:
                    print(f"   Name: {name.text}")
                hmdb_id = elem.find("accession")
                if hmdb_id is not None and hmdb_id.text:
                    print(f"   HMDB ID: {hmdb_id.text}")

            # Clear memory
            elem.clear()

            # Progress update
            if count % 100 == 0:
                elapsed = time.time() - start
                print(
                    f"   Processed {count} metabolites in {elapsed:.1f}s ({count/elapsed:.1f} per second)"
                )

            # Stop after 500 for quick test
            if count >= 500:
                print(f"   Stopping test after {count} metabolites")
                break

except Exception as e:
    print(f"ERROR: {e}")
    import traceback

    traceback.print_exc()

print(f"\nTest complete. Found {count} metabolites in {time.time() - start:.1f}s")

# Test 2: Check XML structure
print("\n2. Checking XML structure...")
try:
    # Just parse first few bytes to check structure
    with open(xml_path, "rb") as f:
        first_1000_bytes = f.read(1000)
        print(f"First 1000 bytes:\n{first_1000_bytes.decode('utf-8', errors='ignore')}")
except Exception as e:
    print(f"ERROR reading file: {e}")
