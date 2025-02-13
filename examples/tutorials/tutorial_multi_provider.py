"""Tutorial demonstrating usage of the multi-provider RAG mapper."""

from dotenv import load_dotenv

from biomapper.mapping.multi_provider_rag import MultiProviderMapper
from biomapper.schemas.provider_schemas import ProviderType, ProviderConfig

# Load environment variables
load_dotenv()


def main() -> None:
    """Demonstrate multi-provider mapping functionality."""
    # Setup provider configurations
    provider_configs = {
        ProviderType.CHEBI: ProviderConfig(
            name=ProviderType.CHEBI,
            data_path="data/chebi.tsv",
            base_url="https://chebi.example.com",
            api_key="dummy_key",
            embedding_model="text-embedding-ada-002",
            chunk_size=1000,
            overlap=100,
        ),
        ProviderType.UNICHEM: ProviderConfig(
            name=ProviderType.UNICHEM,
            data_path="data/unichem.tsv",
            base_url="https://unichem.example.com",
            api_key="dummy_key",
            embedding_model="text-embedding-ada-002",
            chunk_size=1000,
            overlap=100,
        ),
        ProviderType.REFMET: ProviderConfig(
            name=ProviderType.REFMET,
            data_path="data/refmet.tsv",
            base_url="https://refmet.example.com",
            api_key="dummy_key",
            embedding_model="text-embedding-ada-002",
            chunk_size=1000,
            overlap=100,
        ),
    }

    # Initialize multi-provider mapper
    mapper = MultiProviderMapper(
        providers=provider_configs,
        langfuse_key=None,  # Optional: Add your Langfuse key here
    )

    # Example 1: Basic multi-provider mapping
    print("\nExample 1: Basic multi-provider mapping")
    print("-" * 50)
    result = mapper.map_term("glucose")
    print("Query: glucose")
    if result.best_match:
        print(f"Best match: {result.best_match.target_name}")
        print(f"Confidence: {result.best_match.confidence}")
        print(f"Reasoning: {result.best_match.reasoning}")

    # Example 2: Mapping with specific providers
    print("\nExample 2: Mapping with specific providers")
    print("-" * 50)
    result = mapper.map_term("ATP", target_ontology=ProviderType.CHEBI.value)
    print("Query: ATP")
    if result.best_match:
        print(f"Best match: {result.best_match.target_name}")
    print("Cross-references:")
    for i, match in enumerate(result.matches[1:], 1):
        print(f"\n{i}. {match.target_name}")
        if match.metadata:
            print(f"   Provider: {match.metadata.get('provider', 'unknown')}")
        print(f"   Confidence: {match.confidence}")

    # Example 3: Complex compound with cross-references
    print("\nExample 3: Complex compound with cross-references")
    print("-" * 50)
    result = mapper.map_term("glucose-6-phosphate")
    print("Query: glucose-6-phosphate")
    if result.best_match:
        print(f"Best match: {result.best_match.target_name}")
    print("\nCross-references across providers:")
    for i, match in enumerate(result.matches[1:], 1):
        print(f"\n{i}. {match.target_name}")
        if match.metadata:
            print(f"   Provider: {match.metadata.get('provider', 'unknown')}")
        print(f"   ID: {match.target_id}")

    # Example 4: Mapping with metadata
    print("\nExample 4: Mapping with metadata")
    print("-" * 50)
    metadata = {
        "experiment_type": "metabolomics",
        "platform": "mass_spec",
        "confidence_threshold": "0.8",
        "cross_reference_required": "true",
    }
    result = mapper.map_term(
        "caffeine",
        target_ontology=ProviderType.CHEBI.value,
        metadata=metadata,
    )
    print("Query: caffeine")
    if result.best_match:
        print(f"Best match: {result.best_match.target_name}")
        print(f"Metadata: {result.best_match.metadata}")
        print(f"Trace ID: {result.trace_id}")


if __name__ == "__main__":
    main()
