# Configuration-Driven Normalization

## Overview

Configuration-Driven Normalization replaces hardcoded data transformation logic with declarative YAML rules. This approach enables dataset-specific normalization without code changes, supporting the diverse formats found in biological data sources.

## Architecture

### Normalization Engine

```python
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, validator
from enum import Enum
import re

class TransformationType(str, Enum):
    """Types of transformations available."""
    UPPERCASE = "uppercase"
    LOWERCASE = "lowercase"
    STRIP = "strip"
    REPLACE = "replace"
    REGEX_REPLACE = "regex_replace"
    SPLIT = "split"
    JOIN = "join"
    EXTRACT = "extract"
    MAP = "map"
    COALESCE = "coalesce"
    DEFAULT = "default"
    CAST = "cast"
    FORMAT = "format"
    VALIDATE = "validate"

class TransformationRule(BaseModel):
    """Single transformation rule."""
    type: TransformationType
    params: Dict[str, Any] = Field(default_factory=dict)
    condition: Optional[str] = None  # Python expression
    on_error: str = "skip"  # skip, default, raise
    
    @validator('params')
    def validate_params(cls, v, values):
        """Validate parameters match transformation type."""
        transform_type = values.get('type')
        
        # Define required parameters for each type
        required_params = {
            TransformationType.REPLACE: ["pattern", "replacement"],
            TransformationType.REGEX_REPLACE: ["pattern", "replacement"],
            TransformationType.SPLIT: ["separator"],
            TransformationType.JOIN: ["separator"],
            TransformationType.EXTRACT: ["pattern", "group"],
            TransformationType.MAP: ["mapping"],
            TransformationType.DEFAULT: ["value"],
            TransformationType.CAST: ["target_type"],
            TransformationType.FORMAT: ["template"],
            TransformationType.VALIDATE: ["pattern"]
        }
        
        if transform_type in required_params:
            for param in required_params[transform_type]:
                if param not in v:
                    raise ValueError(f"Missing required parameter '{param}' for {transform_type}")
        
        return v

class FieldNormalizationRule(BaseModel):
    """Normalization rules for a single field."""
    source_field: str
    target_field: Optional[str] = None  # Defaults to source_field
    transformations: List[TransformationRule]
    required: bool = False
    
    def __init__(self, **data):
        super().__init__(**data)
        if self.target_field is None:
            self.target_field = self.source_field

class NormalizationConfig(BaseModel):
    """Complete normalization configuration."""
    name: str
    version: str = "1.0"
    description: Optional[str] = None
    field_rules: List[FieldNormalizationRule]
    global_transformations: List[TransformationRule] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

class NormalizationEngine:
    """Engine for applying normalization rules."""
    
    def __init__(self, config: Union[NormalizationConfig, Dict[str, Any]]):
        if isinstance(config, dict):
            self.config = NormalizationConfig(**config)
        else:
            self.config = config
        
        # Compile regex patterns for performance
        self._compiled_patterns = {}
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile regex patterns."""
        for rule in self.config.field_rules:
            for transform in rule.transformations:
                if transform.type in [TransformationType.REGEX_REPLACE, 
                                    TransformationType.EXTRACT,
                                    TransformationType.VALIDATE]:
                    pattern = transform.params.get("pattern")
                    if pattern and pattern not in self._compiled_patterns:
                        self._compiled_patterns[pattern] = re.compile(pattern)
    
    async def normalize_record(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Normalize a single record."""
        normalized = {}
        
        # Apply field-specific rules
        for field_rule in self.config.field_rules:
            value = record.get(field_rule.source_field)
            
            if value is None and field_rule.required:
                raise ValueError(f"Required field '{field_rule.source_field}' is missing")
            
            if value is not None:
                # Apply transformations in sequence
                for transform in field_rule.transformations:
                    if transform.condition:
                        # Evaluate condition
                        if not self._evaluate_condition(transform.condition, value, record):
                            continue
                    
                    try:
                        value = await self._apply_transformation(value, transform)
                    except Exception as e:
                        if transform.on_error == "raise":
                            raise
                        elif transform.on_error == "default":
                            value = transform.params.get("default_value")
                        else:  # skip
                            continue
                
                normalized[field_rule.target_field] = value
        
        # Apply global transformations
        for transform in self.config.global_transformations:
            normalized = await self._apply_global_transformation(normalized, transform)
        
        return normalized
    
    async def _apply_transformation(self, value: Any, rule: TransformationRule) -> Any:
        """Apply a single transformation."""
        transform_map = {
            TransformationType.UPPERCASE: lambda v: v.upper() if isinstance(v, str) else v,
            TransformationType.LOWERCASE: lambda v: v.lower() if isinstance(v, str) else v,
            TransformationType.STRIP: lambda v: v.strip() if isinstance(v, str) else v,
            TransformationType.REPLACE: lambda v: v.replace(
                rule.params["pattern"], 
                rule.params["replacement"]
            ) if isinstance(v, str) else v,
            TransformationType.REGEX_REPLACE: self._regex_replace,
            TransformationType.SPLIT: lambda v: v.split(rule.params["separator"]) if isinstance(v, str) else v,
            TransformationType.JOIN: lambda v: rule.params["separator"].join(v) if isinstance(v, list) else v,
            TransformationType.EXTRACT: self._extract_pattern,
            TransformationType.MAP: lambda v: rule.params["mapping"].get(v, v),
            TransformationType.COALESCE: lambda v: v if v else rule.params.get("default"),
            TransformationType.DEFAULT: lambda v: v if v is not None else rule.params["value"],
            TransformationType.CAST: self._cast_value,
            TransformationType.FORMAT: lambda v: rule.params["template"].format(value=v),
            TransformationType.VALIDATE: self._validate_pattern
        }
        
        handler = transform_map.get(rule.type)
        if handler:
            if rule.type in [TransformationType.REGEX_REPLACE, 
                           TransformationType.EXTRACT,
                           TransformationType.VALIDATE,
                           TransformationType.CAST]:
                return handler(value, rule)
            else:
                return handler(value)
        
        return value
    
    def _regex_replace(self, value: str, rule: TransformationRule) -> str:
        """Apply regex replacement."""
        if not isinstance(value, str):
            return value
        
        pattern = self._compiled_patterns.get(rule.params["pattern"])
        if pattern:
            return pattern.sub(rule.params["replacement"], value)
        return value
    
    def _extract_pattern(self, value: str, rule: TransformationRule) -> Optional[str]:
        """Extract pattern from value."""
        if not isinstance(value, str):
            return None
        
        pattern = self._compiled_patterns.get(rule.params["pattern"])
        if pattern:
            match = pattern.search(value)
            if match:
                group = rule.params.get("group", 0)
                return match.group(group)
        return None
    
    def _validate_pattern(self, value: str, rule: TransformationRule) -> str:
        """Validate value against pattern."""
        if not isinstance(value, str):
            raise ValueError(f"Cannot validate non-string value: {value}")
        
        pattern = self._compiled_patterns.get(rule.params["pattern"])
        if pattern and not pattern.match(value):
            raise ValueError(f"Value '{value}' does not match pattern '{rule.params['pattern']}'")
        
        return value
    
    def _cast_value(self, value: Any, rule: TransformationRule) -> Any:
        """Cast value to target type."""
        target_type = rule.params["target_type"]
        
        type_map = {
            "int": int,
            "float": float,
            "str": str,
            "bool": bool,
            "list": list,
            "dict": dict
        }
        
        if target_type in type_map:
            try:
                return type_map[target_type](value)
            except (ValueError, TypeError):
                if rule.on_error == "raise":
                    raise
                return value
        
        return value
    
    def _evaluate_condition(self, condition: str, value: Any, record: Dict[str, Any]) -> bool:
        """Safely evaluate condition."""
        # Create safe context
        context = {
            "value": value,
            "record": record,
            "len": len,
            "str": str,
            "int": int,
            "float": float,
            "bool": bool
        }
        
        try:
            return eval(condition, {"__builtins__": {}}, context)
        except Exception:
            return False
    
    async def _apply_global_transformation(
        self, 
        record: Dict[str, Any], 
        transform: TransformationRule
    ) -> Dict[str, Any]:
        """Apply transformation to entire record."""
        # Global transformations can modify the entire record
        # Implementation depends on specific requirements
        return record
```

## Configuration Examples

### Basic Normalization Config

```yaml
name: "clinical_lab_normalization"
version: "1.0"
description: "Normalization rules for clinical laboratory data"

field_rules:
  - source_field: "test_code"
    target_field: "loinc_code"
    transformations:
      - type: "strip"
      - type: "uppercase"
      - type: "validate"
        params:
          pattern: "^\\d{1,5}-\\d$"
        on_error: "raise"

  - source_field: "test_name"
    target_field: "display_name"
    transformations:
      - type: "strip"
      - type: "regex_replace"
        params:
          pattern: "\\s+"
          replacement: " "
      - type: "extract"
        params:
          pattern: "^([^:]+):"
          group: 1
        condition: "':' in value"

  - source_field: "result_value"
    target_field: "normalized_value"
    transformations:
      - type: "strip"
      - type: "replace"
        params:
          pattern: "<"
          replacement: ""
        condition: "value.startswith('<')"
      - type: "cast"
        params:
          target_type: "float"
        on_error: "skip"

  - source_field: "units"
    transformations:
      - type: "lowercase"
      - type: "map"
        params:
          mapping:
            "mg/dl": "mg/dL"
            "ug/ml": "μg/mL"
            "mmol/l": "mmol/L"
```

### Complex Multi-Value Normalization

```yaml
name: "chemical_identifier_normalization"
version: "1.0"

field_rules:
  - source_field: "cas_numbers"
    transformations:
      # Handle multi-value CAS numbers
      - type: "split"
        params:
          separator: ";"
        condition: "';' in value"
      
      # Validate each CAS number
      - type: "validate"
        params:
          pattern: "^\\d{2,7}-\\d{2}-\\d$"
        on_error: "skip"

  - source_field: "synonyms"
    transformations:
      # Split by multiple possible separators
      - type: "regex_replace"
        params:
          pattern: "[|;]"
          replacement: ","
      
      - type: "split"
        params:
          separator: ","
      
      # Clean each synonym
      - type: "strip"
        condition: "isinstance(value, list)"

  - source_field: "cross_references"
    target_field: "xrefs"
    transformations:
      # Extract database:id pairs
      - type: "extract"
        params:
          pattern: "([A-Z][A-Z0-9_.]+):([A-Za-z0-9_.-]+)"
          group: 0
      
      # Group by database
      - type: "map"
        params:
          mapping: "custom_function:group_xrefs"
```

### Entity-Specific Normalization

```yaml
name: "protein_data_normalization"
version: "1.0"

metadata:
  entity_type: "protein"
  source_format: "uniprot"

field_rules:
  - source_field: "accession"
    target_field: "uniprot_id"
    required: true
    transformations:
      - type: "strip"
      - type: "validate"
        params:
          pattern: "^[OPQ][0-9][A-Z0-9]{3}[0-9]|[A-NR-Z][0-9]([A-Z][A-Z0-9]{2}[0-9]){1,2}$"
        on_error: "raise"

  - source_field: "protein_names"
    target_field: "names"
    transformations:
      # Extract primary name
      - type: "extract"
        params:
          pattern: "^([^(]+)"
          group: 1
      
      # Clean formatting
      - type: "strip"
      - type: "regex_replace"
        params:
          pattern: "\\s{2,}"
          replacement: " "

  - source_field: "gene_names"
    transformations:
      # Parse gene name format: "Name=APOE; Synonyms=AD2, APO-E"
      - type: "extract"
        params:
          pattern: "Name=([^;]+)"
          group: 1
      - type: "strip"

global_transformations:
  # Add metadata to all records
  - type: "default"
    params:
      fields:
        source: "uniprot"
        normalized_at: "current_timestamp()"
```

## Integration with Actions

```python
@register_action("NORMALIZE_BIOLOGICAL_DATA")
class NormalizeBiologicalDataAction(TypedStrategyAction[NormalizeParams, NormalizeResult]):
    
    async def execute_typed(
        self,
        params: NormalizeParams,
        context: StrategyExecutionContext
    ) -> NormalizeResult:
        """Normalize biological data using configuration."""
        
        # Load normalization config
        if params.config_path:
            with open(params.config_path, 'r') as f:
                config_data = yaml.safe_load(f)
        else:
            config_data = params.inline_config
        
        engine = NormalizationEngine(config_data)
        
        # Process data
        normalized_records = []
        errors = []
        
        async for record in self._stream_input_data(params, context):
            try:
                normalized = await engine.normalize_record(record)
                normalized_records.append(normalized)
            except Exception as e:
                errors.append({
                    "record": record,
                    "error": str(e)
                })
        
        return NormalizeResult(
            total_processed=len(normalized_records),
            total_errors=len(errors),
            normalized_data=normalized_records,
            errors=errors if params.include_errors else None
        )
```

## Advanced Features

### Custom Functions

```python
class CustomFunctionRegistry:
    """Registry for custom transformation functions."""
    
    def __init__(self):
        self._functions = {}
        self._register_defaults()
    
    def _register_defaults(self):
        """Register default custom functions."""
        
        @self.register("group_xrefs")
        def group_xrefs(xref_list: List[str]) -> Dict[str, List[str]]:
            """Group cross-references by database."""
            grouped = {}
            for xref in xref_list:
                if ':' in xref:
                    db, identifier = xref.split(':', 1)
                    if db not in grouped:
                        grouped[db] = []
                    grouped[db].append(identifier)
            return grouped
        
        @self.register("parse_loinc_components")
        def parse_loinc_components(loinc_name: str) -> Dict[str, str]:
            """Parse LOINC name components."""
            parts = loinc_name.split(':')
            return {
                "component": parts[0] if len(parts) > 0 else None,
                "property": parts[1] if len(parts) > 1 else None,
                "time": parts[2] if len(parts) > 2 else None,
                "system": parts[3] if len(parts) > 3 else None,
                "scale": parts[4] if len(parts) > 4 else None,
                "method": parts[5] if len(parts) > 5 else None
            }
    
    def register(self, name: str):
        """Decorator to register custom function."""
        def decorator(func):
            self._functions[name] = func
            return func
        return decorator
    
    def get(self, name: str):
        """Get custom function by name."""
        return self._functions.get(name)
```

### Validation Rules

```yaml
validation_rules:
  - field: "identifier"
    rules:
      - type: "required"
      - type: "pattern"
        pattern: "^[A-Z0-9_]+$"
      - type: "length"
        min: 3
        max: 50
  
  - field: "value"
    rules:
      - type: "numeric"
        min: 0
        max: 1000
      - type: "precision"
        decimal_places: 2
```

## Benefits

1. **Flexibility**: Change normalization logic without code modifications
2. **Reusability**: Share normalization configs across projects
3. **Maintainability**: Clear, declarative rules are easier to understand
4. **Validation**: Built-in validation ensures data quality
5. **Performance**: Pre-compiled patterns and streaming processing
6. **Debugging**: Clear error messages with rule context

## Next Steps

- Create library of standard normalization configs
- Build config validation and testing tools
- Add support for conditional rule chains
- Implement normalization preview mode
- Create visual rule builder interface