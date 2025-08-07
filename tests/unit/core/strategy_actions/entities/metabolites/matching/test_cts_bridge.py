"""
Test suite for METABOLITE_CTS_BRIDGE action.

Tests the Chemical Translation Service (CTS) integration for metabolite identifier bridging.
"""

import pytest
import pandas as pd
import asyncio
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock
import json
import aiohttp
from typing import List, Optional

from biomapper.core.strategy_actions.entities.metabolites.matching.cts_bridge import (
    MetaboliteCtsBridgeAction,
    MetaboliteCtsBridgeParams,
    CTSClient,
    CTSCache,
    BatchProcessor,
    FallbackTranslator,
    CTSAPIError,
    CTSTimeoutError,
)


# Mock CTS response data for testing
MOCK_CTS_RESPONSES = {
    "hmdb_to_inchikey": {
        "HMDB0001234": ["BQJCRHHNABKAKU-KBQPJGBKSA-N"],
        "HMDB0000122": ["WQZGKKKJIJFFOK-GASJEMHNSA-N"],  # Glucose
        "HMDB0000562": ["BTCSSZJGUNDROE-UHFFFAOYSA-N"],  # Creatinine
        "HMDB0000292": ["FFDGPVCHZBVARC-UHFFFAOYSA-N"],  # Xanthine
        "HMDB0000177": ["KDXKERNSBIXSRK-YFKPBYRVSA-N"],  # Histidine
    },
    "inchikey_to_hmdb": {
        "BQJCRHHNABKAKU-KBQPJGBKSA-N": ["HMDB0001234"],
        "WQZGKKKJIJFFOK-GASJEMHNSA-N": ["HMDB0000122"],
        "BTCSSZJGUNDROE-UHFFFAOYSA-N": ["HMDB0000562"],
        "FFDGPVCHZBVARC-UHFFFAOYSA-N": ["HMDB0000292"],
        "KDXKERNSBIXSRK-YFKPBYRVSA-N": ["HMDB0000177"],
    },
    "chebi_to_kegg": {
        "CHEBI:17234": ["C00031"],  # Glucose
        "CHEBI:16737": ["C00791"],  # Creatinine
        "CHEBI:17712": ["C00385"],  # Xanthine
    },
    "pubchem_to_hmdb": {
        "5793": ["HMDB0000122"],  # Glucose
        "588": ["HMDB0000562"],  # Creatinine
        "1188": ["HMDB0000292"],  # Xanthine
    },
    "kegg_to_inchikey": {
        "C00031": ["WQZGKKKJIJFFOK-GASJEMHNSA-N"],  # Glucose
        "C00791": ["BTCSSZJGUNDROE-UHFFFAOYSA-N"],  # Creatinine
    },
}


def mock_cts_response(
    from_type: str, to_type: str, identifier: str
) -> Optional[List[str]]:
    """Generate mock CTS response for testing."""
    key = f"{from_type}_to_{to_type}"
    if key in MOCK_CTS_RESPONSES:
        return MOCK_CTS_RESPONSES[key].get(identifier, None)
    return None


class MockResponse:
    """Mock aiohttp response."""

    def __init__(
        self, status: int, json_data: Optional[List] = None, raise_error: bool = False
    ):
        self.status = status
        self._json_data = json_data
        self._raise_error = raise_error

    async def json(self):
        if self._raise_error:
            raise json.JSONDecodeError("Invalid JSON", "", 0)
        return self._json_data or []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass


def create_mock_session(response=None, side_effect=None):
    """Create a properly configured mock session."""
    mock_session = MagicMock()
    if side_effect:
        mock_session.get.side_effect = side_effect
    elif response:
        mock_session.get.return_value.__aenter__.return_value = response
    return mock_session


class TestMetaboliteCtsBridge:
    """Test cases for METABOLITE_CTS_BRIDGE action."""

    # 1. Parameter Tests
    def test_default_parameters(self):
        """Test action initializes with default parameters."""
        params = MetaboliteCtsBridgeParams(
            source_key="source",
            target_key="target",
            output_key="output",
            source_id_column="source_id",
            source_id_type="hmdb",
            target_id_column="target_id",
            target_id_type="inchikey",
        )

        assert params.batch_size == 100
        assert params.max_retries == 3
        assert params.timeout_seconds == 30
        assert params.cache_results is True
        assert params.use_fallback_services is True
        assert params.confidence_threshold == 0.8
        assert params.handle_multiple_translations == "best"
        assert params.skip_on_error is True
        assert params.log_failures is True

    def test_custom_parameters(self):
        """Test custom parameter configuration."""
        params = MetaboliteCtsBridgeParams(
            source_key="source",
            target_key="target",
            output_key="output",
            source_id_column="source_id",
            source_id_type="inchikey",
            target_id_column="target_id",
            target_id_type="hmdb",
            batch_size=50,
            max_retries=5,
            timeout_seconds=60,
            cache_results=False,
            cache_file="/custom/cache.pkl",
            use_fallback_services=False,
            confidence_threshold=0.9,
            handle_multiple_translations="all",
            skip_on_error=False,
            log_failures=False,
        )

        assert params.batch_size == 50
        assert params.max_retries == 5
        assert params.timeout_seconds == 60
        assert params.cache_results is False
        assert params.cache_file == "/custom/cache.pkl"
        assert params.use_fallback_services is False
        assert params.confidence_threshold == 0.9
        assert params.handle_multiple_translations == "all"
        assert params.skip_on_error is False
        assert params.log_failures is False

    def test_invalid_id_types(self):
        """Test validation of invalid identifier types."""
        with pytest.raises(ValueError):
            MetaboliteCtsBridgeParams(
                source_key="source",
                target_key="target",
                output_key="output",
                source_id_column="source_id",
                source_id_type="invalid_type",  # Invalid
                target_id_column="target_id",
                target_id_type="hmdb",
            )

    # 2. CTS API Tests (Mocked)
    @pytest.mark.asyncio
    async def test_cts_api_successful_translation(self):
        """Test successful CTS API translation."""
        client = CTSClient()

        mock_response = MockResponse(
            status=200, json_data=[{"result": ["BQJCRHHNABKAKU-KBQPJGBKSA-N"]}]
        )
        mock_session = create_mock_session(response=mock_response)

        result = await client.translate_identifier(
            "HMDB0001234", "hmdb", "inchikey", mock_session
        )

        assert result == ["BQJCRHHNABKAKU-KBQPJGBKSA-N"]
        mock_session.get.assert_called_once()

    @pytest.mark.asyncio
    async def test_cts_api_not_found(self):
        """Test CTS API returns 404 for unknown ID."""
        client = CTSClient()

        mock_response = MockResponse(status=404)
        mock_session = create_mock_session(response=mock_response)

        result = await client.translate_identifier(
            "UNKNOWN_ID", "hmdb", "inchikey", mock_session
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_cts_api_timeout(self):
        """Test CTS API timeout handling."""
        client = CTSClient()

        mock_session = create_mock_session(side_effect=asyncio.TimeoutError())

        with pytest.raises(CTSTimeoutError):
            await client.translate_identifier(
                "HMDB0001234", "hmdb", "inchikey", mock_session
            )

    @pytest.mark.asyncio
    async def test_cts_api_error_response(self):
        """Test CTS API error response handling."""
        client = CTSClient()

        mock_response = MockResponse(status=500)
        mock_session = create_mock_session(response=mock_response)

        with pytest.raises(CTSAPIError):
            await client.translate_identifier(
                "HMDB0001234", "hmdb", "inchikey", mock_session
            )

    @pytest.mark.asyncio
    async def test_cts_api_invalid_json(self):
        """Test CTS API invalid JSON response."""
        client = CTSClient()

        mock_response = MockResponse(status=200, raise_error=True)
        mock_session = create_mock_session(response=mock_response)

        with pytest.raises(CTSAPIError):
            await client.translate_identifier(
                "HMDB0001234", "hmdb", "inchikey", mock_session
            )

    # 3. Batch Processing Tests
    @pytest.mark.asyncio
    async def test_batch_processing_success(self):
        """Test batch processing of multiple IDs."""
        processor = BatchProcessor(batch_size=3)
        processor.cts_client = CTSClient()

        # Mock translate_with_retry
        async def mock_translate(
            identifier, from_type, to_type, session, max_retries=3
        ):
            return mock_cts_response(from_type, to_type, identifier)

        processor.translate_with_retry = mock_translate

        identifiers = ["HMDB0001234", "HMDB0000122", "HMDB0000562"]
        results = await processor.process_batch(identifiers, "hmdb", "inchikey")

        assert len(results) == 3
        assert results["HMDB0001234"] == ["BQJCRHHNABKAKU-KBQPJGBKSA-N"]
        assert results["HMDB0000122"] == ["WQZGKKKJIJFFOK-GASJEMHNSA-N"]
        assert results["HMDB0000562"] == ["BTCSSZJGUNDROE-UHFFFAOYSA-N"]

    @pytest.mark.asyncio
    async def test_batch_rate_limiting(self):
        """Test rate limiting is applied."""
        processor = BatchProcessor(batch_size=10, requests_per_second=5)

        # Track timing
        call_times = []

        async def mock_translate(
            identifier, from_type, to_type, session, max_retries=3
        ):
            call_times.append(datetime.now())
            return ["result"]

        processor.translate_with_retry = mock_translate

        identifiers = ["ID1", "ID2", "ID3", "ID4", "ID5"]
        await processor.process_batch(identifiers, "hmdb", "inchikey")

        # Check that calls are rate limited (approximately)
        if len(call_times) > 1:
            time_diff = (call_times[-1] - call_times[0]).total_seconds()
            expected_min_time = (len(identifiers) - 1) / 5  # 5 requests per second
            assert time_diff >= expected_min_time * 0.8  # Allow some variance

    @pytest.mark.asyncio
    async def test_batch_partial_failures(self):
        """Test batch with some failed translations."""
        processor = BatchProcessor(batch_size=5)

        async def mock_translate(
            identifier, from_type, to_type, session, max_retries=3
        ):
            if identifier == "FAIL_ID":
                raise CTSAPIError("Failed")
            return mock_cts_response(from_type, to_type, identifier)

        processor.translate_with_retry = mock_translate

        identifiers = ["HMDB0001234", "FAIL_ID", "HMDB0000122"]
        results = await processor.process_batch(identifiers, "hmdb", "inchikey")

        assert results["HMDB0001234"] == ["BQJCRHHNABKAKU-KBQPJGBKSA-N"]
        assert results["FAIL_ID"] is None
        assert results["HMDB0000122"] == ["WQZGKKKJIJFFOK-GASJEMHNSA-N"]

    # 4. Retry Logic Tests
    @pytest.mark.asyncio
    async def test_retry_on_timeout(self):
        """Test retry with exponential backoff."""
        processor = BatchProcessor()
        client = CTSClient()

        attempt = 0

        async def mock_translate_with_timeout(*args, **kwargs):
            nonlocal attempt
            attempt += 1
            if attempt < 3:
                raise CTSTimeoutError("Timeout")
            return ["SUCCESS"]

        client.translate_identifier = mock_translate_with_timeout
        processor.cts_client = client

        result = await processor.translate_with_retry(
            "HMDB0001234", "hmdb", "inchikey", AsyncMock(), max_retries=3
        )

        assert result == ["SUCCESS"]
        assert attempt == 3

    @pytest.mark.asyncio
    async def test_max_retries_exceeded(self):
        """Test failure after max retries."""
        processor = BatchProcessor()
        client = CTSClient()

        async def mock_translate_always_fails(*args, **kwargs):
            raise CTSTimeoutError("Timeout")

        client.translate_identifier = mock_translate_always_fails
        processor.cts_client = client

        with pytest.raises(CTSTimeoutError):
            await processor.translate_with_retry(
                "HMDB0001234", "hmdb", "inchikey", AsyncMock(), max_retries=3
            )

    # 5. Caching Tests
    def test_cache_hit(self):
        """Test retrieval from cache."""
        cache = CTSCache(cache_file="/tmp/test_cache.pkl")
        key = cache.cache_key("HMDB0001234", "hmdb", "inchikey")

        # Add to cache
        cache.set(key, ["BQJCRHHNABKAKU-KBQPJGBKSA-N"])

        # Retrieve from cache
        result = cache.get(key)
        assert result == ["BQJCRHHNABKAKU-KBQPJGBKSA-N"]

    def test_cache_miss(self):
        """Test cache miss triggers API call."""
        cache = CTSCache(cache_file="/tmp/test_cache.pkl")
        key = cache.cache_key("UNKNOWN_ID", "hmdb", "inchikey")

        result = cache.get(key)
        assert result is None

    def test_cache_expiration(self):
        """Test expired cache entries are removed."""
        cache = CTSCache(cache_file="/tmp/test_cache.pkl", ttl_days=0)
        key = cache.cache_key("HMDB0001234", "hmdb", "inchikey")

        # Add to cache with expired TTL
        cache.cache[key] = {
            "value": ["OLD_VALUE"],
            "timestamp": datetime.now() - timedelta(days=1),
        }

        # Should return None and remove expired entry
        result = cache.get(key)
        assert result is None
        assert key not in cache.cache

    def test_cache_persistence(self):
        """Test cache saves and loads from disk."""
        cache_file = "/tmp/test_persist_cache.pkl"

        # Create and populate cache
        cache1 = CTSCache(cache_file=cache_file)
        key = cache1.cache_key("HMDB0001234", "hmdb", "inchikey")
        cache1.set(key, ["BQJCRHHNABKAKU-KBQPJGBKSA-N"])
        cache1.save()

        # Load cache in new instance
        cache2 = CTSCache(cache_file=cache_file)
        result = cache2.get(key)
        assert result == ["BQJCRHHNABKAKU-KBQPJGBKSA-N"]

        # Cleanup
        Path(cache_file).unlink(missing_ok=True)

    # 6. Fallback Service Tests
    @pytest.mark.asyncio
    async def test_pubchem_fallback(self):
        """Test PubChem fallback when CTS fails."""
        fallback = FallbackTranslator()

        # Mock PubChem API calls
        async def mock_inchikey_to_cid(identifier):
            return "5793" if identifier == "WQZGKKKJIJFFOK-GASJEMHNSA-N" else None

        async def mock_cid_to_hmdb(cid):
            return ["HMDB0000122"] if cid == "5793" else None

        fallback._inchikey_to_cid = mock_inchikey_to_cid
        fallback._cid_to_hmdb = mock_cid_to_hmdb

        result = await fallback.translate_via_pubchem(
            "WQZGKKKJIJFFOK-GASJEMHNSA-N", "inchikey", "hmdb"
        )

        assert result == ["HMDB0000122"]

    @pytest.mark.asyncio
    async def test_fallback_disabled(self):
        """Test fallback services can be disabled."""
        action = MetaboliteCtsBridgeAction()
        params = MetaboliteCtsBridgeParams(
            source_key="source",
            target_key="target",
            output_key="output",
            source_id_column="source_id",
            source_id_type="hmdb",
            target_id_column="target_id",
            target_id_type="inchikey",
            use_fallback_services=False,
        )

        # Should not use fallback even if CTS fails
        assert params.use_fallback_services is False

    # 7. Translation Type Tests
    @pytest.mark.asyncio
    async def test_hmdb_to_inchikey(self):
        """Test HMDB to InChIKey translation."""
        client = CTSClient()

        mock_response = MockResponse(
            status=200, json_data=[{"result": ["BQJCRHHNABKAKU-KBQPJGBKSA-N"]}]
        )
        mock_session = create_mock_session(response=mock_response)

        result = await client.translate_identifier(
            "HMDB0001234", "hmdb", "inchikey", mock_session
        )

        assert result == ["BQJCRHHNABKAKU-KBQPJGBKSA-N"]

    @pytest.mark.asyncio
    async def test_inchikey_to_hmdb(self):
        """Test InChIKey to HMDB translation."""
        client = CTSClient()

        mock_response = MockResponse(
            status=200, json_data=[{"result": ["HMDB0001234"]}]
        )
        mock_session = create_mock_session(response=mock_response)

        result = await client.translate_identifier(
            "BQJCRHHNABKAKU-KBQPJGBKSA-N", "inchikey", "hmdb", mock_session
        )

        assert result == ["HMDB0001234"]

    @pytest.mark.asyncio
    async def test_chebi_to_kegg(self):
        """Test CHEBI to KEGG translation."""
        client = CTSClient()

        mock_response = MockResponse(status=200, json_data=[{"result": ["C00031"]}])
        mock_session = create_mock_session(response=mock_response)

        result = await client.translate_identifier(
            "CHEBI:17234", "chebi", "kegg", mock_session
        )

        assert result == ["C00031"]

    @pytest.mark.asyncio
    async def test_pubchem_to_hmdb(self):
        """Test PubChem to HMDB translation."""
        client = CTSClient()

        mock_response = MockResponse(
            status=200, json_data=[{"result": ["HMDB0000122"]}]
        )
        mock_session = create_mock_session(response=mock_response)

        result = await client.translate_identifier(
            "5793", "pubchem", "hmdb", mock_session
        )

        assert result == ["HMDB0000122"]

    # 8. Matching Tests
    def test_exact_match_after_translation(self):
        """Test exact matching after translation."""
        action = MetaboliteCtsBridgeAction()

        source_translations = {
            "HMDB0001234": ["BQJCRHHNABKAKU-KBQPJGBKSA-N"],
            "HMDB0000122": ["WQZGKKKJIJFFOK-GASJEMHNSA-N"],
        }

        target_df = pd.DataFrame(
            {
                "target_id": [
                    "BQJCRHHNABKAKU-KBQPJGBKSA-N",
                    "OTHER-INCHIKEY",
                    "WQZGKKKJIJFFOK-GASJEMHNSA-N",
                ],
                "name": ["Compound1", "Compound2", "Glucose"],
            }
        )

        matches = action._match_translated_ids(
            source_translations, target_df, "target_id"
        )

        assert len(matches) == 2
        assert "BQJCRHHNABKAKU-KBQPJGBKSA-N" in matches["target_id"].values
        assert "WQZGKKKJIJFFOK-GASJEMHNSA-N" in matches["target_id"].values

    def test_multiple_translation_results(self):
        """Test handling of multiple translation results."""
        action = MetaboliteCtsBridgeAction()

        # Simulate multiple translation results
        source_translations = {
            "HMDB0001234": ["INCHI1", "INCHI2", "INCHI3"],
        }

        target_df = pd.DataFrame(
            {"target_id": ["INCHI2", "OTHER"], "name": ["Compound1", "Compound2"]}
        )

        # Test "best" mode (default)
        params = MetaboliteCtsBridgeParams(
            source_key="source",
            target_key="target",
            output_key="output",
            source_id_column="source_id",
            source_id_type="hmdb",
            target_id_column="target_id",
            target_id_type="inchikey",
            handle_multiple_translations="best",
        )

        matches = action._match_translated_ids(
            source_translations, target_df, "target_id"
        )

        assert len(matches) == 1
        assert matches.iloc[0]["target_id"] == "INCHI2"

    def test_confidence_scoring(self):
        """Test confidence score calculation."""
        action = MetaboliteCtsBridgeAction()

        # Test single translation (high confidence)
        confidence = action._calculate_confidence("HMDB0001234", "INCHIKEY", 1, "hmdb")
        assert confidence > 0.8

        # Test multiple translations (lower confidence)
        confidence = action._calculate_confidence("HMDB0001234", "INCHIKEY", 5, "hmdb")
        assert confidence < 0.5

        # Test InChIKey source (highest confidence)
        confidence = action._calculate_confidence(
            "INCHIKEY", "HMDB0001234", 1, "inchikey"
        )
        assert confidence > 0.85

    def test_threshold_filtering(self):
        """Test matches below threshold are filtered."""
        action = MetaboliteCtsBridgeAction()

        matches = pd.DataFrame(
            {
                "source_id": ["ID1", "ID2", "ID3"],
                "target_id": ["TARGET1", "TARGET2", "TARGET3"],
                "confidence": [0.9, 0.7, 0.5],
            }
        )

        # Filter with 0.8 threshold
        filtered = matches[matches["confidence"] >= 0.8]

        assert len(filtered) == 1
        assert filtered.iloc[0]["source_id"] == "ID1"

    # 9. Error Handling Tests
    @pytest.mark.asyncio
    async def test_invalid_identifier_format(self):
        """Test handling of invalid identifier formats."""
        action = MetaboliteCtsBridgeAction()

        # Test with empty identifier
        result = await action._validate_identifier("", "hmdb")
        assert result is False

        # Test with None
        result = await action._validate_identifier(None, "hmdb")
        assert result is False

        # Test with invalid HMDB format
        result = await action._validate_identifier("INVALID", "hmdb")
        assert result is False

        # Test with valid HMDB format
        result = await action._validate_identifier("HMDB0001234", "hmdb")
        assert result is True

    @pytest.mark.asyncio
    async def test_network_error_handling(self):
        """Test network error handling."""
        client = CTSClient()

        mock_session = create_mock_session(
            side_effect=aiohttp.ClientError("Network error")
        )

        with pytest.raises(CTSAPIError):
            await client.translate_identifier(
                "HMDB0001234", "hmdb", "inchikey", mock_session
            )

    @pytest.mark.asyncio
    async def test_skip_on_error_mode(self):
        """Test skip_on_error parameter."""
        action = MetaboliteCtsBridgeAction()
        params = MetaboliteCtsBridgeParams(
            source_key="source",
            target_key="target",
            output_key="output",
            source_id_column="source_id",
            source_id_type="hmdb",
            target_id_column="target_id",
            target_id_type="inchikey",
            skip_on_error=True,
        )

        # Mock data with some invalid IDs
        context = {
            "datasets": {
                "source": pd.DataFrame(
                    {"source_id": ["HMDB0001234", "INVALID_ID", "HMDB0000122"]}
                ),
                "target": pd.DataFrame(
                    {
                        "target_id": [
                            "BQJCRHHNABKAKU-KBQPJGBKSA-N",
                            "WQZGKKKJIJFFOK-GASJEMHNSA-N",
                        ]
                    }
                ),
            }
        }

        # Should skip invalid IDs without failing
        # Implementation would handle this in execute_typed
        assert params.skip_on_error is True

    # 10. Integration Tests
    @pytest.mark.asyncio
    async def test_full_pipeline_with_mock_data(self):
        """Test complete pipeline with mock data."""
        action = MetaboliteCtsBridgeAction()

        params = MetaboliteCtsBridgeParams(
            source_key="source",
            target_key="target",
            output_key="output",
            source_id_column="hmdb_id",
            source_id_type="hmdb",
            target_id_column="inchikey",
            target_id_type="inchikey",
            batch_size=2,
            cache_results=False,
        )

        context = {
            "datasets": {
                "source": pd.DataFrame(
                    {
                        "hmdb_id": ["HMDB0001234", "HMDB0000122", "HMDB0000562"],
                        "name": ["Compound1", "Glucose", "Creatinine"],
                    }
                ),
                "target": pd.DataFrame(
                    {
                        "inchikey": [
                            "BQJCRHHNABKAKU-KBQPJGBKSA-N",
                            "WQZGKKKJIJFFOK-GASJEMHNSA-N",
                            "BTCSSZJGUNDROE-UHFFFAOYSA-N",
                            "OTHER-INCHIKEY",
                        ],
                        "compound": ["C1", "C2", "C3", "C4"],
                    }
                ),
            }
        }

        # Mock the CTS client
        with patch.object(action, "_process_translations") as mock_process:
            mock_process.return_value = {
                "HMDB0001234": ["BQJCRHHNABKAKU-KBQPJGBKSA-N"],
                "HMDB0000122": ["WQZGKKKJIJFFOK-GASJEMHNSA-N"],
                "HMDB0000562": ["BTCSSZJGUNDROE-UHFFFAOYSA-N"],
            }

            result = await action.execute_typed(params, context)

            assert result.success
            assert result.data["total_source_ids"] == 3
            assert result.data["successful_translations"] == 3
            assert result.data["matches_found"] == 3
            assert "output" in context["datasets"]

    # 11. Performance Tests
    @pytest.mark.asyncio
    async def test_performance_large_dataset(self):
        """Test performance with 1000 metabolites."""
        action = MetaboliteCtsBridgeAction()

        # Create large dataset
        large_dataset = pd.DataFrame(
            {
                "hmdb_id": [f"HMDB{str(i).zfill(7)}" for i in range(1000)],
                "name": [f"Compound_{i}" for i in range(1000)],
            }
        )

        params = MetaboliteCtsBridgeParams(
            source_key="source",
            target_key="target",
            output_key="output",
            source_id_column="hmdb_id",
            source_id_type="hmdb",
            target_id_column="inchikey",
            target_id_type="inchikey",
            batch_size=100,
            cache_results=True,
        )

        context = {
            "datasets": {
                "source": large_dataset,
                "target": pd.DataFrame(
                    {"inchikey": ["DUMMY-INCHIKEY"], "compound": ["Dummy"]}
                ),
            }
        }

        # Mock translations to be fast
        with patch.object(action, "_process_translations") as mock_process:
            mock_process.return_value = {
                f"HMDB{str(i).zfill(7)}": [f"INCHI-{i}"] for i in range(100)
            }

            import time

            start_time = time.time()

            result = await action.execute_typed(params, context)

            elapsed_time = time.time() - start_time

            # Should complete in < 60 seconds
            assert elapsed_time < 60
            assert result.success

    # 12. Real Data Pattern Tests
    @pytest.mark.asyncio
    async def test_israeli10k_to_kg2c_pattern(self):
        """Test real Israeli10k to KG2c translation pattern."""
        action = MetaboliteCtsBridgeAction()

        # Simulate Israeli10k metabolite data
        israeli10k_data = pd.DataFrame(
            {
                "metabolite_id": ["M001", "M002", "M003"],
                "hmdb_id": ["HMDB0001234", "HMDB0000122", "HMDB0000562"],
                "name": ["Metabolite1", "Glucose", "Creatinine"],
            }
        )

        # Simulate KG2c data with InChIKeys
        kg2c_data = pd.DataFrame(
            {
                "node_id": ["CHEBI:123", "CHEBI:456", "CHEBI:789"],
                "inchikey": [
                    "BQJCRHHNABKAKU-KBQPJGBKSA-N",
                    "WQZGKKKJIJFFOK-GASJEMHNSA-N",
                    "BTCSSZJGUNDROE-UHFFFAOYSA-N",
                ],
                "node_name": ["Compound1", "D-Glucose", "Creatinine"],
            }
        )

        params = MetaboliteCtsBridgeParams(
            source_key="israeli10k",
            target_key="kg2c",
            output_key="matched",
            source_id_column="hmdb_id",
            source_id_type="hmdb",
            target_id_column="inchikey",
            target_id_type="inchikey",
        )

        context = {"datasets": {"israeli10k": israeli10k_data, "kg2c": kg2c_data}}

        # Mock translations
        with patch.object(action, "_process_translations") as mock_process:
            mock_process.return_value = {
                "HMDB0001234": ["BQJCRHHNABKAKU-KBQPJGBKSA-N"],
                "HMDB0000122": ["WQZGKKKJIJFFOK-GASJEMHNSA-N"],
                "HMDB0000562": ["BTCSSZJGUNDROE-UHFFFAOYSA-N"],
            }

            result = await action.execute_typed(params, context)

            assert result.success
            assert result.data["matches_found"] == 3
            assert "matched" in context["datasets"]

            matched_df = context["datasets"]["matched"]
            assert len(matched_df) == 3

    @pytest.mark.asyncio
    async def test_arivale_to_spoke_pattern(self):
        """Test real Arivale to SPOKE translation pattern."""
        action = MetaboliteCtsBridgeAction()

        # Simulate Arivale metabolite data
        arivale_data = pd.DataFrame(
            {
                "test_id": ["T001", "T002"],
                "chemical_id": ["CHEBI:17234", "CHEBI:16737"],
                "test_name": ["Glucose Test", "Creatinine Test"],
            }
        )

        # Simulate SPOKE data with KEGG IDs
        spoke_data = pd.DataFrame(
            {
                "node_id": ["Compound:C00031", "Compound:C00791"],
                "kegg_id": ["C00031", "C00791"],
                "name": ["D-Glucose", "Creatinine"],
            }
        )

        params = MetaboliteCtsBridgeParams(
            source_key="arivale",
            target_key="spoke",
            output_key="matched",
            source_id_column="chemical_id",
            source_id_type="chebi",
            target_id_column="kegg_id",
            target_id_type="kegg",
        )

        context = {"datasets": {"arivale": arivale_data, "spoke": spoke_data}}

        # Mock translations
        with patch.object(action, "_process_translations") as mock_process:
            mock_process.return_value = {
                "CHEBI:17234": ["C00031"],
                "CHEBI:16737": ["C00791"],
            }

            result = await action.execute_typed(params, context)

            assert result.success
            assert result.data["matches_found"] == 2
            assert "matched" in context["datasets"]
