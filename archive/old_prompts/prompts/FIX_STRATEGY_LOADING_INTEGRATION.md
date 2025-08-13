# Fix Strategy Loading Integration Issue

## Context

The biomapper infrastructure is **100% functional**:
- ✅ All 26 actions registered and working
- ✅ API server running successfully
- ✅ Test data configured correctly
- ✅ Variable substitution fixed

**Current Issue**: Strategies load but aren't accessible via API due to name resolution problems.

## Diagnosis Phase

### Step 1: Identify How Strategies Are Actually Loaded

```python
# Diagnose strategy loading mechanism
cat > /tmp/diagnose_strategy_loading.py << 'EOF'
import os
import yaml
from pathlib import Path
import json

def analyze_strategy_loading():
    """Analyze how strategies are loaded and named."""
    
    # Check strategy directories
    strategy_dirs = [
        '/home/ubuntu/biomapper/configs/strategies',
        '/home/ubuntu/biomapper/configs/strategies/experimental'
    ]
    
    strategies_found = {}
    
    for dir_path in strategy_dirs:
        if Path(dir_path).exists():
            yaml_files = list(Path(dir_path).glob('*.yaml'))
            print(f"\nDirectory: {dir_path}")
            print(f"Found {len(yaml_files)} YAML files")
            
            for yaml_file in yaml_files[:5]:  # Sample first 5
                with open(yaml_file, 'r') as f:
                    try:
                        content = yaml.safe_load(f)
                        file_name = yaml_file.stem
                        strategy_name = content.get('name', 'NO_NAME')
                        
                        print(f"\n  File: {file_name}.yaml")
                        print(f"    name field: {strategy_name}")
                        print(f"    Match: {'✅' if file_name == strategy_name else '❌'}")
                        
                        strategies_found[file_name] = strategy_name
                    except Exception as e:
                        print(f"    Error loading: {e}")
    
    return strategies_found

def check_api_strategy_loader():
    """Check how the API loads strategies."""
    api_file = '/home/ubuntu/biomapper/biomapper-api/app/services/mapper_service.py'
    
    if Path(api_file).exists():
        with open(api_file, 'r') as f:
            content = f.read()
            
        # Look for strategy loading code
        if 'load_strategy' in content or 'get_strategy' in content:
            print("\n=== API Strategy Loading Code ===")
            # Extract relevant lines
            lines = content.split('\n')
            for i, line in enumerate(lines):
                if 'strategy' in line.lower() and ('load' in line.lower() or 'get' in line.lower()):
                    print(f"Line {i}: {line.strip()}")

def get_loaded_strategies_from_api():
    """Get strategies as the API sees them."""
    import requests
    
    try:
        response = requests.get("http://localhost:8001/api/v1/strategies")
        if response.status_code == 200:
            strategies = response.json()
            print(f"\n=== API Reports {len(strategies)} Strategies ===")
            
            # Show first 5
            for strategy in strategies[:5]:
                print(f"  - {strategy.get('name', 'NO_NAME')}")
                if 'description' in strategy:
                    print(f"    Desc: {strategy['description'][:50]}...")
            
            return [s.get('name') for s in strategies]
    except Exception as e:
        print(f"API Error: {e}")
        return []

if __name__ == "__main__":
    print("=" * 70)
    print("STRATEGY LOADING DIAGNOSIS")
    print("=" * 70)
    
    # Analyze file vs name field
    file_to_name = analyze_strategy_loading()
    
    # Check API loader
    check_api_strategy_loader()
    
    # Get API's view
    api_strategies = get_loaded_strategies_from_api()
    
    # Compare
    print("\n" + "=" * 70)
    print("DIAGNOSIS RESULTS")
    print("=" * 70)
    
    if file_to_name:
        mismatches = [(f, n) for f, n in file_to_name.items() if f != n]
        if mismatches:
            print(f"\n⚠️  Found {len(mismatches)} name mismatches:")
            for file_name, yaml_name in mismatches[:5]:
                print(f"  File: {file_name} → YAML name: {yaml_name}")
            print("\nThis is likely the root cause!")
EOF

python /tmp/diagnose_strategy_loading.py
```

### Step 2: Check Strategy Service Implementation

```bash
# Check how strategies are indexed
grep -n "strategy_name" /home/ubuntu/biomapper/biomapper-api/app/services/mapper_service.py | head -10

# Check if using file name or YAML name field
grep -n "\.yaml\|\.yml" /home/ubuntu/biomapper/biomapper-api/app/services/mapper_service.py | head -10

# Look for strategy registry/cache
grep -n "strategies\[" /home/ubuntu/biomapper/biomapper-api/app/services/mapper_service.py | head -10
```

## Fix Phase

### Option 1: Quick Fix - Update Strategy Name Fields

If the issue is mismatched names, update YAML files to match their filenames:

```python
# Fix strategy name fields to match filenames
cat > /tmp/fix_strategy_names.py << 'EOF'
import yaml
from pathlib import Path
import shutil

def fix_strategy_names(dry_run=True):
    """Update YAML name fields to match filenames."""
    
    experimental_dir = Path('/home/ubuntu/biomapper/configs/strategies/experimental')
    
    if not experimental_dir.exists():
        print("Experimental directory not found")
        return
    
    fixed_count = 0
    
    for yaml_file in experimental_dir.glob('*.yaml'):
        with open(yaml_file, 'r') as f:
            content = yaml.safe_load(f)
        
        file_name = yaml_file.stem
        yaml_name = content.get('name', '')
        
        if file_name != yaml_name:
            print(f"\nFixing: {yaml_file.name}")
            print(f"  Old name: {yaml_name}")
            print(f"  New name: {file_name}")
            
            if not dry_run:
                # Backup original
                shutil.copy(yaml_file, f"{yaml_file}.backup")
                
                # Update name field
                content['name'] = file_name
                
                # Write back
                with open(yaml_file, 'w') as f:
                    yaml.dump(content, f, default_flow_style=False, sort_keys=False)
                
                print(f"  ✅ Fixed!")
            else:
                print(f"  🔍 Would fix (dry run)")
            
            fixed_count += 1
    
    print(f"\n{'Would fix' if dry_run else 'Fixed'} {fixed_count} strategies")
    return fixed_count

if __name__ == "__main__":
    print("=" * 70)
    print("STRATEGY NAME FIX")
    print("=" * 70)
    
    # Dry run first
    print("\n--- DRY RUN ---")
    count = fix_strategy_names(dry_run=True)
    
    if count > 0:
        response = input(f"\nFix {count} strategies? (y/n): ")
        if response.lower() == 'y':
            print("\n--- APPLYING FIXES ---")
            fix_strategy_names(dry_run=False)
            print("\n✅ Strategy names fixed!")
        else:
            print("Skipped fixes")
EOF

python /tmp/fix_strategy_names.py
```

### Option 2: Fix API Strategy Resolver

If the API needs to use file names instead of YAML name fields:

```python
# Check current strategy loading logic
cat > /tmp/check_strategy_resolver.py << 'EOF'
from pathlib import Path

def analyze_mapper_service():
    """Analyze the mapper service strategy loading."""
    
    mapper_service = Path('/home/ubuntu/biomapper/biomapper-api/app/services/mapper_service.py')
    
    if mapper_service.exists():
        with open(mapper_service, 'r') as f:
            content = f.read()
        
        # Find the load_strategy method
        lines = content.split('\n')
        
        in_load_method = False
        method_lines = []
        
        for line in lines:
            if 'def load_strategy' in line or 'def get_strategy' in line:
                in_load_method = True
                method_lines = [line]
            elif in_load_method:
                if line and not line[0].isspace() and 'def ' in line:
                    # Next method started
                    break
                method_lines.append(line)
        
        if method_lines:
            print("=== Current Strategy Loading Logic ===")
            for line in method_lines[:30]:  # First 30 lines
                print(line)
            
            # Identify the issue
            method_text = '\n'.join(method_lines)
            if "strategy['name']" in method_text:
                print("\n⚠️  API uses YAML 'name' field for indexing")
                print("   This causes mismatch with file names!")
            elif ".stem" in method_text or "file_name" in method_text:
                print("\n✅ API uses file names for indexing")

if __name__ == "__main__":
    analyze_mapper_service()
EOF

python /tmp/check_strategy_resolver.py
```

### Option 3: Create Strategy Name Mapping

If we can't change the files or API, create a mapping:

```python
# Create strategy name mapping
cat > /tmp/create_strategy_mapping.py << 'EOF'
import yaml
import json
from pathlib import Path

def create_strategy_mapping():
    """Create a mapping between file names and YAML names."""
    
    experimental_dir = Path('/home/ubuntu/biomapper/configs/strategies/experimental')
    
    mapping = {}
    
    for yaml_file in experimental_dir.glob('*.yaml'):
        with open(yaml_file, 'r') as f:
            try:
                content = yaml.safe_load(f)
                file_name = yaml_file.stem
                yaml_name = content.get('name', file_name)
                
                mapping[file_name] = yaml_name
                
                # Also map the reverse
                mapping[yaml_name] = file_name
                
            except Exception as e:
                print(f"Error loading {yaml_file}: {e}")
    
    # Save mapping
    mapping_file = '/home/ubuntu/biomapper/configs/strategy_name_mapping.json'
    with open(mapping_file, 'w') as f:
        json.dump(mapping, f, indent=2)
    
    print(f"Created mapping with {len(mapping)} entries")
    print(f"Saved to: {mapping_file}")
    
    # Show sample
    print("\nSample mappings:")
    for key, value in list(mapping.items())[:5]:
        print(f"  {key} → {value}")
    
    return mapping

if __name__ == "__main__":
    mapping = create_strategy_mapping()
EOF

python /tmp/create_strategy_mapping.py
```

## Validation Phase

### Test Fixed Strategies

```python
# Test after fixing
cat > /tmp/test_fixed_strategies.py << 'EOF'
import requests
import time

def test_strategies():
    """Test if strategies work after fixes."""
    
    test_strategies = [
        'prot_arv_to_kg2c_uniprot_v1_base',
        'chem_arv_to_kg2c_phenotypes_v1_base',
        'met_arv_to_spoke_hmdb_v1_base'
    ]
    
    api_base = "http://localhost:8001"
    results = []
    
    print("Testing fixed strategies...")
    print("-" * 40)
    
    for strategy_name in test_strategies:
        print(f"\nTesting: {strategy_name}")
        
        try:
            # Try with file name
            response = requests.post(
                f"{api_base}/api/v1/strategies/execute",
                json={"strategy_name": strategy_name},
                timeout=10
            )
            
            if response.status_code == 200:
                print(f"  ✅ Strategy found and submitted!")
                job_id = response.json().get('job_id')
                
                time.sleep(2)
                
                # Check status
                status_resp = requests.get(f"{api_base}/api/v1/jobs/{job_id}/status")
                if status_resp.status_code == 200:
                    status = status_resp.json().get('status')
                    print(f"  Status: {status}")
                    
                    if status == 'completed':
                        results.append('SUCCESS')
                    else:
                        results.append('RUNNING')
            else:
                print(f"  ❌ Not found with file name")
                results.append('NOT_FOUND')
                
        except Exception as e:
            print(f"  ❌ Error: {e}")
            results.append('ERROR')
    
    # Summary
    success_count = results.count('SUCCESS') + results.count('RUNNING')
    print("\n" + "=" * 40)
    print(f"Results: {success_count}/{len(test_strategies)} strategies accessible")
    
    if success_count > 0:
        print("🎉 BREAKTHROUGH! Strategies are now accessible!")
        print(f"   Improvement: 0% → {(success_count/len(test_strategies)*100):.0f}%")
    
    return results

if __name__ == "__main__":
    test_strategies()
EOF

python /tmp/test_fixed_strategies.py
```

## Expected Outcome

After applying the fix, we should see:
- Strategies become accessible via API
- At least some strategies execute successfully
- Clear improvement from 0% to >0% success rate

## Success Criteria

- [ ] Strategy name mismatch identified
- [ ] Fix applied (names updated or API modified)
- [ ] At least 1 strategy executes successfully
- [ ] End-to-end validation complete

## Time Estimate

- Diagnosis: 10 minutes
- Fix application: 15 minutes
- Validation: 10 minutes
- **Total: ~35 minutes**

## Notes

This is the final piece to make the biomapper system fully operational. Once strategy loading is fixed, the entire pipeline will work end-to-end with all the improvements made.