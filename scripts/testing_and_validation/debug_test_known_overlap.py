#!/usr/bin/env python3
"""Test mapping with known overlapping IDs"""

import pandas as pd
import tempfile
import os

# Known overlapping IDs from our analysis
overlapping_ids = ['A1E959', 'A1KZ92', 'A2VDF0', 'A6NGG8', 'A6NGN9', 
                   'A6NLU5', 'A6NM11', 'A8MTB9', 'A8MVW5', 'B6A8C7']

# Create a test UKBB file with known overlapping IDs
test_data = {
    'Assay': [f'TEST_{i+1}' for i in range(10)],
    'UniProt': overlapping_ids,
    'Panel': ['Oncology'] * 10
}

test_df = pd.DataFrame(test_data)

# Save to temporary file
test_file = '/home/ubuntu/biomapper/data/output/test_ukbb_overlap.tsv'
test_df.to_csv(test_file, sep='\t', index=False)

print(f"Created test file with known overlapping IDs: {test_file}")
print("\nTest data:")
print(test_df)