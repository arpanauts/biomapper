#!/usr/bin/env python3
"""
Script to monitor the progress of PubMed data processing.
"""

import argparse
import glob
import json
import os
import subprocess
import sys
import time
from datetime import datetime


def get_json_file_count(json_dir):
    """Get the number of processed JSON files."""
    return len(glob.glob(os.path.join(json_dir, "*.jsonl")))


def get_temp_batch_status(temp_dir):
    """Get the status of batch processing in the temp directory."""
    batches = {}
    for batch_dir in glob.glob(os.path.join(temp_dir, "batch_*")):
        batch_name = os.path.basename(batch_dir)

        input_dir = os.path.join(batch_dir, "input")
        output_dir = os.path.join(batch_dir, "output")

        input_files = glob.glob(os.path.join(input_dir, "*.xml.gz"))
        output_files = glob.glob(os.path.join(output_dir, "*.jsonl"))

        batches[batch_name] = {
            "input_files": len(input_files),
            "output_files": len(output_files),
            "input_files_size": sum(os.path.getsize(f) for f in input_files)
            if input_files
            else 0,
            "output_files_size": sum(os.path.getsize(f) for f in output_files)
            if output_files
            else 0,
        }

    return batches


def get_vector_store_info(index_path, metadata_path):
    """Get information about the vector store."""
    if not (os.path.exists(index_path) and os.path.exists(metadata_path)):
        return {"status": "Not created yet"}

    try:
        with open(metadata_path, "r") as f:
            metadata = json.load(f)

        return {
            "status": "Available",
            "vectors": len(metadata),
            "metadata_size": os.path.getsize(metadata_path),
            "index_size": os.path.getsize(index_path),
        }
    except:
        return {"status": "Error reading metadata"}


def format_size(size_bytes):
    """Format size in bytes to human-readable format."""
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.2f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def main():
    parser = argparse.ArgumentParser(
        description="Monitor the progress of PubMed data processing."
    )
    parser.add_argument(
        "--data-dir", required=True, help="Base directory for PubMed data processing"
    )
    parser.add_argument(
        "--refresh-interval", type=int, default=10, help="Refresh interval in seconds"
    )
    args = parser.parse_args()

    json_dir = os.path.join(args.data_dir, "json")
    temp_dir = os.path.join(args.data_dir, "temp")
    vectors_dir = os.path.join(args.data_dir, "vectors")

    index_path = os.path.join(vectors_dir, "pubmed_full_embeddings.index")
    metadata_path = os.path.join(vectors_dir, "pubmed_full_metadata.json")

    while True:
        os.system("clear")

        print("=" * 70)
        print(
            f"PUBMED DATA PROCESSING MONITOR - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )
        print("=" * 70)

        # JSON conversion progress
        json_count = get_json_file_count(json_dir)
        json_size = sum(
            os.path.getsize(f) for f in glob.glob(os.path.join(json_dir, "*.jsonl"))
        )

        print(f"\nJSON Conversion Progress:")
        print(f"- Completed files: {json_count} / 1274")
        print(f"- Progress: {json_count / 1274 * 100:.2f}%")
        print(f"- Total JSON size: {format_size(json_size)}")

        # Current batch processing
        batches = get_temp_batch_status(temp_dir)
        if batches:
            print(f"\nActive Batch Processing:")
            for batch_name, status in batches.items():
                print(f"- {batch_name}:")
                print(
                    f"  - Input files: {status['input_files']} ({format_size(status['input_files_size'])})"
                )
                print(
                    f"  - Output files: {status['output_files']} ({format_size(status['output_files_size'])})"
                )
        else:
            print(f"\nNo active batch processing detected.")

        # Vector store status
        vector_info = get_vector_store_info(index_path, metadata_path)
        print(f"\nVector Store Status:")
        for key, value in vector_info.items():
            if key in ["metadata_size", "index_size"]:
                print(f"- {key}: {format_size(value)}")
            else:
                print(f"- {key}: {value}")

        # System status
        print(f"\nSystem Status:")
        try:
            mem_info = subprocess.check_output("free -h", shell=True).decode("utf-8")
            print(mem_info)
        except:
            print("Unable to get memory information")

        try:
            disk_info = subprocess.check_output(
                "df -h | grep -E '/$|/home'", shell=True
            ).decode("utf-8")
            print(disk_info)
        except:
            print("Unable to get disk information")

        print("\nPress Ctrl+C to exit...")
        print("=" * 70)

        try:
            time.sleep(args.refresh_interval)
        except KeyboardInterrupt:
            print("\nMonitoring stopped.")
            break


if __name__ == "__main__":
    main()
