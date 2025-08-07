# Biomapper Cleanup Execution Prompt

## Objective
Execute the cleanup plan systematically, removing ~30-40% dead code while maintaining all active functionality. Update the cleanup tracker after each step.

## Pre-Execution Setup

### 1. Create Backup and Working Branch
```bash
# Create backup branch
git checkout main
git pull origin main
git checkout -b cleanup-backup-$(date +%Y%m%d)
git push origin cleanup-backup-$(date +%Y%m%d)

# Create working branch for cleanup
git checkout -b cleanup-phase-1-safe-removals

# Verify current state
git status
make check  # Ensure everything passes before starting
```

### 2. Capture Baseline Metrics
```bash
# Count total lines of code
find biomapper biomapper-api biomapper_client -name "*.py" | xargs wc -l | tail -1

# Count number of Python files
find biomapper biomapper-api biomapper_client -name "*.py" | wc -l

# Run coverage baseline
poetry run pytest --cov=biomapper --cov=biomapper-api --cov=biomapper_client --cov-report=term

# Save output to cleanup_tracker.md under "Pre-Cleanup Baseline"
```

## Phase 1: Safe Immediate Removals

### Step 1.1: Remove Old Action Files
```bash
# Navigate to strategy actions directory
cd /home/ubuntu/biomapper/biomapper/core/strategy_actions/

# Verify these files are not imported anywhere
grep -r "load_endpoint_identifiers_action_old" /home/ubuntu/biomapper/
grep -r "format_and_save_results_action_old" /home/ubuntu/biomapper/

# If no imports found (except from themselves), remove them
rm load_endpoint_identifiers_action_old.py
rm format_and_save_results_action_old.py

# Verify removal
ls *_old.py  # Should return nothing

# Run tests to ensure nothing broke
cd /home/ubuntu/biomapper
poetry run pytest tests/unit/core/strategy_actions/
```

**Update cleanup_tracker.md:**
- [ ] ✅ Remove `load_endpoint_identifiers_action_old.py`
- [ ] ✅ Remove `format_and_save_results_action_old.py`

### Step 1.2: Clean Engine Components Directory
```bash
cd /home/ubuntu/biomapper/biomapper/core/engine_components/

# First, verify what's currently using CheckpointManager and ProgressReporter
grep -r "CheckpointManager" /home/ubuntu/biomapper/ --exclude-dir=__pycache__
grep -r "ProgressReporter" /home/ubuntu/biomapper/ --exclude-dir=__pycache__

# Verify unused files have no imports
grep -r "action_loader" /home/ubuntu/biomapper/ --exclude-dir=__pycache__
grep -r "config_loader" /home/ubuntu/biomapper/ --exclude-dir=__pycache__
grep -r "robust_execution_coordinator" /home/ubuntu/biomapper/ --exclude-dir=__pycache__
grep -r "strategy_coordinator_service" /home/ubuntu/biomapper/ --exclude-dir=__pycache__

# Remove unused files
rm action_loader.py
rm config_loader.py
rm robust_execution_coordinator.py
rm strategy_coordinator_service.py

# Update __init__.py to only export the kept components
cat > __init__.py << 'EOF'
"""Engine components for execution management."""
from .checkpoint_manager import CheckpointManager
from .progress_reporter import ProgressReporter

__all__ = ["CheckpointManager", "ProgressReporter"]
EOF

# Verify the changes
ls -la
cat __init__.py

# Test that imports still work
cd /home/ubuntu/biomapper
python -c "from biomapper.core.engine_components import CheckpointManager, ProgressReporter; print('Imports successful')"

# Run related tests
poetry run pytest tests/ -k "checkpoint" -v
poetry run pytest tests/ -k "progress" -v
```

**Update cleanup_tracker.md** with checkmarks for removed files

### Step 1.3: Identify and Remove Duplicate API Routes
```bash
cd /home/ubuntu/biomapper/biomapper-api/app/api/routes/

# Analyze which strategy routes are actually used
grep -r "from app.api.routes" /home/ubuntu/biomapper/biomapper-api/

# Check main.py to see which routers are included
grep "include_router" /home/ubuntu/biomapper/biomapper-api/app/main.py

# Compare the three strategy route files
wc -l strategies.py strategies_enhanced.py strategies_v2_simple.py
diff strategies.py strategies_enhanced.py | head -20
diff strategies.py strategies_v2_simple.py | head -20

# Determine which one is actually being used in main.py
# Keep only the active one, remove the others
# Example (adjust based on findings):
# rm strategies_enhanced.py  # If not used
# rm strategies_v2_simple.py  # If not used

# Check for other potentially unused routes
grep -l "router\|APIRouter" *.py | while read file; do
    echo "=== $file ==="
    grep -q "$file\|${file%.py}" ../../../app/main.py && echo "USED" || echo "POSSIBLY UNUSED"
done
```

### Step 1.4: Validate Phase 1 Changes
```bash
cd /home/ubuntu/biomapper

# Full validation suite
make check

# Specific validations
poetry run ruff check .
poetry run mypy biomapper biomapper-api biomapper_client
poetry run pytest -xvs

# Test API still works
cd biomapper-api
poetry run uvicorn app.main:app --reload &
sleep 5
curl http://localhost:8000/health
curl http://localhost:8000/api/v1/strategies
kill %1

# Test client still works
cd /home/ubuntu/biomapper
poetry run biomapper health
poetry run biomapper metadata list

# If all passes, commit Phase 1
git add -A
git commit -m "Phase 1: Remove old action files and unused engine components

- Removed 2 *_old.py action files (no longer used)
- Removed 4 unused engine_components files
- Kept only CheckpointManager and ProgressReporter
- Updated engine_components __init__.py
- All tests passing"
```

## Phase 2: Database Model Consolidation

### Step 2.1: Analyze Database Models
```bash
cd /home/ubuntu/biomapper/biomapper-api/app/models/

# Compare the two model files
diff job.py persistence.py

# Find actual usage of each model
grep -r "from app.models.job import" /home/ubuntu/biomapper/biomapper-api/
grep -r "from app.models.persistence import" /home/ubuntu/biomapper/biomapper-api/

# Check which tables actually exist in the database
cd /home/ubuntu/biomapper/biomapper-api
sqlite3 biomapper.db ".tables"
sqlite3 biomapper.db ".schema execution_logs"
sqlite3 biomapper.db ".schema jobs"

# Check Alembic migrations to understand history
ls -la alembic/versions/
grep -h "create_table\|drop_table" alembic/versions/*.py

# Determine which model is actually being used by services
grep -r "Job\|ExecutionLog\|JobEvent" app/services/
```

### Step 2.2: Consolidate Models (Example Decision Tree)
```bash
# IF job.py is primary:
cd /home/ubuntu/biomapper/biomapper-api/app/models/

# Backup both files first
cp job.py job.py.backup
cp persistence.py persistence.py.backup

# Identify unique features in persistence.py that need to be preserved
# Merge any unique features into job.py
# Update job.py with any missing fields/methods from persistence.py

# Update all imports
find /home/ubuntu/biomapper/biomapper-api -name "*.py" -exec grep -l "from app.models.persistence" {} \; | while read file; do
    echo "Updating imports in $file"
    sed -i 's/from app.models.persistence/from app.models.job/g' "$file"
done

# Remove the duplicate model
rm persistence.py

# Create migration if schema changed
cd /home/ubuntu/biomapper/biomapper-api
poetry run alembic revision -m "Consolidate database models into job.py"
# Edit the generated migration file if needed
poetry run alembic upgrade head

# Test persistence still works
poetry run pytest tests/ -k "persistence" -v
```

**Update cleanup_tracker.md** Phase 2 section

## Phase 3: Fix Missing Actions

### Step 3.1: Implement EXPORT_DATASET Action
```bash
cd /home/ubuntu/biomapper/biomapper/core/strategy_actions/

# First, check how it's used in strategies
grep -r "EXPORT_DATASET" /home/ubuntu/biomapper/configs/strategies/

# Create the action implementation
cat > export_dataset.py << 'EOF'
"""Export dataset action for saving results to various formats."""
from typing import Dict, Any
from pathlib import Path
import pandas as pd
from pydantic import BaseModel, Field

from biomapper.core.strategy_actions.typed_base import TypedStrategyAction
from biomapper.core.strategy_actions.registry import register_action
from biomapper.core.models.action_results import ActionResult


class ExportDatasetParams(BaseModel):
    """Parameters for EXPORT_DATASET action."""
    input_key: str = Field(..., description="Key in context containing data to export")
    output_path: str = Field(..., description="Path where to save the exported file")
    format: str = Field(default="tsv", description="Export format: tsv, csv, json, xlsx")
    columns: list[str] | None = Field(default=None, description="Specific columns to export")


@register_action("EXPORT_DATASET")
class ExportDatasetAction(TypedStrategyAction[ExportDatasetParams, ActionResult]):
    """Export dataset to file in specified format."""
    
    def get_params_model(self) -> type[ExportDatasetParams]:
        return ExportDatasetParams
    
    async def execute_typed(
        self, 
        params: ExportDatasetParams, 
        context: Dict[str, Any]
    ) -> ActionResult:
        """Export dataset from context to file."""
        try:
            # Get data from context
            if params.input_key not in context.get("datasets", {}):
                return ActionResult(
                    success=False,
                    error=f"Dataset '{params.input_key}' not found in context"
                )
            
            data = context["datasets"][params.input_key]
            
            # Convert to DataFrame if needed
            if not isinstance(data, pd.DataFrame):
                df = pd.DataFrame(data)
            else:
                df = data
            
            # Filter columns if specified
            if params.columns:
                df = df[params.columns]
            
            # Export based on format
            output_path = Path(params.output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            if params.format == "tsv":
                df.to_csv(output_path, sep='\t', index=False)
            elif params.format == "csv":
                df.to_csv(output_path, index=False)
            elif params.format == "json":
                df.to_json(output_path, orient='records', indent=2)
            elif params.format == "xlsx":
                df.to_excel(output_path, index=False)
            else:
                return ActionResult(
                    success=False,
                    error=f"Unsupported format: {params.format}"
                )
            
            # Update context with output file info
            if "output_files" not in context:
                context["output_files"] = {}
            context["output_files"][params.input_key] = str(output_path)
            
            return ActionResult(
                success=True,
                data={"exported_path": str(output_path), "row_count": len(df)}
            )
            
        except Exception as e:
            return ActionResult(
                success=False,
                error=f"Export failed: {str(e)}"
            )
EOF

# Create test for the new action
cat > /home/ubuntu/biomapper/tests/unit/core/strategy_actions/test_export_dataset.py << 'EOF'
"""Tests for EXPORT_DATASET action."""
import pytest
from pathlib import Path
import pandas as pd
import tempfile

from biomapper.core.strategy_actions.export_dataset import ExportDatasetAction, ExportDatasetParams


@pytest.mark.asyncio
async def test_export_dataset_tsv():
    """Test exporting dataset to TSV format."""
    with tempfile.TemporaryDirectory() as tmpdir:
        # Setup
        action = ExportDatasetAction()
        context = {
            "datasets": {
                "test_data": pd.DataFrame({
                    "id": ["A", "B", "C"],
                    "value": [1, 2, 3]
                })
            }
        }
        
        params = ExportDatasetParams(
            input_key="test_data",
            output_path=f"{tmpdir}/output.tsv",
            format="tsv"
        )
        
        # Execute
        result = await action.execute_typed(params, context)
        
        # Verify
        assert result.success
        assert Path(f"{tmpdir}/output.tsv").exists()
        
        # Read back and verify content
        df = pd.read_csv(f"{tmpdir}/output.tsv", sep='\t')
        assert len(df) == 3
        assert list(df.columns) == ["id", "value"]


@pytest.mark.asyncio  
async def test_export_dataset_missing_data():
    """Test export fails gracefully when data is missing."""
    action = ExportDatasetAction()
    context = {"datasets": {}}
    
    params = ExportDatasetParams(
        input_key="missing_data",
        output_path="/tmp/output.tsv"
    )
    
    result = await action.execute_typed(params, context)
    assert not result.success
    assert "not found" in result.error
EOF

# Run the test
poetry run pytest tests/unit/core/strategy_actions/test_export_dataset.py -xvs

# Verify the action is registered
python -c "from biomapper.core.strategy_actions.registry import ACTION_REGISTRY; print('EXPORT_DATASET' in ACTION_REGISTRY)"
```

### Step 3.2: Repeat for Other Missing Actions
Follow similar pattern for:
- CUSTOM_TRANSFORM
- EXECUTE_MAPPING_PATH
- Other missing actions

**Update cleanup_tracker.md** Phase 3 section as you complete each action

## Phase 4: Script Modernization

### Step 4.1: Convert Scripts to Use BiomapperClient
```bash
# Example conversion for one script
cd /home/ubuntu/biomapper/scripts/analysis/

# Backup original
cp dataset_comparison.py dataset_comparison.py.old

# Check current imports
grep "^from biomapper\|^import biomapper" dataset_comparison.py

# Convert the script (example transformation)
cat > dataset_comparison_modernized.py << 'EOF'
#!/usr/bin/env python3
"""Dataset comparison using BiomapperClient."""
import sys
from pathlib import Path

# Add path to import biomapper_client
sys.path.append(str(Path(__file__).parent.parent.parent))

from biomapper_client import BiomapperClient


def main():
    """Main execution using BiomapperClient."""
    client = BiomapperClient(base_url="http://localhost:8000")
    
    # Check health
    health = client.health_check()
    if not health.get("status") == "healthy":
        print("API is not healthy")
        return
    
    # Execute strategy instead of direct service calls
    result = client.execute_strategy(
        "DATASET_COMPARISON",
        parameters={
            "dataset1": "path/to/dataset1.tsv",
            "dataset2": "path/to/dataset2.tsv"
        }
    )
    
    print(f"Comparison complete: {result}")


if __name__ == "__main__":
    main()
EOF

# Test the modernized script
poetry run python dataset_comparison_modernized.py

# If successful, replace original
mv dataset_comparison_modernized.py dataset_comparison.py
rm dataset_comparison.py.old
```

### Step 4.2: Batch Convert Remaining Scripts
```bash
# Create a conversion script for efficiency
cat > /tmp/modernize_scripts.py << 'EOF'
#!/usr/bin/env python3
"""Modernize scripts to use BiomapperClient."""
import re
from pathlib import Path

scripts_to_convert = [
    "scripts/analysis/dataset_comparison.py",
    "scripts/analysis/identifier_analysis.py",
    "scripts/converters/arivale_name_mapper.py",
    "scripts/data_processing/filter_mapping_results.py",
    "scripts/data_processing/generate_test_data.py",
    "scripts/entity_analysis/entity_set_analyzer.py",
    "scripts/main_pipelines/run_metabolomics_workflow.py",
    "scripts/mapping_execution/identifier_mapper.py",
    "scripts/protein_analysis/protein_metadata_comparison.py",
    "scripts/testing/test_iterative_mapping.py",
    "scripts/testing/test_minimal_strategy.py",
]

for script_path in scripts_to_convert:
    path = Path(f"/home/ubuntu/biomapper/{script_path}")
    if not path.exists():
        print(f"Skip: {script_path} not found")
        continue
    
    # Backup
    backup = path.with_suffix('.py.backup')
    path.rename(backup)
    
    # Read original
    content = backup.read_text()
    
    # Check if already uses BiomapperClient
    if "BiomapperClient" in content:
        print(f"Skip: {script_path} already uses BiomapperClient")
        backup.rename(path)  # Restore original
        continue
    
    # Basic conversion (customize as needed)
    # Replace direct imports
    content = re.sub(
        r'from biomapper\.core\..*? import .*?\n',
        '',
        content
    )
    
    # Add BiomapperClient import
    if "from biomapper_client import BiomapperClient" not in content:
        content = "from biomapper_client import BiomapperClient\n\n" + content
    
    # Write modernized version
    path.write_text(content)
    print(f"Modernized: {script_path}")
EOF

python /tmp/modernize_scripts.py
```

**Update cleanup_tracker.md** as each script is converted

## Phase 5: Remove Unused Actions

### Step 5.1: Remove Unused Registered Actions
```bash
cd /home/ubuntu/biomapper/biomapper/core/strategy_actions/

# Verify these are truly unused
grep -r "PROTEIN_EXTRACT_UNIPROT_FROM_XREFS" /home/ubuntu/biomapper/configs/strategies/
grep -r "PROTEIN_MULTI_BRIDGE" /home/ubuntu/biomapper/configs/strategies/

# If confirmed unused, find their files
grep -r "@register_action.*PROTEIN_EXTRACT_UNIPROT_FROM_XREFS" .
grep -r "@register_action.*PROTEIN_MULTI_BRIDGE" .

# Remove the files (adjust paths based on findings)
rm entities/proteins/annotation/extract_uniprot_from_xrefs.py
rm entities/proteins/matching/multi_bridge.py

# Remove any associated tests
rm /home/ubuntu/biomapper/tests/unit/core/strategy_actions/test_extract_uniprot_from_xrefs.py 2>/dev/null
rm /home/ubuntu/biomapper/tests/unit/core/strategy_actions/test_multi_bridge.py 2>/dev/null

# Verify removal
python -c "from biomapper.core.strategy_actions.registry import ACTION_REGISTRY; print('PROTEIN_EXTRACT_UNIPROT_FROM_XREFS' in ACTION_REGISTRY)"
```

## Phase 6 & 7: Investigation and Test Coverage
These phases require more investigation before execution. Document findings in cleanup_tracker.md.

## Post-Execution Validation

### Final Validation Suite
```bash
cd /home/ubuntu/biomapper

# Complete check
make check

# Measure final metrics
echo "=== FINAL METRICS ===" >> /home/ubuntu/biomapper/configs/prompts/cleanup_tracker.md
echo "Date: $(date)" >> /home/ubuntu/biomapper/configs/prompts/cleanup_tracker.md
find biomapper biomapper-api biomapper_client -name "*.py" | xargs wc -l | tail -1 >> /home/ubuntu/biomapper/configs/prompts/cleanup_tracker.md
find biomapper biomapper-api biomapper_client -name "*.py" | wc -l >> /home/ubuntu/biomapper/configs/prompts/cleanup_tracker.md
poetry run pytest --cov=biomapper --cov=biomapper-api --cov=biomapper_client --cov-report=term >> /home/ubuntu/biomapper/configs/prompts/cleanup_tracker.md

# Test all example strategies still work
for strategy in $(ls configs/strategies/*.yaml | xargs -n1 basename | sed 's/.yaml//'); do
    echo "Testing strategy: $strategy"
    poetry run biomapper execute-strategy $strategy --test-mode
done

# Create final commit
git add -A
git commit -m "Complete cleanup: Removed ~30-40% dead code

- Removed old action files and unused engine components
- Consolidated database models
- Implemented missing actions (EXPORT_DATASET, etc.)
- Modernized 11 scripts to use BiomapperClient
- Removed unused registered actions
- All tests passing, functionality preserved"

# Push to remote for review
git push origin cleanup-phase-1-safe-removals
```

## Important Reminders

1. **Always run tests after each removal** - Don't batch removals without testing
2. **Update cleanup_tracker.md immediately** - Document as you go
3. **Commit frequently** - Small, logical commits are easier to revert if needed
4. **Check for dynamic imports** - Some code might be imported via strings
5. **Verify YAML strategies** - Ensure they still execute after changes
6. **Keep backups** - Use git branches and backup files liberally

## Rollback Procedure

If something breaks:
```bash
# Immediate rollback to last working state
git reset --hard HEAD~1

# Or restore from backup branch
git checkout cleanup-backup-$(date +%Y%m%d)
git checkout -b cleanup-retry

# Or revert specific commit
git revert <commit-hash>
```

## Success Criteria

✅ All tests pass: `make check`
✅ All YAML strategies execute successfully
✅ API endpoints respond correctly
✅ Line count reduced by 30-40%
✅ No functionality lost
✅ Documentation updated
✅ cleanup_tracker.md fully completed