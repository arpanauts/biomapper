#!/usr/bin/env python3
"""
Script to process all PubMed XML files and generate embeddings.
This script is designed to handle large-scale processing with error recovery.
"""

import argparse
import glob
import logging
import os
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("pubmed_processing.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def setup_directories(base_dir):
    """Create necessary directories if they don't exist."""
    json_dir = os.path.join(base_dir, "json")
    vectors_dir = os.path.join(base_dir, "vectors")
    temp_dir = os.path.join(base_dir, "temp")
    
    os.makedirs(json_dir, exist_ok=True)
    os.makedirs(vectors_dir, exist_ok=True)
    os.makedirs(temp_dir, exist_ok=True)
    
    return json_dir, vectors_dir, temp_dir

def get_xml_files(input_dir):
    """Get all XML files to process."""
    xml_files = glob.glob(os.path.join(input_dir, "*.xml.gz"))
    logger.info(f"Found {len(xml_files)} XML files to process")
    return xml_files

def get_already_processed_files(output_dir):
    """Get list of already processed files."""
    processed = set()
    for jsonl_file in glob.glob(os.path.join(output_dir, "*.jsonl")):
        base_name = os.path.basename(jsonl_file).replace(".jsonl", ".xml.gz")
        processed.add(base_name)
    
    return processed

def process_batch(xml_files, output_dir, temp_dir, xml_to_json_script, batch_size=10, max_articles=None):
    """Process a batch of XML files."""
    total_processed = 0
    
    # Process files in batches
    for i in range(0, len(xml_files), batch_size):
        batch = xml_files[i:i+batch_size]
        logger.info(f"Processing batch {i//batch_size + 1}/{(len(xml_files) + batch_size - 1)//batch_size} ({len(batch)} files)")
        
        batch_start = time.time()
        
        # Create a temporary directory for this batch
        batch_temp_dir = os.path.join(temp_dir, f"batch_{i//batch_size + 1}")
        os.makedirs(batch_temp_dir, exist_ok=True)
        
        # Copy files to temp directory for processing
        batch_input_dir = os.path.join(batch_temp_dir, "input")
        batch_output_dir = os.path.join(batch_temp_dir, "output")
        
        os.makedirs(batch_input_dir, exist_ok=True)
        os.makedirs(batch_output_dir, exist_ok=True)
        
        for xml_file in batch:
            file_name = os.path.basename(xml_file)
            output_file = os.path.join(output_dir, file_name.replace(".xml.gz", ".jsonl"))
            
            # Skip if file already processed
            if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
                logger.info(f"Skipping already processed file: {file_name}")
                continue
            
            # Copy XML file to batch input directory
            shutil.copy2(xml_file, os.path.join(batch_input_dir, file_name))
        
        try:
            # Process the batch using the XML to JSON script
            cmd = [
                xml_to_json_script,
                "--input-dir", batch_input_dir,
                "--output-dir", batch_output_dir,
            ]
            
            # Only add max-articles if specified
            if max_articles is not None:
                cmd.extend(["--max-articles", str(max_articles)])
            
            logger.info(f"Processing batch of {len(batch)} files")
            result = subprocess.run(cmd, check=True, capture_output=True, text=True)
            logger.info(f"Successfully processed batch")
            
            # Move processed files to final output directory
            for jsonl_file in glob.glob(os.path.join(batch_output_dir, "*.jsonl")):
                file_name = os.path.basename(jsonl_file)
                shutil.move(jsonl_file, os.path.join(output_dir, file_name))
                total_processed += 1
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error processing batch: {e}")
            logger.error(f"STDOUT: {e.stdout}")
            logger.error(f"STDERR: {e.stderr}")
            
        except Exception as e:
            logger.error(f"Unexpected error processing batch: {e}")
        
        # Clean up temp directory
        shutil.rmtree(batch_temp_dir, ignore_errors=True)
        
        batch_end = time.time()
        logger.info(f"Batch processed in {batch_end - batch_start:.2f} seconds")
        
    return total_processed

def generate_embeddings(json_dir, output_index, output_metadata, embedder_cli_script, batch_size=5):
    """Generate embeddings from processed JSON files."""
    logger.info(f"Generating embeddings from JSON files in: {json_dir}")
    
    # Get all processed JSON files
    json_files = glob.glob(os.path.join(json_dir, "*.jsonl"))
    if not json_files:
        logger.error(f"No JSON files found in {json_dir}")
        return False
    
    logger.info(f"Found {len(json_files)} JSON files for embedding")
    
    # Process files in smaller batches since each file could have many articles
    success = True
    total_embedded = 0
    
    for i in range(0, len(json_files), batch_size):
        batch = json_files[i:i+batch_size]
        logger.info(f"Embedding batch {i//batch_size + 1}/{(len(json_files) + batch_size - 1)//batch_size} ({len(batch)} files)")
        
        for json_file in batch:
            try:
                cmd = [
                    embedder_cli_script,
                    "process",
                    "--input-file", json_file,
                    "--index-path", output_index,
                    "--metadata-path", output_metadata
                ]
                
                logger.info(f"Embedding: {os.path.basename(json_file)}")
                result = subprocess.run(cmd, check=True, capture_output=True, text=True)
                logger.info(f"Successfully embedded: {os.path.basename(json_file)}")
                total_embedded += 1
                
                # Get stats about the index periodically
                if total_embedded % 20 == 0:
                    try:
                        stat_cmd = [
                            embedder_cli_script,
                            "info",
                            "--index-path", output_index,
                            "--metadata-path", output_metadata
                        ]
                        stat_result = subprocess.run(stat_cmd, check=True, capture_output=True, text=True)
                        logger.info(f"Current index status:\n{stat_result.stdout}")
                    except Exception as e:
                        logger.warning(f"Could not get index stats: {e}")
                
            except subprocess.CalledProcessError as e:
                logger.error(f"Error embedding {os.path.basename(json_file)}: {e}")
                logger.error(f"STDOUT: {e.stdout}")
                logger.error(f"STDERR: {e.stderr}")
                success = False
                
            except Exception as e:
                logger.error(f"Unexpected error embedding {os.path.basename(json_file)}: {e}")
                success = False
    
    logger.info(f"Total files embedded: {total_embedded}/{len(json_files)}")
    
    return success

def main():
    parser = argparse.ArgumentParser(description="Process full PubMed dataset.")
    parser.add_argument("--input-dir", required=True, help="Directory containing PubMed XML files")
    parser.add_argument("--output-dir", required=True, help="Base directory for outputs")
    parser.add_argument("--batch-size", type=int, default=5, help="Number of XML files to process in each batch")
    parser.add_argument("--max-articles", type=int, help="Maximum articles to extract per XML file. If not specified, process all articles")
    parser.add_argument("--xml-to-json-script", required=True, help="Path to the XML to JSON conversion script")
    parser.add_argument("--embedder-cli-script", required=True, help="Path to the embedder CLI script")
    parser.add_argument("--skip-embedding", action="store_true", help="Skip embedding generation and only process XML files")
    parser.add_argument("--embedding-batch-size", type=int, default=5, help="Number of JSON files to process in each embedding batch")
    args = parser.parse_args()
    
    start_time = time.time()
    logger.info("Starting full PubMed dataset processing")
    logger.info(f"Input directory: {args.input_dir}")
    logger.info(f"Output directory: {args.output_dir}")
    
    # Setup directories
    json_dir, vectors_dir, temp_dir = setup_directories(args.output_dir)
    
    # Get XML files to process
    xml_files = get_xml_files(args.input_dir)
    
    # Process XML files to JSON
    total_processed = process_batch(
        xml_files, 
        json_dir,
        temp_dir,
        args.xml_to_json_script, 
        batch_size=args.batch_size,
        max_articles=args.max_articles
    )
    
    logger.info(f"XML to JSON conversion complete. Processed {total_processed} files.")
    
    # Skip embedding if requested
    if args.skip_embedding:
        logger.info("Skipping embedding generation as requested")
        end_time = time.time()
        logger.info(f"XML to JSON conversion completed in {(end_time - start_time) / 60:.2f} minutes")
        return
    
    # Generate embeddings
    output_index = os.path.join(vectors_dir, "pubmed_full_embeddings.index")
    output_metadata = os.path.join(vectors_dir, "pubmed_full_metadata.json")
    
    embedding_success = generate_embeddings(
        json_dir,
        output_index,
        output_metadata,
        args.embedder_cli_script,
        batch_size=args.embedding_batch_size
    )
    
    if embedding_success:
        logger.info(f"Embeddings successfully generated and stored in {output_index}")
    else:
        logger.warning("Some errors occurred during embedding generation. Check the log for details.")
    
    end_time = time.time()
    logger.info(f"Full PubMed processing completed in {(end_time - start_time) / 60:.2f} minutes")

if __name__ == "__main__":
    main()
