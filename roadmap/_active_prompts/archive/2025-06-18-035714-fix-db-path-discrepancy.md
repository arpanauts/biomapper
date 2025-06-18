# Task: Resolve Persistent "Strategy Not Found" Error by Unifying Database Path Configuration

## 1. Objective

Diagnose and permanently fix the `Strategy 'UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT' not found in database` error that occurs when running the `run_full_ukbb_hpa_mapping.py` script. The root cause is a discrepancy in how the database path is determined between the population script and the main execution script.

The goal is to refactor the configuration to ensure all parts of the application use a single, consistent path for the `metamapper.db`.

## 2. Background & Context

Despite multiple attempts to fix the pipeline, the same error persists. Here's what has been done:

1.  The `UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT` strategy was correctly defined in `configs/mapping_strategies_config.yaml`.
2.  The `populate_metamapper_db.py` script was run to update the database with the new strategy.
3.  The `run_full_ukbb_hpa_mapping.py` script was modified to use what appears to be the correct, absolute path to the database.

Despite these fixes, the error remains, indicating the two scripts are still operating on different database files. The current approach of each script defining its own path to the database is brittle and error-prone.

## 3. Investigation and Implementation Plan

### Step 1: Centralize Database Path in `biomapper/config.py`

Create a single source of truth for the database path.

**File to Modify:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/biomapper/config.py`

**Action:**
- At the top of the file, add a definition for `BIOMAPPER_ROOT`.
- Use this root path to define an absolute path for `metamapper_db_url` within the `Settings` class.

```python
# Add near the top
from pathlib import Path
BIOMAPPER_ROOT = Path(__file__).resolve().parents[1]

# ... inside the Settings class ...
class Settings(BaseSettings):
    # ... other settings ...
    metamapper_db_url: str = f"sqlite+aiosqlite:///{BIOMAPPER_ROOT / 'data' / 'metamapper.db'}"
    cache_db_url: str = f"sqlite+aiosqlite:///{BIOMAPPER_ROOT / 'data' / 'mapping_cache.db'}"
    # ... other settings ...
```

### Step 2: Update `run_full_ukbb_hpa_mapping.py` to Use Central Config

Refactor the main pipeline script to remove its local path construction and use the new centralized setting.

**File to Modify:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/scripts/main_pipelines/run_full_ukbb_hpa_mapping.py`

**Action:**
- Remove the manual construction of `metamapper_db_path` and `correct_metamapper_db_url`.
- When creating the `MappingExecutor`, pass `settings.metamapper_db_url` directly. It will now hold the correct, absolute path.

```python
# This block should be removed
# metamapper_db_path = BIOMAPPER_ROOT / "data" / "metamapper.db"
# correct_metamapper_db_url = f"sqlite+aiosqlite:///{metamapper_db_path.resolve()}"

# ... later in the script ...

# This call should be simplified
executor = await MappingExecutor.create(
    metamapper_db_url=settings.metamapper_db_url, # This now comes from the central config
    mapping_cache_db_url=settings.cache_db_url,
    # ... other params
)
```

### Step 3: Update `populate_metamapper_db.py` to Use Central Config

Ensure the population script also uses the same centralized path.

**File to Modify:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/scripts/setup_and_configuration/populate_metamapper_db.py`

**Action:**
- In the `main` function, when initializing the `DatabaseManager`, ensure it uses the default URL from `settings`, which is now the correct, absolute path.

```python
# In the main function of the population script
manager = DatabaseManager(db_url=settings.metamapper_db_url) # Explicitly use the setting
await manager.init_db_async(drop_all=drop_all)
```

### Step 4: Add Diagnostic Logging to Population Script

Add logging to verify that the strategy is being parsed from the YAML file.

**File to Modify:** `/home/ubuntu/Software-Engineer-AI-Agent-Atlas/biomapper/scripts/setup_and_configuration/populate_metamapper_db.py`

**Action:**
- In the function responsible for populating strategies, add a log message that lists the names of all strategies found in the YAML file before they are inserted into the database.

## 4. Validation

1.  After applying the changes, run the population script first:
    `python scripts/setup_and_configuration/populate_metamapper_db.py`
    - Check the logs to confirm the new diagnostic message shows `UKBB_TO_HPA_BIDIRECTIONAL_EFFICIENT` as a strategy to be populated.

2.  Then, run the main pipeline script:
    `python scripts/main_pipelines/run_full_ukbb_hpa_mapping.py`
    - The script should now start successfully without the "Strategy not found" error.

## 5. Feedback

Create a feedback file named `YYYY-MM-DD-HHMMSS-feedback-fix-db-path-discrepancy.md` and report on the outcome. Confirm that the refactoring was successful and the pipeline now runs. If errors persist, include the logs from both scripts for further analysis.
