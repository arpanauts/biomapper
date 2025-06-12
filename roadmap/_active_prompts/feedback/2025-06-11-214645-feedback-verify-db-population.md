# Feedback: Database Population Verification

## Execution Logs

### `populate_metamapper_db.py` Output
```bash
2025-06-11 23:25:24,981 - INFO - Target database URL: sqlite+aiosqlite:////home/ubuntu/biomapper/data/metamapper.db
2025-06-11 23:25:24,981 - WARNING - Existing database found at /home/ubuntu/biomapper/data/metamapper.db. Deleting...
2025-06-11 23:25:24,982 - INFO - Existing database deleted successfully.
2025-06-11 23:25:24,982 - INFO - Initializing DatabaseManager...
2025-06-11 23:25:24,982 - INFO - Initializing default DatabaseManager.
2025-06-11 23:25:24,982 - INFO - Using provided cache database URL: sqlite+aiosqlite:////home/ubuntu/biomapper/data/metamapper.db
2025-06-11 23:25:24,995 - INFO - Using DatabaseManager instance: 131259700699856 with URL: sqlite+aiosqlite:////home/ubuntu/biomapper/data/metamapper.db
2025-06-11 23:25:24,995 - INFO - Initializing database schema...
2025-06-11 23:25:24,995 - INFO - Initializing database schema asynchronously (drop_all=True) using async_engine.
2025-06-11 23:25:25,003 INFO sqlalchemy.engine.Engine BEGIN (implicit)
2025-06-11 23:25:25,003 - INFO - BEGIN (implicit)
2025-06-11 23:25:25,003 - WARNING - Dropping all tables from the database via async_engine.
2025-06-11 23:25:25,003 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("entity_type_config")
2025-06-11 23:25:25,003 - INFO - PRAGMA main.table_info("entity_type_config")
2025-06-11 23:25:25,004 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,004 - INFO - [raw sql] ()
2025-06-11 23:25:25,005 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("entity_type_config")
2025-06-11 23:25:25,005 - INFO - PRAGMA temp.table_info("entity_type_config")
2025-06-11 23:25:25,005 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,005 - INFO - [raw sql] ()
2025-06-11 23:25:25,005 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("cache_stats")
2025-06-11 23:25:25,005 - INFO - PRAGMA main.table_info("cache_stats")
2025-06-11 23:25:25,005 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,005 - INFO - [raw sql] ()
2025-06-11 23:25:25,006 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("cache_stats")
2025-06-11 23:25:25,006 - INFO - PRAGMA temp.table_info("cache_stats")
2025-06-11 23:25:25,006 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,006 - INFO - [raw sql] ()
2025-06-11 23:25:25,007 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("transitive_job_log")
2025-06-11 23:25:25,007 - INFO - PRAGMA main.table_info("transitive_job_log")
2025-06-11 23:25:25,007 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,007 - INFO - [raw sql] ()
2025-06-11 23:25:25,007 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("transitive_job_log")
2025-06-11 23:25:25,007 - INFO - PRAGMA temp.table_info("transitive_job_log")
2025-06-11 23:25:25,007 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,007 - INFO - [raw sql] ()
2025-06-11 23:25:25,008 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("endpoints")
2025-06-11 23:25:25,008 - INFO - PRAGMA main.table_info("endpoints")
2025-06-11 23:25:25,008 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,008 - INFO - [raw sql] ()
2025-06-11 23:25:25,008 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("endpoints")
2025-06-11 23:25:25,008 - INFO - PRAGMA temp.table_info("endpoints")
2025-06-11 23:25:25,008 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,008 - INFO - [raw sql] ()
2025-06-11 23:25:25,009 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("mapping_resources")
2025-06-11 23:25:25,009 - INFO - PRAGMA main.table_info("mapping_resources")
2025-06-11 23:25:25,009 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,009 - INFO - [raw sql] ()
2025-06-11 23:25:25,010 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("mapping_resources")
2025-06-11 23:25:25,010 - INFO - PRAGMA temp.table_info("mapping_resources")
2025-06-11 23:25:25,010 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,010 - INFO - [raw sql] ()
2025-06-11 23:25:25,010 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("endpoint_relationships")
2025-06-11 23:25:25,010 - INFO - PRAGMA main.table_info("endpoint_relationships")
2025-06-11 23:25:25,010 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,010 - INFO - [raw sql] ()
2025-06-11 23:25:25,011 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("endpoint_relationships")
2025-06-11 23:25:25,011 - INFO - PRAGMA temp.table_info("endpoint_relationships")
2025-06-11 23:25:25,011 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,011 - INFO - [raw sql] ()
2025-06-11 23:25:25,011 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("endpoint_relationship_members")
2025-06-11 23:25:25,011 - INFO - PRAGMA main.table_info("endpoint_relationship_members")
2025-06-11 23:25:25,011 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,011 - INFO - [raw sql] ()
2025-06-11 23:25:25,012 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("endpoint_relationship_members")
2025-06-11 23:25:25,012 - INFO - PRAGMA temp.table_info("endpoint_relationship_members")
2025-06-11 23:25:25,012 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,012 - INFO - [raw sql] ()
2025-06-11 23:25:25,012 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("ontology_preferences")
2025-06-11 23:25:25,012 - INFO - PRAGMA main.table_info("ontology_preferences")
2025-06-11 23:25:25,012 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,012 - INFO - [raw sql] ()
2025-06-11 23:25:25,013 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("ontology_preferences")
2025-06-11 23:25:25,013 - INFO - PRAGMA temp.table_info("ontology_preferences")
2025-06-11 23:25:25,013 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,013 - INFO - [raw sql] ()
2025-06-11 23:25:25,013 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("mapping_paths")
2025-06-11 23:25:25,013 - INFO - PRAGMA main.table_info("mapping_paths")
2025-06-11 23:25:25,013 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,013 - INFO - [raw sql] ()
2025-06-11 23:25:25,014 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("mapping_paths")
2025-06-11 23:25:25,014 - INFO - PRAGMA temp.table_info("mapping_paths")
2025-06-11 23:25:25,014 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,014 - INFO - [raw sql] ()
2025-06-11 23:25:25,015 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("mapping_path_steps")
2025-06-11 23:25:25,015 - INFO - PRAGMA main.table_info("mapping_path_steps")
2025-06-11 23:25:25,015 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,015 - INFO - [raw sql] ()
2025-06-11 23:25:25,015 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("mapping_path_steps")
2025-06-11 23:25:25,015 - INFO - PRAGMA temp.table_info("mapping_path_steps")
2025-06-11 23:25:25,015 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,015 - INFO - [raw sql] ()
2025-06-11 23:25:25,016 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("property_extraction_configs")
2025-06-11 23:25:25,016 - INFO - PRAGMA main.table_info("property_extraction_configs")
2025-06-11 23:25:25,016 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,016 - INFO - [raw sql] ()
2025-06-11 23:25:25,016 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("property_extraction_configs")
2025-06-11 23:25:25,016 - INFO - PRAGMA temp.table_info("property_extraction_configs")
2025-06-11 23:25:25,016 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,016 - INFO - [raw sql] ()
2025-06-11 23:25:25,017 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("endpoint_property_configs")
2025-06-11 23:25:25,017 - INFO - PRAGMA main.table_info("endpoint_property_configs")
2025-06-11 23:25:25,017 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,017 - INFO - [raw sql] ()
2025-06-11 23:25:25,017 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("endpoint_property_configs")
2025-06-11 23:25:25,017 - INFO - PRAGMA temp.table_info("endpoint_property_configs")
2025-06-11 23:25:25,017 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,017 - INFO - [raw sql] ()
2025-06-11 23:25:25,018 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("ontology_coverage")
2025-06-11 23:25:25,018 - INFO - PRAGMA main.table_info("ontology_coverage")
2025-06-11 23:25:25,018 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,018 - INFO - [raw sql] ()
2025-06-11 23:25:25,018 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("ontology_coverage")
2025-06-11 23:25:25,018 - INFO - PRAGMA temp.table_info("ontology_coverage")
2025-06-11 23:25:25,019 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,019 - INFO - [raw sql] ()
2025-06-11 23:25:25,019 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("relationship_mapping_paths")
2025-06-11 23:25:25,019 - INFO - PRAGMA main.table_info("relationship_mapping_paths")
2025-06-11 23:25:25,019 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,019 - INFO - [raw sql] ()
2025-06-11 23:25:25,019 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("relationship_mapping_paths")
2025-06-11 23:25:25,019 - INFO - PRAGMA temp.table_info("relationship_mapping_paths")
2025-06-11 23:25:25,020 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,020 - INFO - [raw sql] ()
2025-06-11 23:25:25,020 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("composite_pattern_config")
2025-06-11 23:25:25,020 - INFO - PRAGMA main.table_info("composite_pattern_config")
2025-06-11 23:25:25,020 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,020 - INFO - [raw sql] ()
2025-06-11 23:25:25,021 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("composite_pattern_config")
2025-06-11 23:25:25,021 - INFO - PRAGMA temp.table_info("composite_pattern_config")
2025-06-11 23:25:25,021 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,021 - INFO - [raw sql] ()
2025-06-11 23:25:25,021 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("composite_processing_step")
2025-06-11 23:25:25,021 - INFO - PRAGMA main.table_info("composite_processing_step")
2025-06-11 23:25:25,021 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,021 - INFO - [raw sql] ()
2025-06-11 23:25:25,022 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("composite_processing_step")
2025-06-11 23:25:25,022 - INFO - PRAGMA temp.table_info("composite_processing_step")
2025-06-11 23:25:25,022 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,022 - INFO - [raw sql] ()
2025-06-11 23:25:25,022 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("ontologies")
2025-06-11 23:25:25,022 - INFO - PRAGMA main.table_info("ontologies")
2025-06-11 23:25:25,022 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,022 - INFO - [raw sql] ()
2025-06-11 23:25:25,023 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("ontologies")
2025-06-11 23:25:25,023 - INFO - PRAGMA temp.table_info("ontologies")
2025-06-11 23:25:25,023 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,023 - INFO - [raw sql] ()
2025-06-11 23:25:25,023 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("properties")
2025-06-11 23:25:25,023 - INFO - PRAGMA main.table_info("properties")
2025-06-11 23:25:25,023 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,023 - INFO - [raw sql] ()
2025-06-11 23:25:25,024 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("properties")
2025-06-11 23:25:25,024 - INFO - PRAGMA temp.table_info("properties")
2025-06-11 23:25:25,024 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,024 - INFO - [raw sql] ()
2025-06-11 23:25:25,024 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("mapping_session_logs")
2025-06-11 23:25:25,024 - INFO - PRAGMA main.table_info("mapping_session_logs")
2025-06-11 23:25:25,024 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,024 - INFO - [raw sql] ()
2025-06-11 23:25:25,025 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("mapping_session_logs")
2025-06-11 23:25:25,025 - INFO - PRAGMA temp.table_info("mapping_session_logs")
2025-06-11 23:25:25,025 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,025 - INFO - [raw sql] ()
2025-06-11 23:25:25,025 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("mapping_strategies")
2025-06-11 23:25:25,025 - INFO - PRAGMA main.table_info("mapping_strategies")
2025-06-11 23:25:25,025 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,025 - INFO - [raw sql] ()
2025-06-11 23:25:25,026 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("mapping_strategies")
2025-06-11 23:25:25,026 - INFO - PRAGMA temp.table_info("mapping_strategies")
2025-06-11 23:25:25,026 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,026 - INFO - [raw sql] ()
2025-06-11 23:25:25,027 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("mapping_strategy_steps")
2025-06-11 23:25:25,027 - INFO - PRAGMA main.table_info("mapping_strategy_steps")
2025-06-11 23:25:25,027 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,027 - INFO - [raw sql] ()
2025-06-11 23:25:25,027 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("mapping_strategy_steps")
2025-06-11 23:25:25,027 - INFO - PRAGMA temp.table_info("mapping_strategy_steps")
2025-06-11 23:25:25,027 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,027 - INFO - [raw sql] ()
2025-06-11 23:25:25,028 - INFO - Creating database tables via async_engine.
2025-06-11 23:25:25,028 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("entity_type_config")
2025-06-11 23:25:25,028 - INFO - PRAGMA main.table_info("entity_type_config")
2025-06-11 23:25:25,028 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,028 - INFO - [raw sql] ()
2025-06-11 23:25:25,029 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("entity_type_config")
2025-06-11 23:25:25,029 - INFO - PRAGMA temp.table_info("entity_type_config")
2025-06-11 23:25:25,029 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,029 - INFO - [raw sql] ()
2025-06-11 23:25:25,029 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("cache_stats")
2025-06-11 23:25:25,029 - INFO - PRAGMA main.table_info("cache_stats")
2025-06-11 23:25:25,029 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,029 - INFO - [raw sql] ()
2025-06-11 23:25:25,030 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("cache_stats")
2025-06-11 23:25:25,030 - INFO - PRAGMA temp.table_info("cache_stats")
2025-06-11 23:25:25,030 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,030 - INFO - [raw sql] ()
2025-06-11 23:25:25,030 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("transitive_job_log")
2025-06-11 23:25:25,030 - INFO - PRAGMA main.table_info("transitive_job_log")
2025-06-11 23:25:25,030 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,030 - INFO - [raw sql] ()
2025-06-11 23:25:25,031 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("transitive_job_log")
2025-06-11 23:25:25,031 - INFO - PRAGMA temp.table_info("transitive_job_log")
2025-06-11 23:25:25,031 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,031 - INFO - [raw sql] ()
2025-06-11 23:25:25,031 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("endpoints")
2025-06-11 23:25:25,031 - INFO - PRAGMA main.table_info("endpoints")
2025-06-11 23:25:25,031 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,031 - INFO - [raw sql] ()
2025-06-11 23:25:25,032 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("endpoints")
2025-06-11 23:25:25,032 - INFO - PRAGMA temp.table_info("endpoints")
2025-06-11 23:25:25,032 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,032 - INFO - [raw sql] ()
2025-06-11 23:25:25,032 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("mapping_resources")
2025-06-11 23:25:25,032 - INFO - PRAGMA main.table_info("mapping_resources")
2025-06-11 23:25:25,032 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,032 - INFO - [raw sql] ()
2025-06-11 23:25:25,033 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("mapping_resources")
2025-06-11 23:25:25,033 - INFO - PRAGMA temp.table_info("mapping_resources")
2025-06-11 23:25:25,033 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,033 - INFO - [raw sql] ()
2025-06-11 23:25:25,033 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("endpoint_relationships")
2025-06-11 23:25:25,033 - INFO - PRAGMA main.table_info("endpoint_relationships")
2025-06-11 23:25:25,033 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,033 - INFO - [raw sql] ()
2025-06-11 23:25:25,034 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("endpoint_relationships")
2025-06-11 23:25:25,034 - INFO - PRAGMA temp.table_info("endpoint_relationships")
2025-06-11 23:25:25,034 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,034 - INFO - [raw sql] ()
2025-06-11 23:25:25,034 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("endpoint_relationship_members")
2025-06-11 23:25:25,034 - INFO - PRAGMA main.table_info("endpoint_relationship_members")
2025-06-11 23:25:25,034 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,034 - INFO - [raw sql] ()
2025-06-11 23:25:25,035 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("endpoint_relationship_members")
2025-06-11 23:25:25,035 - INFO - PRAGMA temp.table_info("endpoint_relationship_members")
2025-06-11 23:25:25,035 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,035 - INFO - [raw sql] ()
2025-06-11 23:25:25,035 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("ontology_preferences")
2025-06-11 23:25:25,035 - INFO - PRAGMA main.table_info("ontology_preferences")
2025-06-11 23:25:25,036 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,036 - INFO - [raw sql] ()
2025-06-11 23:25:25,036 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("ontology_preferences")
2025-06-11 23:25:25,036 - INFO - PRAGMA temp.table_info("ontology_preferences")
2025-06-11 23:25:25,036 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,036 - INFO - [raw sql] ()
2025-06-11 23:25:25,036 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("mapping_paths")
2025-06-11 23:25:25,036 - INFO - PRAGMA main.table_info("mapping_paths")
2025-06-11 23:25:25,036 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,036 - INFO - [raw sql] ()
2025-06-11 23:25:25,037 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("mapping_paths")
2025-06-11 23:25:25,037 - INFO - PRAGMA temp.table_info("mapping_paths")
2025-06-11 23:25:25,037 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,037 - INFO - [raw sql] ()
2025-06-11 23:25:25,037 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("mapping_path_steps")
2025-06-11 23:25:25,037 - INFO - PRAGMA main.table_info("mapping_path_steps")
2025-06-11 23:25:25,037 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,037 - INFO - [raw sql] ()
2025-06-11 23:25:25,038 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("mapping_path_steps")
2025-06-11 23:25:25,038 - INFO - PRAGMA temp.table_info("mapping_path_steps")
2025-06-11 23:25:25,038 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,038 - INFO - [raw sql] ()
2025-06-11 23:25:25,039 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("property_extraction_configs")
2025-06-11 23:25:25,039 - INFO - PRAGMA main.table_info("property_extraction_configs")
2025-06-11 23:25:25,039 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,039 - INFO - [raw sql] ()
2025-06-11 23:25:25,039 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("property_extraction_configs")
2025-06-11 23:25:25,039 - INFO - PRAGMA temp.table_info("property_extraction_configs")
2025-06-11 23:25:25,039 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,039 - INFO - [raw sql] ()
2025-06-11 23:25:25,040 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("endpoint_property_configs")
2025-06-11 23:25:25,040 - INFO - PRAGMA main.table_info("endpoint_property_configs")
2025-06-11 23:25:25,040 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,040 - INFO - [raw sql] ()
2025-06-11 23:25:25,040 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("endpoint_property_configs")
2025-06-11 23:25:25,040 - INFO - PRAGMA temp.table_info("endpoint_property_configs")
2025-06-11 23:25:25,040 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,040 - INFO - [raw sql] ()
2025-06-11 23:25:25,041 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("ontology_coverage")
2025-06-11 23:25:25,041 - INFO - PRAGMA main.table_info("ontology_coverage")
2025-06-11 23:25:25,041 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,041 - INFO - [raw sql] ()
2025-06-11 23:25:25,041 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("ontology_coverage")
2025-06-11 23:25:25,041 - INFO - PRAGMA temp.table_info("ontology_coverage")
2025-06-11 23:25:25,041 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,041 - INFO - [raw sql] ()
2025-06-11 23:25:25,042 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("relationship_mapping_paths")
2025-06-11 23:25:25,042 - INFO - PRAGMA main.table_info("relationship_mapping_paths")
2025-06-11 23:25:25,042 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,042 - INFO - [raw sql] ()
2025-06-11 23:25:25,042 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("relationship_mapping_paths")
2025-06-11 23:25:25,042 - INFO - PRAGMA temp.table_info("relationship_mapping_paths")
2025-06-11 23:25:25,042 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,042 - INFO - [raw sql] ()
2025-06-11 23:25:25,043 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("composite_pattern_config")
2025-06-11 23:25:25,043 - INFO - PRAGMA main.table_info("composite_pattern_config")
2025-06-11 23:25:25,043 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,043 - INFO - [raw sql] ()
2025-06-11 23:25:25,043 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("composite_pattern_config")
2025-06-11 23:25:25,043 - INFO - PRAGMA temp.table_info("composite_pattern_config")
2025-06-11 23:25:25,044 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,044 - INFO - [raw sql] ()
2025-06-11 23:25:25,044 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("composite_processing_step")
2025-06-11 23:25:25,044 - INFO - PRAGMA main.table_info("composite_processing_step")
2025-06-11 23:25:25,044 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,044 - INFO - [raw sql] ()
2025-06-11 23:25:25,045 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("composite_processing_step")
2025-06-11 23:25:25,045 - INFO - PRAGMA temp.table_info("composite_processing_step")
2025-06-11 23:25:25,045 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,045 - INFO - [raw sql] ()
2025-06-11 23:25:25,046 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("ontologies")
2025-06-11 23:25:25,046 - INFO - PRAGMA main.table_info("ontologies")
2025-06-11 23:25:25,046 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,046 - INFO - [raw sql] ()
2025-06-11 23:25:25,046 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("ontologies")
2025-06-11 23:25:25,046 - INFO - PRAGMA temp.table_info("ontologies")
2025-06-11 23:25:25,046 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,046 - INFO - [raw sql] ()
2025-06-11 23:25:25,047 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("properties")
2025-06-11 23:25:25,047 - INFO - PRAGMA main.table_info("properties")
2025-06-11 23:25:25,047 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,047 - INFO - [raw sql] ()
2025-06-11 23:25:25,047 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("properties")
2025-06-11 23:25:25,047 - INFO - PRAGMA temp.table_info("properties")
2025-06-11 23:25:25,047 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,047 - INFO - [raw sql] ()
2025-06-11 23:25:25,048 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("mapping_session_logs")
2025-06-11 23:25:25,048 - INFO - PRAGMA main.table_info("mapping_session_logs")
2025-06-11 23:25:25,048 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,048 - INFO - [raw sql] ()
2025-06-11 23:25:25,048 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("mapping_session_logs")
2025-06-11 23:25:25,048 - INFO - PRAGMA temp.table_info("mapping_session_logs")
2025-06-11 23:25:25,048 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,048 - INFO - [raw sql] ()
2025-06-11 23:25:25,049 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("mapping_strategies")
2025-06-11 23:25:25,049 - INFO - PRAGMA main.table_info("mapping_strategies")
2025-06-11 23:25:25,049 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,049 - INFO - [raw sql] ()
2025-06-11 23:25:25,049 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("mapping_strategies")
2025-06-11 23:25:25,049 - INFO - PRAGMA temp.table_info("mapping_strategies")
2025-06-11 23:25:25,049 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,049 - INFO - [raw sql] ()
2025-06-11 23:25:25,050 INFO sqlalchemy.engine.Engine PRAGMA main.table_info("mapping_strategy_steps")
2025-06-11 23:25:25,050 - INFO - PRAGMA main.table_info("mapping_strategy_steps")
2025-06-11 23:25:25,050 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,050 - INFO - [raw sql] ()
2025-06-11 23:25:25,051 INFO sqlalchemy.engine.Engine PRAGMA temp.table_info("mapping_strategy_steps")
2025-06-11 23:25:25,051 - INFO - PRAGMA temp.table_info("mapping_strategy_steps")
2025-06-11 23:25:25,051 INFO sqlalchemy.engine.Engine [raw sql] ()
2025-06-11 23:25:25,051 - INFO - [raw sql] ()
2025-06-11 23:25:25,052 INFO sqlalchemy.engine.Engine 
CREATE TABLE entity_type_config (
	source_type VARCHAR NOT NULL, 
	target_type VARCHAR NOT NULL, 
	ttl_days INTEGER, 
	confidence_threshold FLOAT, 
	PRIMARY KEY (source_type, target_type)
)


2025-06-11 23:25:25,052 - INFO - 
CREATE TABLE entity_type_config (
	source_type VARCHAR NOT NULL, 
	target_type VARCHAR NOT NULL, 
	ttl_days INTEGER, 
	confidence_threshold FLOAT, 
	PRIMARY KEY (source_type, target_type)
)


2025-06-11 23:25:25,052 INFO sqlalchemy.engine.Engine [no key 0.00014s] ()
2025-06-11 23:25:25,052 - INFO - [no key 0.00014s] ()
2025-06-11 23:25:25,055 INFO sqlalchemy.engine.Engine 
CREATE TABLE cache_stats (
	stats_date DATETIME NOT NULL, 
	hits INTEGER, 
	misses INTEGER, 
	direct_lookups INTEGER, 
	derived_lookups INTEGER, 
	api_calls INTEGER, 
	transitive_derivations INTEGER, 
	PRIMARY KEY (stats_date)
)


2025-06-11 23:25:25,055 - INFO - 
CREATE TABLE cache_stats (
	stats_date DATETIME NOT NULL, 
	hits INTEGER, 
	misses INTEGER, 
	direct_lookups INTEGER, 
	derived_lookups INTEGER, 
	api_calls INTEGER, 
	transitive_derivations INTEGER, 
	PRIMARY KEY (stats_date)
)


2025-06-11 23:25:25,055 INFO sqlalchemy.engine.Engine [no key 0.00012s] ()
2025-06-11 23:25:25,055 - INFO - [no key 0.00012s] ()
2025-06-11 23:25:25,056 INFO sqlalchemy.engine.Engine 
CREATE TABLE transitive_job_log (
	id INTEGER NOT NULL, 
	job_date DATETIME, 
	mappings_processed INTEGER, 
	new_mappings_created INTEGER, 
	duration_seconds FLOAT, 
	status VARCHAR, 
	PRIMARY KEY (id)
)


2025-06-11 23:25:25,056 - INFO - 
CREATE TABLE transitive_job_log (
	id INTEGER NOT NULL, 
	job_date DATETIME, 
	mappings_processed INTEGER, 
	new_mappings_created INTEGER, 
	duration_seconds FLOAT, 
	status VARCHAR, 
	PRIMARY KEY (id)
)


2025-06-11 23:25:25,056 INFO sqlalchemy.engine.Engine [no key 0.00012s] ()
2025-06-11 23:25:25,056 - INFO - [no key 0.00012s] ()
2025-06-11 23:25:25,057 INFO sqlalchemy.engine.Engine 
CREATE TABLE endpoints (
	id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	description TEXT, 
	type VARCHAR, 
	primary_property_name VARCHAR, 
	connection_details TEXT, 
	PRIMARY KEY (id), 
	UNIQUE (name)
)


2025-06-11 23:25:25,057 - INFO - 
CREATE TABLE endpoints (
	id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	description TEXT, 
	type VARCHAR, 
	primary_property_name VARCHAR, 
	connection_details TEXT, 
	PRIMARY KEY (id), 
	UNIQUE (name)
)


2025-06-11 23:25:25,057 INFO sqlalchemy.engine.Engine [no key 0.00012s] ()
2025-06-11 23:25:25,057 - INFO - [no key 0.00012s] ()
2025-06-11 23:25:25,058 INFO sqlalchemy.engine.Engine 
CREATE TABLE mapping_resources (
	id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	description TEXT, 
	resource_type VARCHAR, 
	api_endpoint VARCHAR, 
	base_url VARCHAR, 
	config_template TEXT, 
	input_ontology_term VARCHAR, 
	output_ontology_term VARCHAR, 
	client_class_path VARCHAR, 
	PRIMARY KEY (id), 
	UNIQUE (name)
)


2025-06-11 23:25:25,058 - INFO - 
CREATE TABLE mapping_resources (
	id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	description TEXT, 
	resource_type VARCHAR, 
	api_endpoint VARCHAR, 
	base_url VARCHAR, 
	config_template TEXT, 
	input_ontology_term VARCHAR, 
	output_ontology_term VARCHAR, 
	client_class_path VARCHAR, 
	PRIMARY KEY (id), 
	UNIQUE (name)
)


2025-06-11 23:25:25,058 INFO sqlalchemy.engine.Engine [no key 0.00012s] ()
2025-06-11 23:25:25,058 - INFO - [no key 0.00012s] ()
2025-06-11 23:25:25,059 INFO sqlalchemy.engine.Engine 
CREATE TABLE composite_pattern_config (
	id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	description VARCHAR, 
	ontology_type VARCHAR NOT NULL, 
	pattern VARCHAR NOT NULL, 
	delimiters VARCHAR NOT NULL, 
	mapping_strategy VARCHAR NOT NULL, 
	keep_component_type BOOLEAN NOT NULL, 
	component_ontology_type VARCHAR, 
	priority INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
)


2025-06-11 23:25:25,059 - INFO - 
CREATE TABLE composite_pattern_config (
	id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	description VARCHAR, 
	ontology_type VARCHAR NOT NULL, 
	pattern VARCHAR NOT NULL, 
	delimiters VARCHAR NOT NULL, 
	mapping_strategy VARCHAR NOT NULL, 
	keep_component_type BOOLEAN NOT NULL, 
	component_ontology_type VARCHAR, 
	priority INTEGER NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name)
)


2025-06-11 23:25:25,059 INFO sqlalchemy.engine.Engine [no key 0.00014s] ()
2025-06-11 23:25:25,059 - INFO - [no key 0.00014s] ()
2025-06-11 23:25:25,061 INFO sqlalchemy.engine.Engine 
CREATE TABLE ontologies (
	id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	prefix VARCHAR, 
	uri VARCHAR, 
	description TEXT, 
	source_db VARCHAR, 
	version VARCHAR, 
	PRIMARY KEY (id), 
	UNIQUE (name), 
	UNIQUE (prefix)
)


2025-06-11 23:25:25,061 - INFO - 
CREATE TABLE ontologies (
	id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	prefix VARCHAR, 
	uri VARCHAR, 
	description TEXT, 
	source_db VARCHAR, 
	version VARCHAR, 
	PRIMARY KEY (id), 
	UNIQUE (name), 
	UNIQUE (prefix)
)


2025-06-11 23:25:25,061 INFO sqlalchemy.engine.Engine [no key 0.00012s] ()
2025-06-11 23:25:25,061 - INFO - [no key 0.00012s] ()
2025-06-11 23:25:25,062 INFO sqlalchemy.engine.Engine 
CREATE TABLE properties (
	id INTEGER NOT NULL, 
	key VARCHAR NOT NULL, 
	description TEXT, 
	predicate_uri VARCHAR, 
	PRIMARY KEY (id), 
	UNIQUE (key)
)


2025-06-11 23:25:25,062 - INFO - 
CREATE TABLE properties (
	id INTEGER NOT NULL, 
	key VARCHAR NOT NULL, 
	description TEXT, 
	predicate_uri VARCHAR, 
	PRIMARY KEY (id), 
	UNIQUE (key)
)


2025-06-11 23:25:25,062 INFO sqlalchemy.engine.Engine [no key 0.00013s] ()
2025-06-11 23:25:25,062 - INFO - [no key 0.00013s] ()
2025-06-11 23:25:25,063 INFO sqlalchemy.engine.Engine 
CREATE TABLE mapping_strategies (
	id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	description TEXT, 
	source_endpoint_id INTEGER, 
	target_endpoint_id INTEGER, 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (name), 
	FOREIGN KEY(source_endpoint_id) REFERENCES endpoints (id), 
	FOREIGN KEY(target_endpoint_id) REFERENCES endpoints (id)
)


2025-06-11 23:25:25,063 - INFO - 
CREATE TABLE mapping_strategies (
	id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	description TEXT, 
	source_endpoint_id INTEGER, 
	target_endpoint_id INTEGER, 
	created_at DATETIME, 
	updated_at DATETIME, 
	PRIMARY KEY (id), 
	UNIQUE (name), 
	FOREIGN KEY(source_endpoint_id) REFERENCES endpoints (id), 
	FOREIGN KEY(target_endpoint_id) REFERENCES endpoints (id)
)


2025-06-11 23:25:25,063 INFO sqlalchemy.engine.Engine [no key 0.00014s] ()
2025-06-11 23:25:25,063 - INFO - [no key 0.00014s] ()
2025-06-11 23:25:25,064 INFO sqlalchemy.engine.Engine 
CREATE TABLE endpoint_relationships (
	id INTEGER NOT NULL, 
	relationship_type VARCHAR NOT NULL, 
	description TEXT, 
	PRIMARY KEY (id)
)


2025-06-11 23:25:25,064 - INFO - 
CREATE TABLE endpoint_relationships (
	id INTEGER NOT NULL, 
	relationship_type VARCHAR NOT NULL, 
	description TEXT, 
	PRIMARY KEY (id)
)


2025-06-11 23:25:25,064 INFO sqlalchemy.engine.Engine [no key 0.00012s] ()
2025-06-11 23:25:25,064 - INFO - [no key 0.00012s] ()
2025-06-11 23:25:25,065 INFO sqlalchemy.engine.Engine 
CREATE TABLE ontology_preferences (
	id INTEGER NOT NULL, 
	source_ontology_id INTEGER NOT NULL, 
	target_ontology_id INTEGER NOT NULL, 
	endpoint_id INTEGER NOT NULL, 
	preference_level INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(source_ontology_id) REFERENCES ontologies (id), 
	FOREIGN KEY(target_ontology_id) REFERENCES ontologies (id), 
	FOREIGN KEY(endpoint_id) REFERENCES endpoints (id)
)


2025-06-11 23:25:25,065 - INFO - 
CREATE TABLE ontology_preferences (
	id INTEGER NOT NULL, 
	source_ontology_id INTEGER NOT NULL, 
	target_ontology_id INTEGER NOT NULL, 
	endpoint_id INTEGER NOT NULL, 
	preference_level INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(source_ontology_id) REFERENCES ontologies (id), 
	FOREIGN KEY(target_ontology_id) REFERENCES ontologies (id), 
	FOREIGN KEY(endpoint_id) REFERENCES endpoints (id)
)


2025-06-11 23:25:25,065 INFO sqlalchemy.engine.Engine [no key 0.00014s] ()
2025-06-11 23:25:25,065 - INFO - [no key 0.00014s] ()
2025-06-11 23:25:25,066 INFO sqlalchemy.engine.Engine 
CREATE TABLE mapping_paths (
	id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	source_endpoint_id INTEGER NOT NULL, 
	target_endpoint_id INTEGER NOT NULL, 
	description TEXT, 
	priority INTEGER, 
	entity_type VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name, source_endpoint_id, target_endpoint_id, entity_type), 
	FOREIGN KEY(source_endpoint_id) REFERENCES endpoints (id), 
	FOREIGN KEY(target_endpoint_id) REFERENCES endpoints (id)
)


2025-06-11 23:25:25,066 - INFO - 
CREATE TABLE mapping_paths (
	id INTEGER NOT NULL, 
	name VARCHAR NOT NULL, 
	source_endpoint_id INTEGER NOT NULL, 
	target_endpoint_id INTEGER NOT NULL, 
	description TEXT, 
	priority INTEGER, 
	entity_type VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	UNIQUE (name, source_endpoint_id, target_endpoint_id, entity_type), 
	FOREIGN KEY(source_endpoint_id) REFERENCES endpoints (id), 
	FOREIGN KEY(target_endpoint_id) REFERENCES endpoints (id)
)


2025-06-11 23:25:25,066 INFO sqlalchemy.engine.Engine [no key 0.00016s] ()
2025-06-11 23:25:25,066 - INFO - [no key 0.00016s] ()
2025-06-11 23:25:25,068 INFO sqlalchemy.engine.Engine CREATE INDEX ix_mapping_paths_endpoints ON mapping_paths (source_endpoint_id, target_endpoint_id)
2025-06-11 23:25:25,068 - INFO - CREATE INDEX ix_mapping_paths_endpoints ON mapping_paths (source_endpoint_id, target_endpoint_id)
2025-06-11 23:25:25,068 INFO sqlalchemy.engine.Engine [no key 0.00012s] ()
2025-06-11 23:25:25,068 - INFO - [no key 0.00012s] ()
2025-06-11 23:25:25,069 INFO sqlalchemy.engine.Engine 
CREATE TABLE property_extraction_configs (
	id INTEGER NOT NULL, 
	property_id INTEGER NOT NULL, 
	endpoint_id INTEGER NOT NULL, 
	extraction_path VARCHAR NOT NULL, 
	extraction_type VARCHAR, 
	description TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(property_id) REFERENCES properties (id), 
	FOREIGN KEY(endpoint_id) REFERENCES endpoints (id)
)


2025-06-11 23:25:25,069 - INFO - 
CREATE TABLE property_extraction_configs (
	id INTEGER NOT NULL, 
	property_id INTEGER NOT NULL, 
	endpoint_id INTEGER NOT NULL, 
	extraction_path VARCHAR NOT NULL, 
	extraction_type VARCHAR, 
	description TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(property_id) REFERENCES properties (id), 
	FOREIGN KEY(endpoint_id) REFERENCES endpoints (id)
)


2025-06-11 23:25:25,069 INFO sqlalchemy.engine.Engine [no key 0.00014s] ()
2025-06-11 23:25:25,069 - INFO - [no key 0.00014s] ()
2025-06-11 23:25:25,070 INFO sqlalchemy.engine.Engine 
CREATE TABLE endpoint_property_configs (
	id INTEGER NOT NULL, 
	endpoint_id INTEGER NOT NULL, 
	property_id INTEGER NOT NULL, 
	is_primary BOOLEAN, 
	is_required BOOLEAN, 
	extraction_config TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(endpoint_id) REFERENCES endpoints (id), 
	FOREIGN KEY(property_id) REFERENCES properties (id)
)


2025-06-11 23:25:25,070 - INFO - 
CREATE TABLE endpoint_property_configs (
	id INTEGER NOT NULL, 
	endpoint_id INTEGER NOT NULL, 
	property_id INTEGER NOT NULL, 
	is_primary BOOLEAN, 
	is_required BOOLEAN, 
	extraction_config TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(endpoint_id) REFERENCES endpoints (id), 
	FOREIGN KEY(property_id) REFERENCES properties (id)
)


2025-06-11 23:25:25,070 INFO sqlalchemy.engine.Engine [no key 0.00013s] ()
2025-06-11 23:25:25,070 - INFO - [no key 0.00013s] ()
2025-06-11 23:25:25,071 INFO sqlalchemy.engine.Engine 
CREATE TABLE ontology_coverage (
	id INTEGER NOT NULL, 
	endpoint_id INTEGER NOT NULL, 
	ontology_id INTEGER NOT NULL, 
	coverage_type VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(endpoint_id) REFERENCES endpoints (id), 
	FOREIGN KEY(ontology_id) REFERENCES ontologies (id)
)


2025-06-11 23:25:25,071 - INFO - 
CREATE TABLE ontology_coverage (
	id INTEGER NOT NULL, 
	endpoint_id INTEGER NOT NULL, 
	ontology_id INTEGER NOT NULL, 
	coverage_type VARCHAR, 
	PRIMARY KEY (id), 
	FOREIGN KEY(endpoint_id) REFERENCES endpoints (id), 
	FOREIGN KEY(ontology_id) REFERENCES ontologies (id)
)


2025-06-11 23:25:25,071 INFO sqlalchemy.engine.Engine [no key 0.00013s] ()
2025-06-11 23:25:25,071 - INFO - [no key 0.00013s] ()
2025-06-11 23:25:25,072 INFO sqlalchemy.engine.Engine 
CREATE TABLE relationship_mapping_paths (
	id INTEGER NOT NULL, 
	from_endpoint_id INTEGER NOT NULL, 
	to_endpoint_id INTEGER NOT NULL, 
	through_property VARCHAR NOT NULL, 
	reverse_property VARCHAR, 
	mapping_path_id INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(from_endpoint_id) REFERENCES endpoints (id), 
	FOREIGN KEY(to_endpoint_id) REFERENCES endpoints (id), 
	FOREIGN KEY(mapping_path_id) REFERENCES mapping_paths (id)
)


2025-06-11 23:25:25,072 - INFO - 
CREATE TABLE relationship_mapping_paths (
	id INTEGER NOT NULL, 
	from_endpoint_id INTEGER NOT NULL, 
	to_endpoint_id INTEGER NOT NULL, 
	through_property VARCHAR NOT NULL, 
	reverse_property VARCHAR, 
	mapping_path_id INTEGER, 
	PRIMARY KEY (id), 
	FOREIGN KEY(from_endpoint_id) REFERENCES endpoints (id), 
	FOREIGN KEY(to_endpoint_id) REFERENCES endpoints (id), 
	FOREIGN KEY(mapping_path_id) REFERENCES mapping_paths (id)
)


2025-06-11 23:25:25,072 INFO sqlalchemy.engine.Engine [no key 0.00014s] ()
2025-06-11 23:25:25,072 - INFO - [no key 0.00014s] ()
2025-06-11 23:25:25,073 INFO sqlalchemy.engine.Engine 
CREATE TABLE composite_processing_step (
	id INTEGER NOT NULL, 
	composite_pattern_id INTEGER NOT NULL, 
	step_order INTEGER NOT NULL, 
	operation VARCHAR NOT NULL, 
	config TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(composite_pattern_id) REFERENCES composite_pattern_config (id)
)


2025-06-11 23:25:25,073 - INFO - 
CREATE TABLE composite_processing_step (
	id INTEGER NOT NULL, 
	composite_pattern_id INTEGER NOT NULL, 
	step_order INTEGER NOT NULL, 
	operation VARCHAR NOT NULL, 
	config TEXT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(composite_pattern_id) REFERENCES composite_pattern_config (id)
)


2025-06-11 23:25:25,073 INFO sqlalchemy.engine.Engine [no key 0.00013s] ()
2025-06-11 23:25:25,073 - INFO - [no key 0.00013s] ()
2025-06-11 23:25:25,075 INFO sqlalchemy.engine.Engine 
CREATE TABLE mapping_session_logs (
	session_id VARCHAR NOT NULL, 
	input_data TEXT NOT NULL, 
	endpoint_id INTEGER NOT NULL, 
	output_data TEXT, 
	status VARCHAR NOT NULL, 
	error_message TEXT, 
	api_calls_made INTEGER, 
	timestamp DATETIME NOT NULL, 
	PRIMARY KEY (session_id), 
	FOREIGN KEY(endpoint_id) REFERENCES endpoints (id)
)


2025-06-11 23:25:25,075 - INFO - 
CREATE TABLE mapping_session_logs (
	session_id VARCHAR NOT NULL, 
	input_data TEXT NOT NULL, 
	endpoint_id INTEGER NOT NULL, 
	output_data TEXT, 
	status VARCHAR NOT NULL, 
	error_message TEXT, 
	api_calls_made INTEGER, 
	timestamp DATETIME NOT NULL, 
	PRIMARY KEY (session_id), 
	FOREIGN KEY(endpoint_id) REFERENCES endpoints (id)
)


2025-06-11 23:25:25,075 INFO sqlalchemy.engine.Engine [no key 0.00013s] ()
2025-06-11 23:25:25,075 - INFO - [no key 0.00013s] ()
2025-06-11 23:25:25,076 INFO sqlalchemy.engine.Engine 
CREATE TABLE mapping_strategy_steps (
	id INTEGER NOT NULL, 
	strategy_id INTEGER NOT NULL, 
	step_order INTEGER NOT NULL, 
	action VARCHAR NOT NULL, 
	parameters TEXT, 
	is_required BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(strategy_id) REFERENCES mapping_strategies (id)
)


2025-06-11 23:25:25,076 - INFO - 
CREATE TABLE mapping_strategy_steps (
	id INTEGER NOT NULL, 
	strategy_id INTEGER NOT NULL, 
	step_order INTEGER NOT NULL, 
	action VARCHAR NOT NULL, 
	parameters TEXT, 
	is_required BOOLEAN NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(strategy_id) REFERENCES mapping_strategies (id)
)


2025-06-11 23:25:25,076 INFO sqlalchemy.engine.Engine [no key 0.00013s] ()
2025-06-11 23:25:25,076 - INFO - [no key 0.00013s] ()
2025-06-11 23:25:25,077 INFO sqlalchemy.engine.Engine CREATE INDEX ix_mapping_strategy_steps_strategy_id ON mapping_strategy_steps (strategy_id)
2025-06-11 23:25:25,077 - INFO - CREATE INDEX ix_mapping_strategy_steps_strategy_id ON mapping_strategy_steps (strategy_id)
2025-06-11 23:25:25,077 INFO sqlalchemy.engine.Engine [no key 0.00012s] ()
2025-06-11 23:25:25,077 - INFO - [no key 0.00012s] ()
2025-06-11 23:25:25,077 INFO sqlalchemy.engine.Engine 
CREATE TABLE endpoint_relationship_members (
	id INTEGER NOT NULL, 
	relationship_id INTEGER NOT NULL, 
	endpoint_id INTEGER NOT NULL, 
	role VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(relationship_id) REFERENCES endpoint_relationships (id), 
	FOREIGN KEY(endpoint_id) REFERENCES endpoints (id)
)


2025-06-11 23:25:25,077 - INFO - 
CREATE TABLE endpoint_relationship_members (
	id INTEGER NOT NULL, 
	relationship_id INTEGER NOT NULL, 
	endpoint_id INTEGER NOT NULL, 
	role VARCHAR NOT NULL, 
	PRIMARY KEY (id), 
	FOREIGN KEY(relationship_id) REFERENCES endpoint_relationships (id), 
	FOREIGN KEY(endpoint_id) REFERENCES endpoints (id)
)


2025-06-11 23:25:25,077 INFO sqlalchemy.engine.Engine [no key 0.00014s] ()
2025-06-11 23:25:25,077 - INFO - [no key 0.00014s] ()
2025-06-11 23:25:25,079 INFO sqlalchemy.engine.Engine 
CREATE TABLE mapping_path_steps (
	id INTEGER NOT NULL, 
	mapping_path_id INTEGER NOT NULL, 
	step_order INTEGER NOT NULL, 
	resource_id INTEGER NOT NULL, 
	transform_function VARCHAR, 
	confidence_score FLOAT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(mapping_path_id) REFERENCES mapping_paths (id), 
	FOREIGN KEY(resource_id) REFERENCES mapping_resources (id)
)


2025-06-11 23:25:25,079 - INFO - 
CREATE TABLE mapping_path_steps (
	id INTEGER NOT NULL, 
	mapping_path_id INTEGER NOT NULL, 
	step_order INTEGER NOT NULL, 
	resource_id INTEGER NOT NULL, 
	transform_function VARCHAR, 
	confidence_score FLOAT, 
	PRIMARY KEY (id), 
	FOREIGN KEY(mapping_path_id) REFERENCES mapping_paths (id), 
	FOREIGN KEY(resource_id) REFERENCES mapping_resources (id)
)


2025-06-11 23:25:25,079 INFO sqlalchemy.engine.Engine [no key 0.00014s] ()
2025-06-11 23:25:25,079 - INFO - [no key 0.00014s] ()
2025-06-11 23:25:25,080 INFO sqlalchemy.engine.Engine COMMIT
2025-06-11 23:25:25,080 - INFO - COMMIT
2025-06-11 23:25:25,081 - INFO - Database schema initialization completed.
2025-06-11 23:25:25,081 - INFO - Populating database from YAML configurations...
2025-06-11 23:25:25,081 - INFO - Successfully obtained async session: 125094894602480
2025-06-11 23:25:25,081 - INFO - Loading configuration files from: /home/ubuntu/biomapper/configs
2025-06-11 23:25:25,081 - INFO - Found configuration files: ['/home/ubuntu/biomapper/configs/protein_config.yaml', '/home/ubuntu/biomapper/configs/test_optional_steps_config.yaml']
2025-06-11 23:25:25,081 - INFO - Processing configuration: /home/ubuntu/biomapper/configs/protein_config.yaml
2025-06-11 23:25:25,090 - INFO - Configuration validation passed!
2025-06-11 23:25:25,091 - INFO - Starting populate_configuration for test_optional_steps_config.yaml
2025-06-11 23:25:25,095 INFO sqlalchemy.engine.Engine BEGIN (implicit)
2025-06-11 23:25:25,095 - INFO - BEGIN (implicit)
2025-06-11 23:25:25,095 INFO sqlalchemy.engine.Engine SELECT endpoints.id AS endpoints_id, endpoints.name AS endpoints_name, endpoints.description AS endpoints_description, endpoints.type AS endpoints_type, endpoints.primary_property_name AS endpoints_primary_property_name, endpoints.connection_details AS endpoints_connection_details 
FROM endpoints 
WHERE endpoints.name = ?
2025-06-11 23:25:25,095 - INFO - SELECT endpoints.id AS endpoints_id, endpoints.name AS endpoints_name, endpoints.description AS endpoints_description, endpoints.type AS endpoints_type, endpoints.primary_property_name AS endpoints_primary_property_name, endpoints.connection_details AS endpoints_connection_details 
FROM endpoints 
WHERE endpoints.name = ?
2025-06-11 23:25:25,095 INFO sqlalchemy.engine.Engine [generated in 0.00027s] ('test_endpoint',)
2025-06-11 23:25:25,095 - INFO - [generated in 0.00027s] ('test_endpoint',)
2025-06-11 23:25:25,096 - INFO - Created endpoint: test_endpoint
2025-06-11 23:25:25,096 INFO sqlalchemy.engine.Engine INSERT INTO endpoints (name, description, type, primary_property_name, connection_details) VALUES (?, ?, ?, ?, ?)
2025-06-11 23:25:25,096 - INFO - INSERT INTO endpoints (name, description, type, primary_property_name, connection_details) VALUES (?, ?, ?, ?, ?)
2025-06-11 23:25:25,096 INFO sqlalchemy.engine.Engine [generated in 0.00013s] ('test_endpoint', 'Test endpoint for YAML strategy validation', 'YAML_TEST', None, None)
2025-06-11 23:25:25,096 - INFO - [generated in 0.00013s] ('test_endpoint', 'Test endpoint for YAML strategy validation', 'YAML_TEST', None, None)
2025-06-11 23:25:25,097 INFO sqlalchemy.engine.Engine SELECT mapping_strategies.id AS mapping_strategies_id, mapping_strategies.name AS mapping_strategies_name, mapping_strategies.description AS mapping_strategies_description, mapping_strategies.source_endpoint_id AS mapping_strategies_source_endpoint_id, mapping_strategies.target_endpoint_id AS mapping_strategies_target_endpoint_id, mapping_strategies.created_at AS mapping_strategies_created_at, mapping_strategies.updated_at AS mapping_strategies_updated_at 
FROM mapping_strategies 
WHERE mapping_strategies.name = ?
2025-06-11 23:25:25,097 - INFO - SELECT mapping_strategies.id AS mapping_strategies_id, mapping_strategies.name AS mapping_strategies_name, mapping_strategies.description AS mapping_strategies_description, mapping_strategies.source_endpoint_id AS mapping_strategies_source_endpoint_id, mapping_strategies.target_endpoint_id AS mapping_strategies_target_endpoint_id, mapping_strategies.created_at AS mapping_strategies_created_at, mapping_strategies.updated_at AS mapping_strategies_updated_at 
FROM mapping_strategies 
WHERE mapping_strategies.name = ?
2025-06-11 23:25:25,097 INFO sqlalchemy.engine.Engine [generated in 0.00019s] ('TEST_STRATEGY_WITH_OPTIONAL_STEPS',)
2025-06-11 23:25:25,097 - INFO - [generated in 0.00019s] ('TEST_STRATEGY_WITH_OPTIONAL_STEPS',)
2025-06-11 23:25:25,098 - INFO - Creating mapping strategy: TEST_STRATEGY_WITH_OPTIONAL_STEPS
2025-06-11 23:25:25,098 INFO sqlalchemy.engine.Engine INSERT INTO mapping_strategies (name, description, source_endpoint_id, target_endpoint_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)
2025-06-11 23:25:25,098 - INFO - INSERT INTO mapping_strategies (name, description, source_endpoint_id, target_endpoint_id, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?)
2025-06-11 23:25:25,098 INFO sqlalchemy.engine.Engine [generated in 0.00015s] ('TEST_STRATEGY_WITH_OPTIONAL_STEPS', 'Test strategy to validate optional step execution', 1, 1, '2025-06-11 23:25:25.098238', '2025-06-11 23:25:25.098244')
2025-06-11 23:25:25,098 - INFO - [generated in 0.00015s] ('TEST_STRATEGY_WITH_OPTIONAL_STEPS', 'Test strategy to validate optional step execution', 1, 1, '2025-06-11 23:25:25.098238', '2025-06-11 23:25:25.098244')
2025-06-11 23:25:25,099 - INFO - Creating strategy step 1: execute_mapping_path
2025-06-11 23:25:25,099 INFO sqlalchemy.engine.Engine INSERT INTO mapping_strategy_steps (strategy_id, step_order, action, parameters, is_required) VALUES (?, ?, ?, ?, ?)
2025-06-11 23:25:25,099 - INFO - INSERT INTO mapping_strategy_steps (strategy_id, step_order, action, parameters, is_required) VALUES (?, ?, ?, ?, ?)
2025-06-11 23:25:25,099 INFO sqlalchemy.engine.Engine [generated in 0.00015s] (1, 1, 'execute_mapping_path', '{"path": "test_path", "direction": "forward"}', 1)
2025-06-11 23:25:25,099 - INFO - [generated in 0.00015s] (1, 1, 'execute_mapping_path', '{"path": "test_path", "direction": "forward"}', 1)
2025-06-11 23:25:25,100 - INFO - Creating strategy step 2: convert_identifiers_local
2025-06-11 23:25:25,100 INFO sqlalchemy.engine.Engine INSERT INTO mapping_strategy_steps (strategy_id, step_order, action, parameters, is_required) VALUES (?, ?, ?, ?, ?)
2025-06-11 23:25:25,100 - INFO - INSERT INTO mapping_strategy_steps (strategy_id, step_order, action, parameters, is_required) VALUES (?, ?, ?, ?, ?)
2025-06-11 23:25:25,100 INFO sqlalchemy.engine.Engine [cached since 0.0008536s ago] (1, 2, 'convert_identifiers_local', '{"pattern": "test_pattern"}', 0)
2025-06-11 23:25:25,100 - INFO - [cached since 0.0008536s ago] (1, 2, 'convert_identifiers_local', '{"pattern": "test_pattern"}', 0)
2025-06-11 23:25:25,100 - INFO - Creating strategy step 3: filter_by_target_presence
2025-06-11 23:25:25,100 INFO sqlalchemy.engine.Engine INSERT INTO mapping_strategy_steps (strategy_id, step_order, action, parameters, is_required) VALUES (?, ?, ?, ?, ?)
2025-06-11 23:25:25,100 - INFO - INSERT INTO mapping_strategy_steps (strategy_id, step_order, action, parameters, is_required) VALUES (?, ?, ?, ?, ?)
2025-06-11 23:25:25,100 INFO sqlalchemy.engine.Engine [cached since 0.001254s ago] (1, 3, 'filter_by_target_presence', '{"endpoint": "test_endpoint"}', 1)
2025-06-11 23:25:25,100 - INFO - [cached since 0.001254s ago] (1, 3, 'filter_by_target_presence', '{"endpoint": "test_endpoint"}', 1)
2025-06-11 23:25:25,101 INFO sqlalchemy.engine.Engine COMMIT
2025-06-11 23:25:25,101 - INFO - COMMIT
2025-06-11 23:25:25,101 - INFO - Processing configuration: /home/ubuntu/biomapper/configs/test_optional_steps_config.yaml
2025-06-11 23:25:25,102 - WARNING - Configuration validation has 2 warning(s) to review.
2025-06-11 23:25:25,103 - WARNING - Configuration validation warnings (non-critical):
2025-06-11 23:25:25,103 - WARNING - - Missing optional top-level key: 'mapping_paths'
2025-06-11 23:25:25,103 - WARNING - - Endpoint 'test_endpoint' already exists in the database, will update it.
2025-06-11 23:25:25,103 - INFO - Configuration validation passed!
2025-06-11 23:25:25,103 - INFO - Starting populate_configuration for protein_config.yaml
2025-06-11 23:25:25,103 INFO sqlalchemy.engine.Engine BEGIN (implicit)
2025-06-11 23:25:25,103 - INFO - BEGIN (implicit)
2025-06-11 23:25:25,103 INFO sqlalchemy.engine.Engine SELECT endpoints.id AS endpoints_id, endpoints.name AS endpoints_name, endpoints.description AS endpoints_description, endpoints.type AS endpoints_type, endpoints.primary_property_name AS endpoints_primary_property_name, endpoints.connection_details AS endpoints_connection_details 
FROM endpoints 
WHERE endpoints.name = ?
2025-06-11 23:25:25,103 - INFO - SELECT endpoints.id AS endpoints_id, endpoints.name AS endpoints_name, endpoints.description AS endpoints_description, endpoints.type AS endpoints_type, endpoints.primary_property_name AS endpoints_primary_property_name, endpoints.connection_details AS endpoints_connection_details 
FROM endpoints 
WHERE endpoints.name = ?
2025-06-11 23:25:25,103 INFO sqlalchemy.engine.Engine [cached since 0.008179s ago] ('test_endpoint',)
2025-06-11 23:25:25,103 - INFO - [cached since 0.008179s ago] ('test_endpoint',)
2025-06-11 23:25:25,104 - INFO - Updating existing endpoint: test_endpoint
2025-06-11 23:25:25,104 INFO sqlalchemy.engine.Engine UPDATE endpoints SET description=?, type=?, primary_property_name=?, connection_details=? WHERE endpoints.id = ?
2025-06-11 23:25:25,104 - INFO - UPDATE endpoints SET description=?, type=?, primary_property_name=?, connection_details=? WHERE endpoints.id = ?
2025-06-11 23:25:25,104 INFO sqlalchemy.engine.Engine [generated in 0.00013s] ('Test endpoint for YAML strategy validation', 'YAML_TEST', None, None, 1)
2025-06-11 23:25:25,104 - INFO - [generated in 0.00013s] ('Test endpoint for YAML strategy validation', 'YAML_TEST', None, None, 1)
2025-06-11 23:25:25,105 INFO sqlalchemy.engine.Engine SELECT mapping_strategies.id AS mapping_strategies_id, mapping_strategies.name AS mapping_strategies_name, mapping_strategies.description AS mapping_strategies_description, mapping_strategies.source_endpoint_id AS mapping_strategies_source_endpoint_id, mapping_strategies.target_endpoint_id AS mapping_strategies_target_endpoint_id, mapping_strategies.created_at AS mapping_strategies_created_at, mapping_strategies.updated_at AS mapping_strategies_updated_at 
FROM mapping_strategies 
WHERE mapping_strategies.name = ?
2025-06-11 23:25:25,105 - INFO - SELECT mapping_strategies.id AS mapping_strategies_id, mapping_strategies.name AS mapping_strategies_name, mapping_strategies.description AS mapping_strategies_description, mapping_strategies.source_endpoint_id AS mapping_strategies_source_endpoint_id, mapping_strategies.target_endpoint_id AS mapping_strategies_target_endpoint_id, mapping_strategies.created_at AS mapping_strategies_created_at, mapping_strategies.updated_at AS mapping_strategies_updated_at 
FROM mapping_strategies 
WHERE mapping_strategies.name = ?
2025-06-11 23:25:25,105 INFO sqlalchemy.engine.Engine [cached since 0.007849s ago] ('TEST_STRATEGY_WITH_OPTIONAL_STEPS',)
2025-06-11 23:25:25,105 - INFO - [cached since 0.007849s ago] ('TEST_STRATEGY_WITH_OPTIONAL_STEPS',)
2025-06-11 23:25:25,105 - INFO - Updating existing mapping strategy: TEST_STRATEGY_WITH_OPTIONAL_STEPS
2025-06-11 23:25:25,105 INFO sqlalchemy.engine.Engine UPDATE mapping_strategies SET description=?, source_endpoint_id=?, target_endpoint_id=?, updated_at=? WHERE mapping_strategies.id = ?
2025-06-11 23:25:25,105 - INFO - UPDATE mapping_strategies SET description=?, source_endpoint_id=?, target_endpoint_id=?, updated_at=? WHERE mapping_strategies.id = ?
2025-06-11 23:25:25,105 INFO sqlalchemy.engine.Engine [generated in 0.00014s] ('Test strategy to validate optional step execution', 1, 1, '2025-06-11 23:25:25.105774', 1)
2025-06-11 23:25:25,105 - INFO - [generated in 0.00014s] ('Test strategy to validate optional step execution', 1, 1, '2025-06-11 23:25:25.105774', 1)
2025-06-11 23:25:25,106 INFO sqlalchemy.engine.Engine SELECT mapping_strategy_steps.id AS mapping_strategy_steps_id, mapping_strategy_steps.strategy_id AS mapping_strategy_steps_strategy_id, mapping_strategy_steps.step_order AS mapping_strategy_steps_step_order, mapping_strategy_steps.action AS mapping_strategy_steps_action, mapping_strategy_steps.parameters AS mapping_strategy_steps_parameters, mapping_strategy_steps.is_required AS mapping_strategy_steps_is_required 
FROM mapping_strategy_steps 
WHERE mapping_strategy_steps.strategy_id = ?
2025-06-11 23:25:25,106 - INFO - SELECT mapping_strategy_steps.id AS mapping_strategy_steps_id, mapping_strategy_steps.strategy_id AS mapping_strategy_steps_strategy_id, mapping_strategy_steps.step_order AS mapping_strategy_steps_step_order, mapping_strategy_steps.action AS mapping_strategy_steps_action, mapping_strategy_steps.parameters AS mapping_strategy_steps_parameters, mapping_strategy_steps.is_required AS mapping_strategy_steps_is_required 
FROM mapping_strategy_steps 
WHERE mapping_strategy_steps.strategy_id = ?
2025-06-11 23:25:25,106 INFO sqlalchemy.engine.Engine [generated in 0.00017s] (1,)
2025-06-11 23:25:25,106 - INFO - [generated in 0.00017s] (1,)
2025-06-11 23:25:25,106 INFO sqlalchemy.engine.Engine DELETE FROM mapping_strategy_steps WHERE mapping_strategy_steps.id = ?
2025-06-11 23:25:25,106 - INFO - DELETE FROM mapping_strategy_steps WHERE mapping_strategy_steps.id = ?
2025-06-11 23:25:25,106 INFO sqlalchemy.engine.Engine [generated in 0.00011s] (1,)
2025-06-11 23:25:25,106 - INFO - [generated in 0.00011s] (1,)
2025-06-11 23:25:25,107 INFO sqlalchemy.engine.Engine DELETE FROM mapping_strategy_steps WHERE mapping_strategy_steps.id = ?
2025-06-11 23:25:25,107 - INFO - DELETE FROM mapping_strategy_steps WHERE mapping_strategy_steps.id = ?
2025-06-11 23:25:25,107 INFO sqlalchemy.engine.Engine [cached since 0.0006328s ago] (2,)
2025-06-11 23:25:25,107 - INFO - [cached since 0.0006328s ago] (2,)
2025-06-11 23:25:25,107 INFO sqlalchemy.engine.Engine DELETE FROM mapping_strategy_steps WHERE mapping_strategy_steps.id = ?
2025-06-11 23:25:25,107 - INFO - DELETE FROM mapping_strategy_steps WHERE mapping_strategy_steps.id = ?
2025-06-11 23:25:25,107 INFO sqlalchemy.engine.Engine [cached since 0.0009856s ago] (3,)
2025-06-11 23:25:25,107 - INFO - [cached since 0.0009856s ago] (3,)
2025-06-11 23:25:25,107 - INFO - Creating strategy step 1: execute_mapping_path
2025-06-11 23:25:25,107 INFO sqlalchemy.engine.Engine INSERT INTO mapping_strategy_steps (strategy_id, step_order, action, parameters, is_required) VALUES (?, ?, ?, ?, ?)
2025-06-11 23:25:25,107 - INFO - INSERT INTO mapping_strategy_steps (strategy_id, step_order, action, parameters, is_required) VALUES (?, ?, ?, ?, ?)
2025-06-11 23:25:25,107 INFO sqlalchemy.engine.Engine [cached since 0.008356s ago] (1, 1, 'execute_mapping_path', '{"path": "test_path", "direction": "forward"}', 1)
2025-06-11 23:25:25,107 - INFO - [cached since 0.008356s ago] (1, 1, 'execute_mapping_path', '{"path": "test_path", "direction": "forward"}', 1)
2025-06-11 23:25:25,108 - INFO - Creating strategy step 2: convert_identifiers_local
2025-06-11 23:25:25,108 INFO sqlalchemy.engine.Engine INSERT INTO mapping_strategy_steps (strategy_id, step_order, action, parameters, is_required) VALUES (?, ?, ?, ?, ?)
2025-06-11 23:25:25,108 - INFO - INSERT INTO mapping_strategy_steps (strategy_id, step_order, action, parameters, is_required) VALUES (?, ?, ?, ?, ?)
2025-06-11 23:25:25,108 INFO sqlalchemy.engine.Engine [cached since 0.008725s ago] (1, 2, 'convert_identifiers_local', '{"pattern": "test_pattern"}', 0)
2025-06-11 23:25:25,108 - INFO - [cached since 0.008725s ago] (1, 2, 'convert_identifiers_local', '{"pattern": "test_pattern"}', 0)
2025-06-11 23:25:25,108 - INFO - Creating strategy step 3: filter_by_target_presence
2025-06-11 23:25:25,108 INFO sqlalchemy.engine.Engine INSERT INTO mapping_strategy_steps (strategy_id, step_order, action, parameters, is_required) VALUES (?, ?, ?, ?, ?)
2025-06-11 23:25:25,108 - INFO - INSERT INTO mapping_strategy_steps (strategy_id, step_order, action, parameters, is_required) VALUES (?, ?, ?, ?, ?)
2025-06-11 23:25:25,108 INFO sqlalchemy.engine.Engine [cached since 0.009122s ago] (1, 3, 'filter_by_target_presence', '{"endpoint": "test_endpoint"}', 1)
2025-06-11 23:25:25,108 - INFO - [cached since 0.009122s ago] (1, 3, 'filter_by_target_presence', '{"endpoint": "test_endpoint"}', 1)
2025-06-11 23:25:25,109 INFO sqlalchemy.engine.Engine COMMIT
2025-06-11 23:25:25,109 - INFO - COMMIT
2025-06-11 23:25:25,110 - INFO - Successfully populated configurations: ['protein_config.yaml', 'test_optional_steps_config.yaml']
2025-06-11 23:25:25,110 - INFO - Database population complete!
```

### `sqlite3` Inspection Output
```bash
sqlite3 /home/ubuntu/biomapper/data/metamapper.db "SELECT name FROM mapping_strategies;" 2>&1
TEST_STRATEGY_WITH_OPTIONAL_STEPS

sqlite3 /home/ubuntu/biomapper/data/metamapper.db "SELECT name FROM endpoints;" 2>&1
test_endpoint
```

## Outcome Analysis

**Status:** PARTIAL_SUCCESS

**Summary:**
The database population script ran successfully after fixing the database path configuration issue. The script successfully created the database schema and populated it with data from the YAML configuration files. However, only test data was populated - the script found and processed `test_optional_steps_config.yaml` and `protein_config.yaml`, but these appear to be test configurations rather than the full project configuration. The database now contains one mapping strategy (`TEST_STRATEGY_WITH_OPTIONAL_STEPS`) and one endpoint (`test_endpoint`), which suggests the actual project YAML configurations may need to be created or located elsewhere.