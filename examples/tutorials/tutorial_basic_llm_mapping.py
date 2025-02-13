"""Tutorial demonstrating usage of the base LLM mapper."""

from dotenv import load_dotenv

from biomapper.mapping.llm_mapper import LLMMapper

# Load environment variables
load_dotenv()


def main() -> None:
    """Demonstrate basic LLM mapping functionality."""
    # Initialize mapper
    mapper = LLMMapper(model="gpt-4", temperature=0.0, max_tokens=1000)

    # Example 1: Basic term mapping
    print("\nExample 1: Basic term mapping")
    print("-" * 50)
    result = mapper.map_term("glucose")
    print("Query: glucose")
    if result.best_match:
        print(f"Best match: {result.best_match.target_name}")
        print(f"Confidence: {result.best_match.confidence}")
        print(f"Reasoning: {result.best_match.reasoning}")
    print(f"Cost: ${result.metrics.cost:.4f}")

    # Example 2: Mapping with target ontology
    print("\nExample 2: Mapping with target ontology")
    print("-" * 50)
    result = mapper.map_term("ATP", target_ontology="CHEBI")
    print("Query: ATP")
    if result.best_match:
        print(f"Best match: {result.best_match.target_name}")
        print(f"Confidence: {result.best_match.confidence}")
        print(f"Reasoning: {result.best_match.reasoning}")

    # Example 3: Mapping with metadata
    print("\nExample 3: Mapping with metadata")
    print("-" * 50)
    metadata = {"source": "example_source", "version": "1.0", "domain": "biochemistry"}
    result = mapper.map_term("caffeine", metadata=metadata)
    print("Query: caffeine")
    if result.best_match:
        print(f"Best match: {result.best_match.target_name}")
        print(f"Metadata: {result.best_match.metadata}")
    print(f"Trace ID: {result.trace_id}")


if __name__ == "__main__":
    main()
