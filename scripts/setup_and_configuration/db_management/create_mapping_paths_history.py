#!/usr/bin/env python3
"""
Create a mapping_paths_history table to track changes to mapping paths over time.

This script:
1. Creates a mapping_paths_history table to store a complete history of mapping path changes
2. Sets up database triggers to automatically log changes to mapping_paths
3. Adds utility functions for querying the mapping path history
"""

import sqlite3
import sys
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple

# Get database path
db_path = Path("data/metamapper.db")
if not db_path.exists():
    print(f"Database file {db_path} not found!")
    sys.exit(1)

print(f"Using database at {db_path}")

# Connect to the database
conn = sqlite3.connect(db_path)
conn.row_factory = sqlite3.Row  # Return rows as dictionaries
cursor = conn.cursor()

# SQL to create the mapping_paths_history table
CREATE_HISTORY_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS mapping_paths_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    mapping_path_id INTEGER NOT NULL,
    source_type TEXT NOT NULL,
    target_type TEXT NOT NULL,
    path_steps TEXT NOT NULL,
    performance_score REAL,
    success_rate REAL,
    usage_count INTEGER,
    event_type TEXT NOT NULL,  -- 'created', 'updated', 'deleted'
    reason TEXT,  -- Why the change occurred
    previous_id INTEGER,  -- ID of the previous version (for updates)
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (mapping_path_id) REFERENCES mapping_paths(id)
);

CREATE INDEX IF NOT EXISTS idx_mapping_paths_history_path_id 
ON mapping_paths_history (mapping_path_id);

CREATE INDEX IF NOT EXISTS idx_mapping_paths_history_event 
ON mapping_paths_history (event_type, timestamp);

CREATE INDEX IF NOT EXISTS idx_mapping_paths_history_types
ON mapping_paths_history (source_type, target_type);
"""

# SQL to create triggers for automatic history logging
CREATE_TRIGGERS_SQL = """
-- Trigger for INSERT operations on mapping_paths
CREATE TRIGGER IF NOT EXISTS trg_mapping_paths_after_insert
AFTER INSERT ON mapping_paths
BEGIN
    INSERT INTO mapping_paths_history (
        mapping_path_id, source_type, target_type, path_steps, 
        performance_score, success_rate, usage_count, event_type
    )
    VALUES (
        NEW.id, NEW.source_type, NEW.target_type, NEW.path_steps,
        NEW.performance_score, NEW.success_rate, NEW.usage_count, 'created'
    );
END;

-- Trigger for UPDATE operations on mapping_paths
CREATE TRIGGER IF NOT EXISTS trg_mapping_paths_after_update
AFTER UPDATE ON mapping_paths
BEGIN
    INSERT INTO mapping_paths_history (
        mapping_path_id, source_type, target_type, path_steps, 
        performance_score, success_rate, usage_count, event_type,
        previous_id
    )
    SELECT 
        NEW.id, NEW.source_type, NEW.target_type, NEW.path_steps,
        NEW.performance_score, NEW.success_rate, NEW.usage_count, 'updated',
        (SELECT MAX(id) FROM mapping_paths_history WHERE mapping_path_id = NEW.id)
    WHERE (
        NEW.path_steps != OLD.path_steps OR
        NEW.performance_score != OLD.performance_score OR
        NEW.success_rate != OLD.success_rate
    );
END;

-- Trigger for DELETE operations on mapping_paths
CREATE TRIGGER IF NOT EXISTS trg_mapping_paths_after_delete
AFTER DELETE ON mapping_paths
BEGIN
    INSERT INTO mapping_paths_history (
        mapping_path_id, source_type, target_type, path_steps, 
        performance_score, success_rate, usage_count, event_type,
        previous_id
    )
    SELECT 
        OLD.id, OLD.source_type, OLD.target_type, OLD.path_steps,
        OLD.performance_score, OLD.success_rate, OLD.usage_count, 'deleted',
        (SELECT MAX(id) FROM mapping_paths_history WHERE mapping_path_id = OLD.id);
END;
"""

# Helper functions for mapping path history management


def log_mapping_path_change(
    mapping_path_id: int,
    event_type: str,
    reason: str = None,
    conn: sqlite3.Connection = None,
) -> int:
    """
    Manually log a change to a mapping path with a specific reason.

    Args:
        mapping_path_id: ID of the mapping path
        event_type: Type of event ('created', 'updated', 'deleted')
        reason: Optional explanation for the change
        conn: Optional database connection (creates a new one if not provided)

    Returns:
        ID of the created history entry
    """
    should_close = False
    if conn is None:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        should_close = True

    cursor = conn.cursor()

    # Get the current mapping path data
    cursor.execute(
        """
        SELECT id, source_type, target_type, path_steps, 
               performance_score, success_rate, usage_count
        FROM mapping_paths
        WHERE id = ?
        """,
        (mapping_path_id,),
    )

    path = cursor.fetchone()
    if not path and event_type != "deleted":
        raise ValueError(f"Mapping path with ID {mapping_path_id} not found")

    # Get the previous history entry ID
    cursor.execute(
        """
        SELECT MAX(id) as prev_id 
        FROM mapping_paths_history 
        WHERE mapping_path_id = ?
        """,
        (mapping_path_id,),
    )

    result = cursor.fetchone()
    previous_id = result["prev_id"] if result and result["prev_id"] else None

    # Handle deleted paths that no longer exist in the main table
    if not path and event_type == "deleted":
        # Get the last history entry for this path
        cursor.execute(
            """
            SELECT * FROM mapping_paths_history 
            WHERE mapping_path_id = ? 
            ORDER BY id DESC LIMIT 1
            """,
            (mapping_path_id,),
        )
        last_entry = cursor.fetchone()
        if not last_entry:
            raise ValueError(
                f"No history found for deleted mapping path ID {mapping_path_id}"
            )

        # Insert the deleted event using data from the last history entry
        cursor.execute(
            """
            INSERT INTO mapping_paths_history (
                mapping_path_id, source_type, target_type, path_steps,
                performance_score, success_rate, usage_count,
                event_type, reason, previous_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                mapping_path_id,
                last_entry["source_type"],
                last_entry["target_type"],
                last_entry["path_steps"],
                last_entry["performance_score"],
                last_entry["success_rate"],
                last_entry["usage_count"],
                "deleted",
                reason,
                previous_id,
            ),
        )
    else:
        # Insert the history entry
        cursor.execute(
            """
            INSERT INTO mapping_paths_history (
                mapping_path_id, source_type, target_type, path_steps,
                performance_score, success_rate, usage_count,
                event_type, reason, previous_id
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                path["id"],
                path["source_type"],
                path["target_type"],
                path["path_steps"],
                path["performance_score"],
                path["success_rate"],
                path["usage_count"],
                event_type,
                reason,
                previous_id,
            ),
        )

    history_id = cursor.lastrowid
    conn.commit()

    if should_close:
        conn.close()

    return history_id


def get_mapping_path_history(
    mapping_path_id: Optional[int] = None,
    source_type: Optional[str] = None,
    target_type: Optional[str] = None,
    limit: int = 100,
    conn: sqlite3.Connection = None,
) -> List[Dict[str, Any]]:
    """
    Get the history of changes for mapping paths.

    Args:
        mapping_path_id: Optional ID to filter by specific mapping path
        source_type: Optional source_type to filter history
        target_type: Optional target_type to filter history
        limit: Maximum number of history entries to return
        conn: Optional database connection (creates a new one if not provided)

    Returns:
        List of history entries as dictionaries
    """
    should_close = False
    if conn is None:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        should_close = True

    cursor = conn.cursor()

    query = """
        SELECT * FROM mapping_paths_history
        WHERE 1=1
    """
    params = []

    if mapping_path_id is not None:
        query += " AND mapping_path_id = ?"
        params.append(mapping_path_id)

    if source_type is not None:
        query += " AND source_type = ?"
        params.append(source_type)

    if target_type is not None:
        query += " AND target_type = ?"
        params.append(target_type)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    results = [dict(row) for row in cursor.fetchall()]

    if should_close:
        conn.close()

    return results


def get_path_evolution(
    source_type: str, target_type: str, conn: sqlite3.Connection = None
) -> List[Dict[str, Any]]:
    """
    Get the evolution of a specific source->target mapping path over time.

    Args:
        source_type: Source ontology type
        target_type: Target ontology type
        conn: Optional database connection (creates a new one if not provided)

    Returns:
        List of history entries showing how the path evolved
    """
    should_close = False
    if conn is None:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        should_close = True

    cursor = conn.cursor()

    # First find all mapping paths (including deleted ones) for this source->target pair
    cursor.execute(
        """
        SELECT DISTINCT mapping_path_id 
        FROM mapping_paths_history 
        WHERE source_type = ? AND target_type = ?
        """,
        (source_type, target_type),
    )

    path_ids = [row["mapping_path_id"] for row in cursor.fetchall()]

    # Now get the history for all these paths
    results = []
    for path_id in path_ids:
        cursor.execute(
            """
            SELECT * FROM mapping_paths_history 
            WHERE mapping_path_id = ? 
            ORDER BY timestamp
            """,
            (path_id,),
        )
        results.extend([dict(row) for row in cursor.fetchall()])

    # Sort by timestamp to show evolution over time
    results.sort(key=lambda x: x["timestamp"])

    if should_close:
        conn.close()

    return results


def compare_path_versions(
    history_id1: int, history_id2: int, conn: sqlite3.Connection = None
) -> Dict[str, Any]:
    """
    Compare two versions of a mapping path to see what changed.

    Args:
        history_id1: ID of the first history entry
        history_id2: ID of the second history entry
        conn: Optional database connection (creates a new one if not provided)

    Returns:
        Dictionary containing the differences between versions
    """
    should_close = False
    if conn is None:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        should_close = True

    cursor = conn.cursor()

    cursor.execute("SELECT * FROM mapping_paths_history WHERE id = ?", (history_id1,))
    version1 = cursor.fetchone()

    cursor.execute("SELECT * FROM mapping_paths_history WHERE id = ?", (history_id2,))
    version2 = cursor.fetchone()

    if not version1 or not version2:
        raise ValueError(
            f"One or both history entries not found: {history_id1}, {history_id2}"
        )

    # Convert to dictionaries for easier comparison
    v1 = dict(version1)
    v2 = dict(version2)

    # Check if they're for the same mapping path
    if v1["mapping_path_id"] != v2["mapping_path_id"]:
        return {
            "error": "Cannot compare different mapping paths",
            "path_id1": v1["mapping_path_id"],
            "path_id2": v2["mapping_path_id"],
        }

    # Compare the versions
    differences = {}

    # Compare scalar fields
    for field in ["performance_score", "success_rate", "usage_count"]:
        if v1[field] != v2[field]:
            differences[field] = {
                "old": v1[field],
                "new": v2[field],
                "change": v2[field] - v1[field]
                if (v1[field] is not None and v2[field] is not None)
                else None,
            }

    # Compare path steps
    try:
        steps1 = json.loads(v1["path_steps"])
        steps2 = json.loads(v2["path_steps"])

        if steps1 != steps2:
            differences["path_steps"] = {
                "old": steps1,
                "new": steps2,
                "changes": {
                    "steps_added": len(steps2) - len(steps1)
                    if len(steps2) > len(steps1)
                    else 0,
                    "steps_removed": len(steps1) - len(steps2)
                    if len(steps1) > len(steps2)
                    else 0,
                    "steps_modified": sum(
                        1
                        for i in range(min(len(steps1), len(steps2)))
                        if steps1[i] != steps2[i]
                    ),
                },
            }
    except (json.JSONDecodeError, TypeError):
        differences["path_steps"] = {"error": "Could not parse path steps as JSON"}

    # Add metadata
    differences["metadata"] = {
        "history_id1": history_id1,
        "history_id2": history_id2,
        "event_type1": v1["event_type"],
        "event_type2": v2["event_type"],
        "timestamp1": v1["timestamp"],
        "timestamp2": v2["timestamp"],
        "time_difference": v2["timestamp"] - v1["timestamp"]
        if (v1["timestamp"] and v2["timestamp"])
        else None,
    }

    if should_close:
        conn.close()

    return differences


try:
    # Create the history table
    print("Creating mapping_paths_history table...")
    cursor.executescript(CREATE_HISTORY_TABLE_SQL)

    # Create triggers for automatic history logging
    print("Creating triggers for automatic history logging...")
    cursor.executescript(CREATE_TRIGGERS_SQL)

    # Check if we have existing mapping paths to log initial history
    cursor.execute("SELECT COUNT(*) as count FROM mapping_paths")
    mapping_paths_count = cursor.fetchone()["count"]

    # Check if we already have history entries
    cursor.execute("SELECT COUNT(*) as count FROM mapping_paths_history")
    history_count = cursor.fetchone()["count"]

    # Log initial state of existing mapping paths if no history exists
    if mapping_paths_count > 0 and history_count == 0:
        print(
            f"Logging initial state for {mapping_paths_count} existing mapping paths..."
        )
        cursor.execute("SELECT * FROM mapping_paths")
        existing_paths = cursor.fetchall()

        for path in existing_paths:
            log_mapping_path_change(
                mapping_path_id=path["id"],
                event_type="created",
                reason="Initial history logging",
                conn=conn,
            )
        print(f"Added {len(existing_paths)} initial history entries")

    # Commit all changes
    conn.commit()
    print("Successfully created mapping_paths_history table and triggers")

    # Show sample usage
    print("\nExample usage of mapping path history functions:")
    print("1. To log a manual change with a reason:")
    print(
        "   log_mapping_path_change(mapping_path_id=1, event_type='updated', reason='Improved performance')"
    )
    print("\n2. To view history for a specific mapping path:")
    print("   get_mapping_path_history(mapping_path_id=1)")
    print("\n3. To view history for a specific source->target type:")
    print("   get_mapping_path_history(source_type='NAME', target_type='CHEBI')")
    print("\n4. To see the evolution of a source->target mapping over time:")
    print("   get_path_evolution(source_type='NAME', target_type='CHEBI')")
    print("\n5. To compare two versions of a mapping path:")
    print("   compare_path_versions(history_id1=1, history_id2=2)")

except Exception as e:
    print(f"Error creating mapping paths history: {e}")
    conn.rollback()
    raise

finally:
    # Close the database connection
    conn.close()
