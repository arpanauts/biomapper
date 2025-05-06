import sqlite3
import json

# Connect to the SQLite database
conn = sqlite3.connect("data/mapping_cache.db")
conn.row_factory = sqlite3.Row  # This enables column access by name
cursor = conn.cursor()

# Query the entity_mappings table for the recent mappings
print("Checking all mappings in the database:")
cursor.execute(
    """
SELECT 
    id,
    source_id, 
    source_type, 
    target_id, 
    target_type, 
    confidence_score, 
    hop_count, 
    mapping_direction, 
    mapping_path_details 
FROM entity_mappings 
ORDER BY id DESC
LIMIT 10
"""
)

rows = cursor.fetchall()

print("\nEntity Mappings:")
print("-" * 120)
print(
    f"{'ID':<5} {'Source ID':<10} {'Source Type':<15} {'Target ID':<15} {'Direction':<10} {'Hop Count':<10} {'Confidence':<10} {'Path Details'}"
)
print("-" * 120)

for row in rows:
    path_details = row["mapping_path_details"]
    # Pretty format the path details if it's JSON
    if path_details:
        try:
            if isinstance(path_details, str):
                path_details = json.loads(path_details)
            path_details = json.dumps(path_details, indent=2)
        except (json.JSONDecodeError, TypeError):
            path_details = str(path_details)

    confidence = row["confidence_score"]
    if confidence is None:
        confidence_str = "None"
    else:
        confidence_str = f"{confidence:.2f}"

    print(
        f"{row['id']:<5} {row['source_id']:<10} {row['source_type']:<15} {row['target_id']:<15} {row['mapping_direction']:<10} {row['hop_count']:<10} {confidence_str:<10} {path_details}"
    )

conn.close()
