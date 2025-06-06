#!/usr/bin/env python3
"""
Convert PubMed XML files to standardized JSON format for embedding.

This script processes the XML files downloaded from PubMed baseline
and converts them to a standardized JSON format suitable for
generating embeddings using the biomapper.embedder module.
"""

import os
import sys
import json
import gzip
import logging
import argparse
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import Dict, List, Any, Generator, Optional
from tqdm import tqdm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("pubmed_preprocessing.log"),
        logging.StreamHandler(sys.stdout),
    ],
)


def parse_pubmed_article(article_elem) -> Dict[str, Any]:
    """Parse a PubMed article element to a standardized format.

    Args:
        article_elem: XML element containing a PubMed article

    Returns:
        Dictionary with parsed article data
    """
    article_data = {}

    # Extract PMID
    pmid_elem = article_elem.find(".//PMID")
    if pmid_elem is not None and pmid_elem.text:
        article_data["id"] = f"PMID{pmid_elem.text}"
    else:
        # Generate a fallback ID
        article_data["id"] = f"article_{hash(ET.tostring(article_elem))}"

    # Extract article title
    title_elem = article_elem.find(".//ArticleTitle")
    if title_elem is not None and title_elem.text:
        article_data["title"] = title_elem.text

    # Extract abstract
    abstract_parts = []
    for abstract_elem in article_elem.findall(".//AbstractText"):
        if abstract_elem is not None and abstract_elem.text:
            # Check for labeled abstract sections
            label = abstract_elem.get("Label")
            if label:
                abstract_parts.append(f"{label}: {abstract_elem.text}")
            else:
                abstract_parts.append(abstract_elem.text)

    if abstract_parts:
        article_data["abstract"] = " ".join(abstract_parts)

    # Extract authors
    authors = []
    for author_elem in article_elem.findall(".//Author"):
        author_parts = []

        last_name = author_elem.find("LastName")
        if last_name is not None and last_name.text:
            author_parts.append(last_name.text)

        fore_name = author_elem.find("ForeName")
        if fore_name is not None and fore_name.text:
            author_parts.append(fore_name.text)

        if author_parts:
            authors.append(" ".join(author_parts))

    if authors:
        article_data["authors"] = authors

    # Extract journal info
    journal_elem = article_elem.find(".//Journal")
    if journal_elem is not None:
        journal_title = journal_elem.find("Title")
        if journal_title is not None and journal_title.text:
            article_data["journal"] = journal_title.text

    # Extract publication date
    pub_date_elem = article_elem.find(".//PubDate")
    if pub_date_elem is not None:
        year = pub_date_elem.find("Year")
        month = pub_date_elem.find("Month")
        day = pub_date_elem.find("Day")

        date_parts = []
        if year is not None and year.text:
            date_parts.append(year.text)
        if month is not None and month.text:
            date_parts.append(month.text)
        if day is not None and day.text:
            date_parts.append(day.text)

        if date_parts:
            article_data["publication_date"] = "-".join(date_parts)

    # Extract MeSH terms
    mesh_terms = []
    for mesh_elem in article_elem.findall(".//MeshHeading/DescriptorName"):
        if mesh_elem is not None and mesh_elem.text:
            mesh_terms.append(mesh_elem.text)

    if mesh_terms:
        article_data["mesh_terms"] = mesh_terms

    # Extract keywords
    keywords = []
    for keyword_elem in article_elem.findall(".//Keyword"):
        if keyword_elem is not None and keyword_elem.text:
            keywords.append(keyword_elem.text)

    if keywords:
        article_data["keywords"] = keywords

    return article_data


def xml_to_standardized_json(
    xml_file: str, output_file: str, max_articles: Optional[int] = None
) -> int:
    """Convert PubMed XML to standardized JSON format for embedding.

    Args:
        xml_file: Path to PubMed XML file (can be gzipped)
        output_file: Path to output JSONL file
        max_articles: Maximum number of articles to process (None for all)

    Returns:
        Number of articles processed
    """
    article_count = 0
    try:
        # Check if file is gzipped
        open_func = gzip.open if xml_file.endswith(".gz") else open
        file_mode = "rt" if xml_file.endswith(".gz") else "r"

        # Set up iterative XML parsing
        with open_func(xml_file, file_mode) as f:
            context = ET.iterparse(f, events=("end",))

            with open(output_file, "w") as out_f:
                for event, elem in context:
                    if elem.tag == "PubmedArticle":
                        try:
                            # Parse the article
                            article_data = parse_pubmed_article(elem)

                            # Create standardized format if we have basic data
                            if (
                                article_data
                                and "id" in article_data
                                and (
                                    "title" in article_data
                                    or "abstract" in article_data
                                )
                            ):
                                # Build primary text from important fields
                                primary_text_parts = []

                                if "title" in article_data:
                                    primary_text_parts.append(
                                        f"Title: {article_data['title']}"
                                    )

                                if "abstract" in article_data:
                                    primary_text_parts.append(
                                        f"Abstract: {article_data['abstract']}"
                                    )

                                # Convert to standard format
                                standardized_item = {
                                    "id": article_data["id"],
                                    "type": "pubmed_article",
                                    "primary_text": " ".join(primary_text_parts),
                                    "metadata": article_data,
                                    "source": "pubmed",
                                }

                                # Write as JSON line
                                out_f.write(json.dumps(standardized_item) + "\n")
                                article_count += 1

                                # Check if we've reached the max
                                if max_articles and article_count >= max_articles:
                                    break

                        except Exception as e:
                            logging.error(f"Error processing article: {str(e)}")

                        # Clear element to save memory
                        elem.clear()

        return article_count

    except Exception as e:
        logging.error(f"Error processing file {xml_file}: {str(e)}")
        return article_count


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Convert PubMed XML to standardized JSON format"
    )
    parser.add_argument(
        "--input-dir", required=True, help="Directory containing PubMed XML files"
    )
    parser.add_argument(
        "--output-dir", required=True, help="Output directory for JSON files"
    )
    parser.add_argument(
        "--max-articles",
        type=int,
        help="Maximum number of articles to process per file",
    )
    parser.add_argument(
        "--max-files", type=int, help="Maximum number of files to process"
    )
    args = parser.parse_args()

    input_dir = Path(args.input_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)

    # Get all XML files
    xml_files = []
    for ext in ["*.xml", "*.xml.gz"]:
        xml_files.extend(list(input_dir.glob(ext)))

    if not xml_files:
        logging.error(f"No XML files found in {input_dir}")
        return

    logging.info(f"Found {len(xml_files)} XML files to process")

    # Process files
    total_articles = 0
    files_processed = 0

    for xml_file in tqdm(
        xml_files[: args.max_files] if args.max_files else xml_files,
        desc="Processing XML files",
    ):
        output_file = output_dir / f"{xml_file.stem.split('.')[0]}.jsonl"
        logging.info(f"Processing {xml_file} -> {output_file}")

        articles = xml_to_standardized_json(
            xml_file=str(xml_file),
            output_file=str(output_file),
            max_articles=args.max_articles,
        )

        total_articles += articles
        files_processed += 1
        logging.info(f"Processed {articles} articles from {xml_file}")

    logging.info(
        f"Total processing complete: {total_articles} articles from {files_processed} files"
    )


if __name__ == "__main__":
    main()
