#!/usr/bin/env python3
"""Tutorial demonstrating RAG-based compound mapping using Arivale data."""

import asyncio
import logging
from pathlib import Path
from typing import List

import pandas as pd
from openai import AsyncOpenAI
from phenome_arivale.data_loaders import load_arivale_metabolomics_metadata
from sentence_transformers import SentenceTransformer

from biomapper.core.base_rag import BaseEmbedder
from biomapper.pipelines.compounds.compound_mapper import (
    CompoundDocument,
    CompoundClass,
)
from biomapper.schemas.domain_schema import DomainType
from biomapper.pipelines.compounds.rag_compound_mapper import RAGCompoundMapper


# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class SentenceEmbedder(BaseEmbedder):
    """Sentence transformer based embedder."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize embedder."""
        self.model = SentenceTransformer(model_name)

    async def embed_text(self, text: str) -> List[float]:
        """Embed text using sentence transformer."""
        return self.model.encode(text).tolist()

    async def embed_texts(self, texts: List[str]) -> List[List[float]]:
        """Embed multiple texts."""
        return self.model.encode(texts).tolist()

    async def embed_batch(
        self, texts: List[str], batch_size: int = 32
    ) -> List[List[float]]:
        """Embed texts in batches.

        Args:
            texts: List of texts to embed
            batch_size: Size of each batch

        Returns:
            List of embeddings
        """
        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch = texts[i : i + batch_size]
            batch_embeddings = await self.embed_texts(batch)
            embeddings.extend(batch_embeddings)
        return embeddings


async def load_compound_data() -> List[CompoundDocument]:
    """Load compound data from Arivale metabolomics metadata.

    Returns:
        List of compound documents
    """
    # Load metabolomics metadata
    df = load_arivale_metabolomics_metadata()

    documents = []
    # Filter out rows with NaN biochemical names
    df = df.dropna(subset=["BIOCHEMICAL_NAME"])

    for idx, row in df.iterrows():
        # For testing, remove HMDB IDs from first 5 compounds
        if len(documents) < 5:
            hmdb_id = None
        else:
            hmdb_id = str(row.get("HMDB", "")) if pd.notna(row.get("HMDB")) else None

        doc = CompoundDocument(
            name=row["BIOCHEMICAL_NAME"],
            domain_type=DomainType.COMPOUND,
            compound_class=CompoundClass.SIMPLE,  # Direct compound measurement
            primary_id=str(row.get("CHEMICAL_ID", "")),
            secondary_id=str(row.get("KEGG", "")),
            refmet_id=None,
            refmet_name=None,
            chebi_id=None,
            chebi_name=None,
            hmdb_id=hmdb_id,
            pubchem_id=str(row.get("PUBCHEM", "")),
            confidence=0.0,
            source="arivale",
            metadata={
                "super_pathway": row.get("SUPER_PATHWAY", ""),
                "sub_pathway": row.get("SUB_PATHWAY", ""),
                "platform": "Metabolon",  # All from Metabolon platform
                "kegg_id": str(row.get("KEGG", "")),
                "metabolon_id": str(row.get("CHEMICAL_ID", "")),
            },
        )
        documents.append(doc)

    logger.info(f"Loaded {len(documents)} compounds from Arivale metabolomics metadata")
    return documents


def parse_llm_response(response_text: str) -> tuple[str, str, float, str, str, float]:
    """Parse the LLM response into structured data.

    Args:
        response_text: Raw response from LLM

    Returns:
        Tuple of (mapped_hmdb_id, mapped_confidence, best_guess_hmdb_id, best_guess_confidence, explanation)
    """
    try:
        # Extract the sections using the delimiters
        lines = response_text.strip().split("\n")
        mapped_hmdb_id = "None"
        mapped_hmdb_name = ""
        mapped_confidence = 0.0
        best_guess_hmdb_id = "None"
        best_guess_hmdb_name = ""
        best_guess_confidence = 0.0
        explanation = ""

        for line in lines:
            if line.startswith("MAPPED_HMDB_ID:"):
                mapped_hmdb_id = line.split(":", 1)[1].strip()
            elif line.startswith("MAPPED_HMDB_NAME:"):
                mapped_hmdb_name = line.split(":", 1)[1].strip()
            elif line.startswith("MAPPED_CONFIDENCE:"):
                conf_str = line.split(":", 1)[1].strip().rstrip("%")
                mapped_confidence = float(conf_str) / 100
            elif line.startswith("BEST_GUESS_HMDB_ID:"):
                best_guess_hmdb_id = line.split(":", 1)[1].strip()
            elif line.startswith("BEST_GUESS_HMDB_NAME:"):
                best_guess_hmdb_name = line.split(":", 1)[1].strip()
            elif line.startswith("BEST_GUESS_CONFIDENCE:"):
                conf_str = line.split(":", 1)[1].strip().rstrip("%")
                best_guess_confidence = float(conf_str) / 100
            elif line.startswith("EXPLANATION:"):
                explanation = line.split(":", 1)[1].strip()

        return (
            mapped_hmdb_id,
            mapped_hmdb_name,
            mapped_confidence,
            best_guess_hmdb_id,
            best_guess_hmdb_name,
            best_guess_confidence,
            explanation,
        )
    except Exception as e:
        logger.error(f"Failed to parse LLM response: {e}")
        return "None", "", 0.0, "None", "", 0.0, f"Error parsing LLM response: {e}"


async def main():
    """Run tutorial."""
    # Initialize components
    embedder = SentenceEmbedder()
    mapper = RAGCompoundMapper(embedder=embedder)

    # Load and index compounds from Arivale dataset
    compounds = await load_compound_data()

    # Filter compounds first
    compounds_to_process = [
        c for c in compounds if not c.hmdb_id and not c.name.startswith("X - ")
    ]

    # Create results dataframe with filtered compounds
    results_df = pd.DataFrame(
        {
            "name": [c.name for c in compounds_to_process],
            "original_hmdb_id": [c.hmdb_id for c in compounds_to_process],
            "mapped_hmdb_id": None,
            "mapped_hmdb_name": None,
            "mapped_confidence": None,
            "best_guess_hmdb_id": None,
            "best_guess_hmdb_name": None,
            "best_guess_confidence": None,
            "explanation": None,
        }
    )

    # Log some example compounds being added
    logger.info("Example compounds being added to vector store:")
    for i, doc in enumerate(compounds[:5]):  # Show first 5 compounds
        logger.info(f"\nCompound {i+1}:")
        logger.info(f"  Name: {doc.name}")
        logger.info(f"  Primary ID: {doc.primary_id}")
        logger.info(f"  HMDB ID: {doc.hmdb_id}")
        logger.info(f"  PubChem ID: {doc.pubchem_id}")
        logger.info(f"  Metadata: {doc.metadata}")

    # We don't add Arivale compounds to vector store - they are used as queries against the HMDB database
    logger.info("\nUsing Arivale compounds as queries against HMDB database...")

    # Process first 20 compounds for testing
    compounds_to_process = compounds_to_process[:20]
    logger.info(
        f"\nProcessing first 20 compounds out of {len(compounds_to_process)} total valid compounds without HMDB IDs"
    )

    # Initialize OpenAI client
    client = AsyncOpenAI()

    for compound in compounds_to_process:
        logger.info(f"\n{'='*50}")
        logger.info(f"Processing compound: {compound.name}")
        logger.info(f"{'='*50}")

        # Create rich query using only name and pathway information
        query_parts = [compound.name]  # Start with biochemical name

        if compound.metadata:
            if "super_pathway" in compound.metadata:
                query_parts.append(f"Pathway: {compound.metadata['super_pathway']}")
            if "sub_pathway" in compound.metadata:
                query_parts.append(f"Sub-pathway: {compound.metadata['sub_pathway']}")

        query = " | ".join(query_parts)
        logger.info(f"\nQuery: {query}")

        # Search vector store
        logger.info("\nSearching vector store...")
        similar_compounds = await mapper.vector_store.get_similar(
            query=query,
            k=10,  # Get more results since we'll filter some out
        )

        if not similar_compounds:
            logger.info("No similar compounds found in vector store")
            continue

        # Filter out cardiolipins and other less useful matches
        filtered_compounds = []
        for doc in similar_compounds:
            if not any(x in doc.name.lower() for x in ["cardiolipin", "cl("]):
                filtered_compounds.append(doc)
            if len(filtered_compounds) >= 5:
                break

        if not filtered_compounds:
            logger.info("No relevant compounds found after filtering")
            continue

        # Log similar compounds found
        logger.info(f"\nFound {len(filtered_compounds)} similar compounds:")
        for i, doc in enumerate(filtered_compounds):
            logger.info(f"\nSimilar Compound {i+1}:")
            logger.info(f"  Name: {doc.name}")
            logger.info(f"  HMDB ID: {doc.hmdb_id}")

        # Prepare context for LLM
        context = "\n".join(
            [
                f"Candidate {i+1}:\nName: {doc.name}\nHMDB ID: {doc.hmdb_id}"
                for i, doc in enumerate(filtered_compounds)
            ]
        )

        # Query LLM to determine best match
        prompt = f"""Given an input compound and similar compounds from HMDB, analyze potential matches and provide both a confident mapping (if one exists) and a best guess.

Input Compound:
Name: {compound.name}
Pathway: {compound.metadata.get('super_pathway', 'Unknown')}
Sub-pathway: {compound.metadata.get('sub_pathway', 'Unknown')}

Similar HMDB Compounds:
{context}

Provide your analysis in the following format EXACTLY:

MAPPED_HMDB_ID: <hmdb_id or None if no confident match>
MAPPED_HMDB_NAME: <name of the mapped compound or empty if None; use primary name only, no synonyms>
MAPPED_CONFIDENCE: <number>%
BEST_GUESS_HMDB_ID: <must provide an HMDB ID, never None>
BEST_GUESS_HMDB_NAME: <name of the best guess compound; use primary name only, no synonyms>
BEST_GUESS_CONFIDENCE: <number>%
EXPLANATION: <three complete sentences explaining both the mapping and best guess reasoning>

Guidelines:
- MAPPED_HMDB_ID should be None if no confident match exists
- BEST_GUESS_HMDB_ID must always provide an HMDB ID from the candidates
- Confidence values should be 0-100%
- For compound names, use only the primary name (first name listed) without synonyms
- Explanation should be exactly three sentences covering:
  1. Why the mapped ID was chosen or why no confident match exists
  2. Why the best guess ID was selected
  3. What key chemical/pathway features influenced the decisions
"""

        response = await client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
        )

        # Log LLM response
        logger.info("\nLLM Analysis:")
        logger.info(response.choices[0].message.content)

        # Parse response and update dataframe
        (
            mapped_id,
            mapped_name,
            mapped_conf,
            best_guess_id,
            best_guess_name,
            best_guess_conf,
            explanation,
        ) = parse_llm_response(response.choices[0].message.content)
        idx = results_df[results_df["name"] == compound.name].index[0]
        results_df.at[idx, "mapped_hmdb_id"] = mapped_id
        results_df.at[idx, "mapped_hmdb_name"] = mapped_name
        results_df.at[idx, "mapped_confidence"] = mapped_conf
        results_df.at[idx, "best_guess_hmdb_id"] = best_guess_id
        results_df.at[idx, "best_guess_hmdb_name"] = best_guess_name
        results_df.at[idx, "best_guess_confidence"] = best_guess_conf
        results_df.at[idx, "explanation"] = explanation

    # Save results
    results_df.to_csv("compound_mapping_results.csv", index=False)
    logger.info("\nResults saved to compound_mapping_results.csv")

    # Log summary statistics
    n_mapped = len(results_df[results_df["mapped_hmdb_id"] != "None"])
    avg_mapped_conf = results_df[results_df["mapped_hmdb_id"] != "None"][
        "mapped_confidence"
    ].mean()
    avg_guess_conf = results_df["best_guess_confidence"].mean()
    logger.info(f"\nMapping Summary:")
    logger.info(f"Total compounds processed: {len(results_df)}")
    logger.info(f"Compounds confidently mapped to HMDB: {n_mapped}")
    logger.info(f"Average confidence for confident mappings: {avg_mapped_conf:.2%}")
    logger.info(f"Average confidence for best guesses: {avg_guess_conf:.2%}")


if __name__ == "__main__":
    asyncio.run(main())
