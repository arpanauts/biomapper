import os
import json
import logging
from typing import List, Dict, Optional, Any
import asyncio
from pydantic import BaseModel, Field
from anthropic import AsyncAnthropic
from biomapper.schemas.mvp0_schema import LLMCandidateInfo, PubChemAnnotation

# Configure logging
logger = logging.getLogger(__name__)

# Default model to use
DEFAULT_LLM_MODEL = "claude-3-sonnet-20240229"

# Define the LLMChoice Pydantic model for the output of this component
class LLMChoice(BaseModel):
    """
    Represents the output of the LLM decision-making process for selecting
    the best PubChem CID from a list of candidates.
    """
    selected_cid: Optional[int] = Field(None, description="The selected PubChem CID, or None if no good match")
    llm_confidence: Optional[float] = Field(None, description="Confidence score from 0.0 to 1.0", ge=0.0, le=1.0)
    llm_rationale: Optional[str] = Field(None, description="Explanation for the selection")
    error_message: Optional[str] = Field(None, description="Error message if the LLM call fails")


async def select_best_cid_with_llm(
    original_biochemical_name: str,
    candidates_info: List[LLMCandidateInfo],
    anthropic_api_key: Optional[str] = None
) -> LLMChoice:
    """
    Uses an LLM to decide the best PubChem CID mapping for a biochemical name
    based on Qdrant search results and PubChem annotations.

    Args:
        original_biochemical_name: The original biochemical name to map.
        candidates_info: A list of LLMCandidateInfo objects, each containing a
                         candidate CID, its Qdrant score, and PubChem annotations.
        anthropic_api_key: Optional Anthropic API key. If not provided, will look
                          for ANTHROPIC_API_KEY environment variable.

    Returns:
        An LLMChoice object containing the LLM's decision, including selected CID,
        confidence, rationale, or error message if the operation fails.
    """
    # Validate input
    if not candidates_info:
        logger.warning("No candidates provided to LLM for decision")
        return LLMChoice(error_message="No candidates provided to LLM for decision.")

    # Get API key
    api_key = anthropic_api_key or os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        logger.error("No Anthropic API key provided or found in environment")
        return LLMChoice(error_message="No Anthropic API key provided. Set ANTHROPIC_API_KEY environment variable or pass as parameter.")

    # Initialize Anthropic client
    try:
        llm_client = AsyncAnthropic(api_key=api_key)
    except Exception as e:
        logger.error(f"Failed to initialize Anthropic client: {e}")
        return LLMChoice(error_message=f"Failed to initialize Anthropic client: {str(e)}")

    # --- Prompt Construction ---
    system_prompt = """You are an expert biochemist and cheminformatician. Your task is to determine the most accurate PubChem Compound ID (CID) for a given biochemical name, based on a list of candidates retrieved from a similarity search and their detailed PubChem annotations.

Please evaluate the information provided for each candidate against the original biochemical name. Consider factors like:
- Direct name matches in title or synonyms
- Chemical nomenclature patterns (e.g., D- vs L- forms, alpha vs beta configurations)
- IUPAC name relevance
- Molecular formula consistency
- Description relevance

Respond in JSON format with the following fields:
- "selected_cid": The PubChem CID you determine to be the best match (integer), or null if no candidate is a good match.
- "confidence": Your confidence score as a decimal between 0.0 and 1.0 (where 1.0 is highest confidence).
- "rationale": A brief explanation for your choice, or why no candidate is suitable (string).

Example response:
{"selected_cid": 5793, "confidence": 0.95, "rationale": "Direct title match with common synonym 'glucose'"}"""

    # Build user prompt
    prompt_parts = [f'Original Biochemical Name: "{original_biochemical_name}"\n']
    prompt_parts.append("Candidate PubChem CIDs and their details:")
    
    for i, candidate in enumerate(candidates_info):
        prompt_parts.append(f"\nCandidate {i+1}:")
        prompt_parts.append(f"  CID: {candidate.cid}")
        prompt_parts.append(f"  Qdrant Similarity Score: {candidate.qdrant_score:.4f}")
        prompt_parts.append(f"  PubChem Title: {candidate.annotations.title or 'N/A'}")
        prompt_parts.append(f"  IUPAC Name: {candidate.annotations.iupac_name or 'N/A'}")
        prompt_parts.append(f"  Molecular Formula: {candidate.annotations.molecular_formula or 'N/A'}")
        
        if candidate.annotations.synonyms:
            # Show up to 10 synonyms for better context
            synonyms_display = candidate.annotations.synonyms[:10]
            prompt_parts.append(f"  Synonyms ({len(synonyms_display)} shown): {', '.join(synonyms_display)}")
            if len(candidate.annotations.synonyms) > 10:
                prompt_parts.append(f"  ... and {len(candidate.annotations.synonyms) - 10} more synonyms")
        else:
            prompt_parts.append("  Synonyms: N/A")
            
        if candidate.annotations.description:
            # Truncate very long descriptions
            desc = candidate.annotations.description
            if len(desc) > 200:
                desc = desc[:197] + "..."
            prompt_parts.append(f"  Description: {desc}")
        else:
            prompt_parts.append("  Description: N/A")
    
    prompt_parts.append("\nBased on the information above, please provide your mapping decision in the specified JSON format.")
    user_prompt = "\n".join(prompt_parts)

    # Log the prompt (summary)
    logger.info(f"Sending LLM request for biochemical name: '{original_biochemical_name}' with {len(candidates_info)} candidates")
    logger.debug(f"Full prompt length: {len(system_prompt) + len(user_prompt)} characters")

    # Make the API call
    try:
        response = await llm_client.messages.create(
            model=DEFAULT_LLM_MODEL,
            max_tokens=500,
            temperature=0.1,  # Low temperature for consistent, deterministic responses
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
        
        # Extract the response text
        if response.content and len(response.content) > 0:
            response_text = response.content[0].text
            logger.debug(f"LLM raw response: {response_text[:200]}...")
        else:
            logger.error("Empty response from LLM")
            return LLMChoice(error_message="Empty response from LLM")
        
        # Parse JSON response
        try:
            # Try to extract JSON from the response (sometimes LLMs add extra text)
            import re
            json_match = re.search(r'\{[^{}]*\}', response_text, re.DOTALL)
            if json_match:
                json_str = json_match.group()
                llm_output = json.loads(json_str)
            else:
                llm_output = json.loads(response_text)
            
            # Convert confidence to float if it's a string
            confidence = llm_output.get("confidence")
            if confidence is not None:
                if isinstance(confidence, str):
                    # Handle string confidence levels
                    confidence_map = {
                        "high": 0.9,
                        "medium": 0.6,
                        "low": 0.3,
                        "none": 0.0
                    }
                    confidence_lower = confidence.lower()
                    if confidence_lower in confidence_map:
                        confidence = confidence_map[confidence_lower]
                    else:
                        # Try to parse as float
                        try:
                            confidence = float(confidence)
                        except ValueError:
                            logger.warning(f"Could not parse confidence value: {confidence}, defaulting to 0.5")
                            confidence = 0.5
                else:
                    confidence = float(confidence)
            
            # Create the result
            result = LLMChoice(
                selected_cid=llm_output.get("selected_cid"),
                llm_confidence=confidence,
                llm_rationale=llm_output.get("rationale", "No rationale provided")
            )
            
            logger.info(f"LLM selected CID {result.selected_cid} with confidence {result.llm_confidence}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response as JSON: {e}")
            logger.debug(f"Response that failed to parse: {response_text}")
            return LLMChoice(error_message=f"Failed to parse LLM response as JSON: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing LLM response: {e}")
            return LLMChoice(error_message=f"Error processing LLM response: {str(e)}")
    
    except Exception as e:
        logger.error(f"Error calling Anthropic API: {e}")
        return LLMChoice(error_message=f"LLM API error: {str(e)}")

# Example usage (for testing this component independently)
async def main():
    """
    Example usage of the select_best_cid_with_llm function.
    To run this example, set the ANTHROPIC_API_KEY environment variable:
    export ANTHROPIC_API_KEY="your_api_key_here"
    """
    # Configure logging for the example
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Example 1: Glucose with multiple candidates
    test_name = "glucose"
    test_candidates = [
        LLMCandidateInfo(
            cid=5793,
            qdrant_score=0.95,
            annotations=PubChemAnnotation(
                cid=5793,
                title="Glucose",
                iupac_name="(2R,3S,4R,5R)-2,3,4,5,6-Pentahydroxyhexanal",
                molecular_formula="C6H12O6",
                synonyms=["D-Glucose", "Dextrose", "Grape sugar", "Blood sugar"],
                description="A primary source of energy for living organisms. The most abundant monosaccharide."
            )
        ),
        LLMCandidateInfo(
            cid=107526,
            qdrant_score=0.88,
            annotations=PubChemAnnotation(
                cid=107526,
                title="beta-D-Glucopyranose",
                iupac_name="(2R,3R,4S,5S,6R)-6-(hydroxymethyl)oxane-2,3,4,5-tetrol",
                molecular_formula="C6H12O6",
                synonyms=["beta-D-glucose", "beta-glucose"],
                description="The beta-anomeric form of D-glucopyranose."
            )
        ),
        LLMCandidateInfo(
            cid=79025,
            qdrant_score=0.82,
            annotations=PubChemAnnotation(
                cid=79025,
                title="alpha-D-Glucose",
                molecular_formula="C6H12O6",
                synonyms=["alpha-D-glucopyranose", "alpha-glucose"],
                description="The alpha-anomeric form of D-glucopyranose."
            )
        )
    ]
    
    print(f"\n{'='*60}")
    print(f"Testing LLM mapper for: '{test_name}'")
    print(f"Number of candidates: {len(test_candidates)}")
    print(f"{'='*60}\n")
    
    # Test with API key from environment
    llm_decision = await select_best_cid_with_llm(test_name, test_candidates)
    
    print(f"LLM Decision for '{test_name}':")
    print(f"  Selected CID: {llm_decision.selected_cid}")
    print(f"  Confidence: {llm_decision.llm_confidence}")
    print(f"  Rationale: {llm_decision.llm_rationale}")
    if llm_decision.error_message:
        print(f"  Error: {llm_decision.error_message}")
    
    # Example 2: Ambiguous case - "vitamin C"
    print(f"\n{'='*60}")
    test_name2 = "vitamin C"
    test_candidates2 = [
        LLMCandidateInfo(
            cid=54670067,
            qdrant_score=0.92,
            annotations=PubChemAnnotation(
                cid=54670067,
                title="Ascorbic acid",
                iupac_name="(5R)-5-[(1S)-1,2-dihydroxyethyl]-3,4-dihydroxyfuran-2(5H)-one",
                molecular_formula="C6H8O6",
                synonyms=["L-Ascorbic acid", "Vitamin C", "L-Ascorbate"],
                description="A water-soluble vitamin found in citrus fruits."
            )
        ),
        LLMCandidateInfo(
            cid=54680673,
            qdrant_score=0.85,
            annotations=PubChemAnnotation(
                cid=54680673,
                title="Sodium ascorbate",
                molecular_formula="C6H7NaO6",
                synonyms=["Sodium L-ascorbate", "Vitamin C sodium salt"],
                description="The sodium salt of ascorbic acid."
            )
        )
    ]
    
    print(f"Testing LLM mapper for: '{test_name2}'")
    print(f"Number of candidates: {len(test_candidates2)}")
    print(f"{'='*60}\n")
    
    llm_decision2 = await select_best_cid_with_llm(test_name2, test_candidates2)
    
    print(f"LLM Decision for '{test_name2}':")
    print(f"  Selected CID: {llm_decision2.selected_cid}")
    print(f"  Confidence: {llm_decision2.llm_confidence}")
    print(f"  Rationale: {llm_decision2.llm_rationale}")
    if llm_decision2.error_message:
        print(f"  Error: {llm_decision2.error_message}")
    
    # Example 3: No good match case
    print(f"\n{'='*60}")
    test_name3 = "unknown_compound_xyz"
    test_candidates3 = [
        LLMCandidateInfo(
            cid=12345,
            qdrant_score=0.45,
            annotations=PubChemAnnotation(
                cid=12345,
                title="Benzene",
                molecular_formula="C6H6",
                synonyms=["Benzol", "Phenyl hydride"]
            )
        )
    ]
    
    print(f"Testing LLM mapper for: '{test_name3}'")
    print(f"Number of candidates: {len(test_candidates3)}")
    print(f"{'='*60}\n")
    
    llm_decision3 = await select_best_cid_with_llm(test_name3, test_candidates3)
    
    print(f"LLM Decision for '{test_name3}':")
    print(f"  Selected CID: {llm_decision3.selected_cid}")
    print(f"  Confidence: {llm_decision3.llm_confidence}")
    print(f"  Rationale: {llm_decision3.llm_rationale}")
    if llm_decision3.error_message:
        print(f"  Error: {llm_decision3.error_message}")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())
