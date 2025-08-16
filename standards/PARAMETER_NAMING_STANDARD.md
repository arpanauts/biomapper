# Parameter Naming Standard for Biomapper

This document defines the authoritative parameter naming standards for the Biomapper codebase. All new actions MUST follow these standards, and existing actions will be migrated to comply.

## 1. Core Principles

- **Clarity**: Names must unambiguously convey the parameter's purpose
- **Consistency**: Use the same name for the same concept across all actions
- **Simplicity**: Use the simplest name that fully describes the parameter
- **Snake Case**: All parameters use lowercase with underscores (snake_case)
- **No Redundancy**: Avoid redundant suffixes like `_name` for string fields unless necessary

## 2. Standard Parameter Names

### Dataset Keys (Context References)

| Concept | Standard Name | Description | OLD Names to Replace |
|---------|--------------|-------------|---------------------|
| Primary input dataset | `input_key` | Key to retrieve dataset from context | `dataset_key`, `dataset1_key`, `input_context_key`, `source_dataset_key`, `input_dataset` |
| Primary output dataset | `output_key` | Key to store dataset in context | `output_context_key`, `result_key`, `output_dataset` |
| Source dataset (merge/join) | `source_key` | Source dataset in operations | `source_dataset`, `from_dataset`, `source_dataset_key` |
| Target dataset (merge/join) | `target_key` | Target dataset in operations | `target_dataset`, `to_dataset`, `target_dataset_key` |
| Second input dataset | `input_key_2` | Secondary input dataset | `dataset2_key`, `second_dataset_key` |
| Third input dataset | `input_key_3` | Tertiary input dataset | `dataset3_key`, `third_dataset_key` |

### File Paths

| Concept | Standard Name | Description | OLD Names to Replace |
|---------|--------------|-------------|---------------------|
| Input file path | `file_path` | Path to input file | `csv_path`, `tsv_path`, `filename`, `input_file`, `input_path`, `filepath` |
| Output file path | `output_path` | Path to output file | `output_file`, `output_filename`, `output_filepath`, `export_path` |
| Directory path | `directory_path` | Path to directory | `output_dir`, `dir_path`, `folder_path` |
| Config file path | `config_path` | Path to configuration file | `config_file`, `configuration_path` |

### Column Names

| Concept | Standard Name | Description | OLD Names to Replace |
|---------|--------------|-------------|---------------------|
| Identifier column | `identifier_column` | Column containing primary identifiers | `id_column`, `id_col`, `identifier_col` |
| Merge column | `merge_column` | Column to merge/join on | `join_column`, `merge_on`, `join_on` |
| Value column | `value_column` | Column containing values | `val_column`, `value_col` |
| Name column | `name_column` | Column containing names | `name_col`, `label_column` |
| Description column | `description_column` | Column containing descriptions | `desc_column`, `description_col` |

### Processing Parameters

| Concept | Standard Name | Description | OLD Names to Replace |
|---------|--------------|-------------|---------------------|
| Threshold value | `threshold` | Numeric threshold | `thresh`, `cutoff`, `min_threshold` |
| Maximum limit | `max_limit` | Maximum value/count | `maximum`, `max_value`, `limit` |
| Minimum limit | `min_limit` | Minimum value/count | `minimum`, `min_value` |
| Batch size | `batch_size` | Number of items per batch | `chunk_size`, `batch_count` |
| Timeout | `timeout_seconds` | Timeout in seconds | `timeout`, `max_timeout` |

### Boolean Flags

| Concept | Standard Name | Description | OLD Names to Replace |
|---------|--------------|-------------|---------------------|
| Case sensitive | `case_sensitive` | Whether to consider case | `ignore_case`, `case_insensitive` |
| Include header | `include_header` | Whether to include header | `has_header`, `with_header` |
| Overwrite existing | `overwrite` | Whether to overwrite existing | `force`, `replace_existing` |
| Verbose output | `verbose` | Enable detailed logging | `debug`, `detailed_output` |
| Strict mode | `strict` | Fail on warnings | `strict_mode`, `fail_on_warning` |

### API/Service Parameters  

| Concept | Standard Name | Description | OLD Names to Replace |
|---------|--------------|-------------|---------------------|
| API key | `api_key` | API authentication key | `apikey`, `auth_key` |
| API endpoint | `api_endpoint` | API URL endpoint | `endpoint`, `api_url`, `service_url` |
| Request timeout | `request_timeout` | API request timeout | `api_timeout`, `http_timeout` |
| Max retries | `max_retries` | Maximum retry attempts | `retry_count`, `retries` |

### Format/Type Parameters

| Concept | Standard Name | Description | OLD Names to Replace |
|---------|--------------|-------------|---------------------|
| File format | `file_format` | Format of file (csv, tsv, json) | `format`, `output_format`, `export_format` |
| Delimiter | `delimiter` | Field delimiter | `separator`, `field_separator` |
| Encoding | `encoding` | Text encoding | `file_encoding`, `text_encoding` |

## 3. Special Naming Rules

### Lists/Arrays
- Use plural form: `columns` not `column_list`
- Exception: When it's a single string with delimited values, use singular + `_list` suffix

### Optional Parameters
- Don't use `optional_` prefix
- Use type hints: `Optional[str]` in code
- Document optionality in descriptions

### Computed/Derived Values
- Use `_computed` suffix only if necessary to distinguish from input
- Example: `score` (input) vs `score_computed` (calculated)

## 4. Migration Examples

### Before (Non-standard):
```python
class MyActionParams(BaseModel):
    dataset_key: str  # WRONG
    output_file: str  # WRONG
    csv_path: str  # WRONG
    source_dataset: str  # WRONG
```

### After (Standard):
```python
class MyActionParams(BaseModel):
    input_key: str  # Standard input dataset key
    output_path: str  # Standard output file path
    file_path: str  # Standard input file path
    source_key: str  # Standard source dataset key
```

## 5. Validation Rules

All parameters MUST:
1. Use snake_case (lowercase with underscores)
2. Start with a letter
3. Not use reserved Python keywords
4. Be descriptive without being verbose
5. Follow the standard names in this document

## 6. Backward Compatibility

During migration:
1. Support both old and new parameter names temporarily
2. Log deprecation warnings for old names
3. Document migration in CHANGELOG
4. Remove old names after 2 version releases

## 7. Adding New Parameters

When adding parameters not in this standard:
1. Check if a similar concept exists
2. Follow the naming patterns established here
3. Update this document with the new standard
4. Get team review before implementing

## 8. Exceptions

The only acceptable exceptions are:
1. External API parameters that must match third-party specs
2. Database field names that must match schema
3. Legacy parameters with >100 usages (document reason)

## Version History

- v1.0.0 (2024-01): Initial standard definition
- Based on audit of 788 parameters across 46 action files
- Addresses 18 non-standard parameters found in audit

## Enforcement

- Pre-commit hooks will validate parameter names
- CI/CD will fail on non-standard parameters
- Quarterly audits will ensure compliance