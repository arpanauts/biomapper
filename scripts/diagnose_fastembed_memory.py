#!/usr/bin/env python3
"""
Diagnostic script to test FastEmbed initialization and identify memory issues.

Usage:
    python scripts/diagnose_fastembed_memory.py
"""

import gc
import logging
import psutil
import sys
import time

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def log_memory(stage: str):
    """Log current memory usage."""
    process = psutil.Process()
    memory_info = process.memory_info()
    memory_mb = memory_info.rss / 1024 / 1024
    virtual_mb = memory_info.vms / 1024 / 1024

    # System memory
    system_memory = psutil.virtual_memory()
    system_available_mb = system_memory.available / 1024 / 1024
    system_used_percent = system_memory.percent

    logger.info(f"{stage}:")
    logger.info(
        f"  Process Memory: {memory_mb:.1f} MB (RSS), {virtual_mb:.1f} MB (VMS)"
    )
    logger.info(
        f"  System Memory: {system_used_percent:.1f}% used, {system_available_mb:.1f} MB available"
    )


def test_fastembed_models():
    """Test different FastEmbed models and their memory usage."""

    models_to_test = [
        "sentence-transformers/all-MiniLM-L6-v2",  # Smallest
        "BAAI/bge-small-en-v1.5",  # Your current model
        "BAAI/bge-base-en-v1.5",  # Larger model for comparison
    ]

    for model_name in models_to_test:
        logger.info(f"\n{'='*60}")
        logger.info(f"Testing model: {model_name}")
        logger.info(f"{'='*60}")

        log_memory("Before model loading")

        # Force garbage collection
        gc.collect()
        log_memory("After garbage collection")

        try:
            start_time = time.time()

            # Import FastEmbed here to avoid loading it multiple times
            from fastembed import TextEmbedding

            log_memory("After FastEmbed import")

            # Try to initialize the model
            logger.info(f"Initializing {model_name}...")
            model = TextEmbedding(model_name=model_name)

            init_time = time.time() - start_time
            log_memory(f"After {model_name} initialization ({init_time:.2f}s)")

            # Test a simple embedding
            test_text = ["This is a test sentence for embedding generation."]
            embed_start = time.time()
            embeddings = list(model.embed(test_text))
            embed_time = time.time() - embed_start

            logger.info(f"Embedding generated in {embed_time:.3f}s")
            logger.info(f"Embedding shape: {len(embeddings)} x {len(embeddings[0])}")

            log_memory("After embedding generation")

            # Clean up
            del model
            del embeddings
            gc.collect()

            log_memory("After cleanup")
            logger.info(f"✅ SUCCESS: {model_name} loaded and tested successfully")

        except Exception as e:
            logger.error(f"❌ FAILED: {model_name} - {e}")
            log_memory("After failure")

            # Try to clean up anyway
            gc.collect()

        # Wait a bit between tests
        time.sleep(2)


def test_alternative_approaches():
    """Test alternative embedding approaches."""

    logger.info(f"\n{'='*60}")
    logger.info("Testing alternative embedding approaches")
    logger.info(f"{'='*60}")

    # Test 1: SentenceTransformers directly
    logger.info("\n--- Testing SentenceTransformers directly ---")
    log_memory("Before SentenceTransformers")

    try:
        from sentence_transformers import SentenceTransformer

        model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
        log_memory("After SentenceTransformers loading")

        # Test embedding
        test_text = ["This is a test sentence."]
        embeddings = model.encode(test_text)
        logger.info(f"SentenceTransformers embedding shape: {embeddings.shape}")

        del model, embeddings
        gc.collect()
        log_memory("After SentenceTransformers cleanup")
        logger.info("✅ SUCCESS: SentenceTransformers works")

    except Exception as e:
        logger.error(f"❌ FAILED: SentenceTransformers - {e}")

    # Test 2: TF-IDF as fallback
    logger.info("\n--- Testing TF-IDF fallback ---")
    log_memory("Before TF-IDF")

    try:
        from sklearn.feature_extraction.text import TfidfVectorizer

        vectorizer = TfidfVectorizer(max_features=384, stop_words="english")
        test_texts = [
            "This is a test sentence.",
            "Another test sentence for TF-IDF.",
            "Metabolite compound name example.",
        ]

        # Fit and transform
        vectors = vectorizer.fit_transform(test_texts).toarray()
        logger.info(f"TF-IDF vector shape: {vectors.shape}")

        del vectorizer, vectors
        gc.collect()
        log_memory("After TF-IDF cleanup")
        logger.info("✅ SUCCESS: TF-IDF works as fallback")

    except Exception as e:
        logger.error(f"❌ FAILED: TF-IDF - {e}")


def check_system_requirements():
    """Check system requirements and configuration."""

    logger.info(f"\n{'='*60}")
    logger.info("System Requirements Check")
    logger.info(f"{'='*60}")

    # Python version
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Python executable: {sys.executable}")
    logger.info(f"64-bit Python: {sys.maxsize > 2**32}")

    # System info
    system_memory = psutil.virtual_memory()
    logger.info(f"Total system memory: {system_memory.total / 1024**3:.1f} GB")
    logger.info(f"Available memory: {system_memory.available / 1024**3:.1f} GB")
    logger.info(f"Memory usage: {system_memory.percent:.1f}%")

    # Check for common issues
    if not (sys.maxsize > 2**32):
        logger.warning("⚠️  WARNING: Using 32-bit Python - this may cause memory issues")
        logger.warning("   Consider upgrading to 64-bit Python")

    if system_memory.available < 2 * 1024**3:  # Less than 2GB available
        logger.warning("⚠️  WARNING: Less than 2GB memory available")
        logger.warning("   FastEmbed may struggle with limited memory")

    # Check dependencies
    logger.info("\nDependency versions:")
    try:
        import fastembed

        logger.info(f"FastEmbed version: {fastembed.__version__}")
    except ImportError:
        logger.error("❌ FastEmbed not installed")

    try:
        import onnxruntime

        logger.info(f"ONNX Runtime version: {onnxruntime.__version__}")
    except ImportError:
        logger.warning("⚠️  ONNX Runtime not found (may be bundled with FastEmbed)")

    try:
        import torch

        logger.info(f"PyTorch version: {torch.__version__}")
        logger.info(f"CUDA available: {torch.cuda.is_available()}")
    except ImportError:
        logger.info("PyTorch not installed (not required for FastEmbed)")


def main():
    """Run all diagnostic tests."""

    logger.info("FastEmbed Memory Diagnostic Tool")
    logger.info("=" * 60)

    # Initial memory state
    log_memory("Initial state")

    # System requirements
    check_system_requirements()

    # Test FastEmbed models
    test_fastembed_models()

    # Test alternatives
    test_alternative_approaches()

    # Final recommendations
    logger.info(f"\n{'='*60}")
    logger.info("RECOMMENDATIONS")
    logger.info(f"{'='*60}")

    logger.info("1. If all models failed: Consider using the lightweight script")
    logger.info(
        "2. If only large models failed: Use sentence-transformers/all-MiniLM-L6-v2"
    )
    logger.info(
        "3. If system memory is low: Reduce batch sizes and use TF-IDF fallback"
    )
    logger.info("4. If 32-bit Python: Upgrade to 64-bit Python installation")
    logger.info("5. Monitor memory usage during actual processing")


if __name__ == "__main__":
    main()
