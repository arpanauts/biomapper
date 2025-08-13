# SEQUENTIAL 4: Architecture Refactoring Investigation

**Prerequisites: Should be done AFTER PRIORITY_1 and ideally after some cleanup (PARALLEL_3)**

## Problem Statement

The current biomapper architecture has grown organically, resulting in:
- Three separate packages (biomapper, biomapper-api, biomapper_client)
- Strategies stored far from their action implementations
- Unclear separation of concerns between packages
- Complex dependency chains
- Difficult onboarding for new developers
- Inconsistent patterns across modules

## Objective

Investigate and propose a more maintainable, scalable architecture that:
- Reduces cognitive load for developers
- Improves modularity and testability
- Clarifies separation of concerns
- Enables easier feature additions
- Supports future growth

## Current Architecture Analysis

### 1. Document Current Structure

```python
# Create architecture analysis script
cat > /tmp/analyze_architecture.py << 'EOF'
import os
from pathlib import Path
import json
from collections import defaultdict

def analyze_current_architecture():
    """Analyze the current biomapper architecture."""
    
    root = Path("/home/ubuntu/biomapper")
    
    analysis = {
        'packages': {},
        'dependencies': defaultdict(list),
        'file_counts': {},
        'line_counts': {},
        'complexity_metrics': {}
    }
    
    # Analyze each package
    packages = ['biomapper', 'biomapper-api', 'biomapper_client']
    
    for package in packages:
        package_path = root / package
        if not package_path.exists():
            continue
            
        # Count files and lines
        py_files = list(package_path.rglob("*.py"))
        yaml_files = list(package_path.rglob("*.yaml"))
        
        total_lines = 0
        for py_file in py_files:
            try:
                total_lines += len(py_file.read_text().splitlines())
            except:
                pass
        
        analysis['packages'][package] = {
            'python_files': len(py_files),
            'yaml_files': len(yaml_files),
            'total_lines': total_lines,
            'main_modules': []
        }
        
        # Find main modules
        for item in package_path.iterdir():
            if item.is_dir() and not item.name.startswith('.') and not item.name.startswith('__'):
                analysis['packages'][package]['main_modules'].append(item.name)
        
        # Analyze imports to understand dependencies
        for py_file in py_files[:50]:  # Sample for speed
            try:
                content = py_file.read_text()
                # Find imports
                import_lines = [l for l in content.splitlines() if l.startswith('from ') or l.startswith('import ')]
                for line in import_lines:
                    if 'biomapper' in line:
                        if package == 'biomapper-api' and 'from biomapper' in line:
                            analysis['dependencies']['api_to_core'].append(line.strip())
                        elif package == 'biomapper_client' and 'from biomapper' in line:
                            analysis['dependencies']['client_to_core'].append(line.strip())
            except:
                pass
    
    # Analyze strategy/action coupling
    strategies_dir = root / "configs" / "strategies"
    experimental_dir = strategies_dir / "experimental"
    
    analysis['strategies'] = {
        'location': str(strategies_dir),
        'experimental_count': len(list(experimental_dir.glob("*.yaml"))) if experimental_dir.exists() else 0,
        'distance_from_actions': "4+ directories away from action implementations"
    }
    
    # Analyze action organization
    actions_dir = root / "biomapper" / "core" / "strategy_actions"
    if actions_dir.exists():
        action_structure = {}
        for category in actions_dir.iterdir():
            if category.is_dir() and not category.name.startswith('__'):
                action_files = list(category.rglob("*.py"))
                action_structure[category.name] = len(action_files)
        analysis['actions'] = action_structure
    
    return analysis

def print_analysis(analysis):
    """Print architecture analysis results."""
    
    print("=" * 70)
    print("BIOMAPPER ARCHITECTURE ANALYSIS")
    print("=" * 70)
    
    print("\n### Package Statistics ###")
    for package, stats in analysis['packages'].items():
        print(f"\n{package}:")
        print(f"  Python files: {stats['python_files']}")
        print(f"  YAML files: {stats['yaml_files']}")
        print(f"  Total lines: {stats['total_lines']:,}")
        print(f"  Main modules: {', '.join(stats['main_modules'][:5])}")
    
    print("\n### Dependencies ###")
    if analysis['dependencies']['api_to_core']:
        print(f"API → Core dependencies: {len(analysis['dependencies']['api_to_core'])}")
    if analysis['dependencies']['client_to_core']:
        print(f"Client → Core dependencies: {len(analysis['dependencies']['client_to_core'])}")
    
    print("\n### Strategy Organization ###")
    print(f"Strategy location: {analysis['strategies']['location']}")
    print(f"Experimental strategies: {analysis['strategies']['experimental_count']}")
    print(f"Distance from actions: {analysis['strategies']['distance_from_actions']}")
    
    print("\n### Action Organization ###")
    if 'actions' in analysis:
        for category, count in analysis['actions'].items():
            print(f"  {category}: {count} files")
    
    # Save to JSON for further analysis
    with open('/tmp/architecture_analysis.json', 'w') as f:
        json.dump(analysis, f, indent=2, default=str)
    
    print("\n✓ Full analysis saved to /tmp/architecture_analysis.json")

if __name__ == "__main__":
    analysis = analyze_current_architecture()
    print_analysis(analysis)
EOF

python /tmp/analyze_architecture.py
```

### 2. Identify Pain Points

```python
# Create pain points identification script
cat > /tmp/identify_pain_points.py << 'EOF'
import os
from pathlib import Path

def identify_pain_points():
    """Identify specific architectural pain points."""
    
    root = Path("/home/ubuntu/biomapper")
    pain_points = []
    
    # Check 1: Circular dependencies
    print("### Checking for circular dependencies ###")
    # This would need more sophisticated analysis
    
    # Check 2: Long import chains
    print("\n### Checking for long import chains ###")
    for py_file in root.rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        try:
            content = py_file.read_text()
            for line in content.splitlines():
                if line.startswith("from ") and line.count(".") > 4:
                    pain_points.append(f"Long import chain: {line[:80]} in {py_file.name}")
                    print(f"  - {line[:80]}...")
        except:
            pass
    
    # Check 3: Scattered related functionality
    print("\n### Checking for scattered functionality ###")
    
    # Find all files with "transform" in name across different locations
    transform_files = list(root.rglob("*transform*.py"))
    if len(transform_files) > 3:
        locations = set(f.parent for f in transform_files)
        if len(locations) > 2:
            pain_points.append(f"Transform logic scattered across {len(locations)} directories")
            print(f"  - Transform files in {len(locations)} different directories")
    
    # Check 4: Strategies far from actions
    strategies_path = root / "configs" / "strategies"
    actions_path = root / "biomapper" / "core" / "strategy_actions"
    
    if strategies_path.exists() and actions_path.exists():
        # Calculate relative path distance
        try:
            rel_path = os.path.relpath(actions_path, strategies_path)
            depth = rel_path.count('..')
            if depth > 2:
                pain_points.append(f"Strategies {depth} levels away from actions")
                print(f"\n  - Strategies are {depth} directory levels from actions")
        except:
            pass
    
    # Check 5: Inconsistent patterns
    print("\n### Checking for pattern inconsistencies ###")
    
    # Check for mixed async/sync patterns
    async_files = []
    sync_files = []
    
    for py_file in (root / "biomapper").rglob("*.py"):
        if "__pycache__" in str(py_file):
            continue
        try:
            content = py_file.read_text()
            if "async def" in content:
                async_files.append(py_file.name)
            elif "def execute" in content:
                sync_files.append(py_file.name)
        except:
            pass
    
    if async_files and sync_files:
        print(f"  - Mixed async ({len(async_files)}) and sync ({len(sync_files)}) execution patterns")
        pain_points.append("Mixed async/sync patterns")
    
    return pain_points

if __name__ == "__main__":
    pain_points = identify_pain_points()
    
    print("\n" + "=" * 70)
    print(f"IDENTIFIED {len(pain_points)} ARCHITECTURAL PAIN POINTS")
    print("=" * 70)
    for i, point in enumerate(pain_points, 1):
        print(f"{i}. {point}")
EOF

python /tmp/identify_pain_points.py
```

## Proposed Architecture Options

### Option A: Monorepo with Clear Boundaries

```
biomapper/
├── core/                      # Core domain logic
│   ├── actions/              # All actions in one place
│   │   ├── base.py          # Base action classes
│   │   ├── proteins/        # Protein-specific actions
│   │   ├── metabolites/     # Metabolite actions
│   │   ├── chemistry/       # Chemistry actions
│   │   └── registry.py      # Action registry
│   ├── strategies/          # Strategy definitions WITH their YAML
│   │   ├── base.py         # Base strategy classes
│   │   ├── proteins/       # Protein strategies
│   │   │   ├── __init__.py
│   │   │   └── arivale_to_kg2c.yaml
│   │   └── loader.py       # Strategy loader
│   ├── models/             # Shared data models
│   └── utils/              # Shared utilities
├── api/                    # API layer (thin)
│   ├── server.py          # FastAPI app
│   ├── routes/            # API routes
│   └── dependencies.py    # DI configuration
├── client/                # Client library
│   └── biomapper.py       # Simple client
├── tests/                 # All tests
└── docs/                  # Documentation
```

**Pros:**
- Strategies and actions co-located
- Clear dependency direction (api → core ← client)
- Easier to understand relationships
- Single package to maintain

**Cons:**
- Large monolithic package
- Need to refactor imports
- Breaking change for users

### Option B: Plugin Architecture

```
biomapper/
├── biomapper-core/           # Minimal core
│   ├── engine/              # Execution engine
│   ├── registry/            # Plugin registry
│   └── interfaces/          # Plugin interfaces
├── biomapper-plugins/        # Plugins directory
│   ├── proteins/           # Protein plugin
│   │   ├── actions/        # Protein actions
│   │   ├── strategies/     # Protein strategies
│   │   └── plugin.yaml     # Plugin manifest
│   ├── metabolites/        # Metabolite plugin
│   └── chemistry/          # Chemistry plugin
├── biomapper-api/           # API server
└── biomapper-cli/           # CLI client
```

**Pros:**
- Highly modular
- Easy to add new entity types
- Can version plugins independently
- Clear separation of concerns

**Cons:**
- More complex setup
- Plugin discovery overhead
- Need plugin management system

### Option C: Domain-Driven Design

```
biomapper/
├── domains/                  # Domain modules
│   ├── proteins/
│   │   ├── actions/         # Protein actions
│   │   ├── strategies/      # Protein strategies
│   │   ├── models/          # Protein models
│   │   └── services/        # Protein services
│   ├── metabolites/
│   ├── chemistry/
│   └── shared/              # Shared domain logic
├── application/             # Application layer
│   ├── api/                # REST API
│   ├── cli/                # CLI interface
│   └── workers/            # Background workers
├── infrastructure/         # Infrastructure layer
│   ├── database/          # Database access
│   ├── cache/             # Caching
│   └── external/          # External services
└── tests/
```

**Pros:**
- Clear domain boundaries
- Follows DDD principles
- Scalable architecture
- Easy to understand domains

**Cons:**
- May be overengineered
- Learning curve for DDD
- More directories to navigate

## Migration Plan Template

### Phase 1: Preparation (Week 1)
1. Create feature branch
2. Set up parallel structure
3. Write migration scripts
4. Update CI/CD for new structure

### Phase 2: Core Migration (Week 2)
1. Move and refactor core modules
2. Update imports
3. Ensure tests pass
4. Update documentation

### Phase 3: API/Client Migration (Week 3)
1. Migrate API to new structure
2. Update client library
3. Test end-to-end workflows
4. Performance testing

### Phase 4: Cleanup (Week 4)
1. Remove old structure
2. Update all documentation
3. Update developer guides
4. Team training

## Evaluation Criteria

Rate each architecture option (1-5 scale):

| Criteria | Weight | Option A | Option B | Option C |
|----------|--------|----------|----------|----------|
| Simplicity | 25% | 4 | 2 | 3 |
| Modularity | 20% | 3 | 5 | 4 |
| Maintainability | 20% | 4 | 3 | 4 |
| Scalability | 15% | 3 | 5 | 5 |
| Migration Effort | 10% | 4 | 2 | 2 |
| Learning Curve | 10% | 5 | 3 | 2 |
| **Total Score** | | **3.7** | **3.4** | **3.5** |

## Recommendation Framework

Based on analysis, recommend architecture based on:

### If simplicity is priority → Option A (Monorepo)
- Best for: Small team, rapid development
- Migration effort: Low-Medium
- Long-term benefit: Medium

### If extensibility is priority → Option B (Plugins)
- Best for: Community contributions, multiple teams
- Migration effort: High
- Long-term benefit: High

### If scalability is priority → Option C (DDD)
- Best for: Large team, complex domain
- Migration effort: High  
- Long-term benefit: High

## Specific Recommendations for Biomapper

Based on current state analysis, recommend:

### Immediate Changes (Low Risk)

1. **Co-locate strategies with actions**
   ```bash
   # Move experimental strategies to action directories
   mv configs/strategies/experimental/*protein*.yaml \
      biomapper/core/strategy_actions/entities/proteins/strategies/
   ```

2. **Consolidate utility functions**
   ```bash
   # Create central utilities module
   mkdir -p biomapper/core/utils
   # Move scattered utilities there
   ```

3. **Flatten deep hierarchies**
   - Reduce directory depth where possible
   - Max 4 levels deep for any module

### Medium-term Changes (Medium Risk)

1. **Merge biomapper-api into biomapper**
   - Keep as separate module within biomapper
   - Simplifies deployment and testing

2. **Create domain modules**
   - Group related functionality by domain
   - Proteins, metabolites, chemistry as top-level domains

3. **Standardize patterns**
   - All actions use async/await
   - All strategies use same parameter pattern
   - Consistent error handling

### Long-term Vision (High Risk/Reward)

1. **Implement plugin architecture**
   - Core engine with pluggable domains
   - Each entity type as plugin
   - Dynamic loading of strategies

2. **API-first redesign**
   - GraphQL API for flexibility
   - Event-driven architecture
   - Microservices-ready

## Success Criteria

1. ✅ Complete architecture analysis documented
2. ✅ Pain points clearly identified
3. ✅ At least 3 architecture options proposed
4. ✅ Migration plan outlined
5. ✅ Recommendations prioritized by risk/reward
6. ✅ Specific next steps identified

## Deliverables

1. Architecture analysis report (`/tmp/architecture_analysis.json`)
2. Pain points list with specific examples
3. Proposed architecture diagrams (ASCII or Mermaid)
4. Migration plan with timelines
5. Risk assessment matrix
6. Recommendation document with rationale

## Time Estimate

- Current architecture analysis: 1.5 hours
- Pain point identification: 1 hour
- Architecture options design: 2 hours
- Migration planning: 1 hour
- Documentation: 1.5 hours
- **Total: 7 hours**

## Questions to Answer

1. **Should strategies live with their actions?**
   - Current: Separated by 4+ directories
   - Proposed: Co-located in domain modules
   - Impact: Easier to understand relationships

2. **Can we consolidate the three packages?**
   - Current: biomapper, biomapper-api, biomapper_client
   - Proposed: Single package with clear modules
   - Impact: Simpler deployment, fewer dependencies

3. **Should we use a plugin architecture?**
   - Current: Monolithic with registry
   - Proposed: Core + plugins
   - Impact: More flexible but more complex

4. **What's the right level of abstraction?**
   - Current: Mixed levels of abstraction
   - Proposed: Clear layers (domain, application, infrastructure)
   - Impact: Better testability and maintainability

## Notes

- Consider gradual migration over big bang
- Maintain backward compatibility where possible
- Get team buy-in before major changes
- Consider creating POC for risky changes
- Document all architectural decisions (ADRs)