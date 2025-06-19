# Task: Resolve Cache Component Errors

## Context:
Several tests for the caching components (`CachedMapper` and `CacheManager`) are failing with `TypeError`, `AssertionError`, and `AttributeError`. These errors point to issues in how cache statistics are handled, how mappings are added or retrieved, and assumptions about object states.

## Objective:
Debug and fix the errors in `CachedMapper` and `CacheManager` to ensure correct cache operation and statistics tracking.

## Affected Tests & Errors:

**`tests/cache/test_cached_mapper.py`**
- `CachedMapperTest::test_batch_map_mixed_hits` - `TypeError: unsupported operand type(s) for +=: 'NoneType' and 'int'`
- `CachedMapperTest::test_map_entity_cache_hit` - `TypeError: unsupported operand type(s) for +=: 'NoneType' and 'int'`
- `CachedMapperTest::test_map_entity_cache_miss` - `TypeError: unsupported operand type(s) for +=: 'NoneType' and 'int'`
- `CachedMapperTest::test_skip_cache` - `TypeError: unsupported operand type(s) for +=: 'NoneType' and 'int'`

**`tests/cache/test_manager.py`**
- `CacheManagerTest::test_add_mapping` - `AssertionError: 0 != 2`
- `CacheManagerTest::test_add_mapping_with_metadata` - `AttributeError: 'NoneType' object has no attribute 'id'`
- `CacheManagerTest::test_bidirectional_lookup` - `TypeError: unsupported operand type(s) for +=: 'NoneType' and 'int'`
- `CacheManagerTest::test_cache_stats` - `TypeError: unsupported operand type(s) for +=: 'NoneType' and 'int'`
- `CacheManagerTest::test_delete_expired_mappings` - `AssertionError: 1 != 0`
- `CacheManagerTest::test_lookup` - `TypeError: unsupported operand type(s) for +=: 'NoneType' and 'int'`

## Tasks:
1.  **Investigate `TypeError` in `CachedMapperTest`:** 
    *   Review how hit/miss counts or other numeric statistics are initialized and incremented in `CachedMapper`. Ensure variables are properly initialized to numeric types (e.g., 0) before arithmetic operations.
2.  **Investigate `AssertionError: 0 != 2` in `CacheManagerTest::test_add_mapping`:**
    *   Examine the logic for adding mappings in `CacheManager`. Determine why the expected number of mappings (or a related count) is not matching the actual count.
3.  **Investigate `AttributeError: 'NoneType' object has no attribute 'id'` in `CacheManagerTest::test_add_mapping_with_metadata`:**
    *   Check how metadata and associated objects (which might be expected to have an `id`) are handled during mapping creation. Ensure objects are correctly instantiated and populated before their attributes are accessed.
4.  **Investigate `TypeError` in `CacheManagerTest` (lookup, bidirectional_lookup, cache_stats):**
    *   Similar to `CachedMapperTest`, review how numeric statistics related to lookups and general cache stats are managed. Ensure proper initialization.
5.  **Investigate `AssertionError: 1 != 0` in `CacheManagerTest::test_delete_expired_mappings`:**
    *   Debug the logic for deleting expired mappings. Verify the conditions for expiration and the counting mechanism for deleted items.

## Expected Outcome:
All listed tests in `tests/cache/test_cached_mapper.py` and `tests/cache/test_manager.py` should pass, indicating that the caching components are functioning correctly.
