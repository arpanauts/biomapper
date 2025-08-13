# Biomapper Architecture Roadmap: Pragmatic Evolution Strategy

## Executive Summary

This roadmap balances immediate research productivity with long-term architectural improvements. The biomapper system is **currently working** with all 26 actions registered and strategies executing successfully. Our priority is maintaining this functionality while gradually improving the architecture.

**Core Principle**: Working code delivering results > Perfect architecture

## Current System Status

### What's Working ✅
- **26 actions registered** and executing
- **Strategies loading** and running via API
- **Variable substitution fixed** with ParameterResolver
- **Chemistry actions implemented** (all 4)
- **Google Drive sync complete** (28/28 tests passing)
- **End-to-end pipeline functional**

### Technical Metrics
- **Codebase**: 463 Python files, ~50,000 lines
- **Technical Debt**: 309 linting issues (non-critical)
- **Data**: 6.1GB HMDB files, 7.3GB total
- **Database**: SQLite (sufficient for current scale)
- **Performance**: In-memory processing (working for current datasets)

### Architectural Issues (Not Breaking Production)
- **Global ACTION_REGISTRY**: Anti-pattern but functional
- **Shared dictionary context**: Creates coupling but works
- **SQLite limitations**: Will hit ceiling at ~100 concurrent users
- **In-memory processing**: Will fail at >10GB datasets

## Phased Roadmap

### 🚀 Phase 0: IMMEDIATE FIXES (Week 1)
**Priority: Fix what's actually broken**

#### Required Actions
1. ✅ **Variable substitution** (COMPLETED)
2. ✅ **CUSTOM_TRANSFORM action** (COMPLETED)
3. ✅ **Chemistry actions** (COMPLETED)
4. ✅ **Strategy name alignment** (COMPLETED)

**Status**: ✅ ALL CRITICAL FIXES COMPLETE

---

### 📊 Phase 1: NON-BREAKING IMPROVEMENTS (Weeks 2-4)
**Priority: Add monitoring and tooling without touching working code**

#### 1.1 Enhanced Monitoring (Week 2)
```python
# Add alongside existing code - doesn't change anything
class ExecutionMonitor:
    """Monitor pipeline execution without modifying it."""
    
    def __init__(self):
        self.metrics = {}
        self.start_times = {}
    
    def track_action(self, action_name: str, duration: float, success: bool):
        """Track action execution metrics."""
        if action_name not in self.metrics:
            self.metrics[action_name] = {
                'count': 0,
                'success': 0,
                'avg_duration': 0
            }
        # Update metrics without affecting execution

# Use in MinimalStrategyService without changing core logic
monitor = ExecutionMonitor()
# Existing code continues unchanged
```

**Risk**: NONE - Pure observation, no functional changes

#### 1.2 Data Management with DVC (Week 3)
```bash
# Setup DVC for large files without moving them
pip install dvc[s3]
dvc init
dvc add data/hmdb_metabolites.xml  # Track but don't move
dvc add data/hmdb_metabolites.zip
git add data/*.dvc .dvcignore
```

**Risk**: MINIMAL - Only adds tracking, doesn't move files

#### 1.3 Pre-commit Hooks (Week 3)
```yaml
# .pre-commit-config.yaml - prevents NEW issues only
repos:
  - repo: https://github.com/charliermarsh/ruff-pre-commit
    rev: v0.1.0
    hooks:
      - id: ruff
        args: [--fix, --exit-zero]  # Don't fail on existing issues
```

**Risk**: NONE - Only affects new commits

#### 1.4 Parallel Type Safety (Week 4)
```python
# Add typed version alongside dictionary context
from typing import TypedDict

class TypedContext(TypedDict, total=False):
    """Typed context that coexists with dict context."""
    datasets: Dict[str, pd.DataFrame]
    output_files: Dict[str, str]
    statistics: Dict[str, Any]

# Actions can use either dict or TypedContext
def execute(self, params, context: Union[Dict, TypedContext]):
    # Works with both old and new
```

**Risk**: LOW - Backward compatible addition

---

### 🔧 Phase 2: COEXISTENCE ARCHITECTURE (Month 2)
**Priority: Build new systems alongside old ones**

#### 2.1 Plugin Registry (Alongside Global Registry)
```python
# New plugin system that coexists with global ACTION_REGISTRY
class PluginRegistry:
    """New registry that doesn't break the old one."""
    
    def __init__(self, fallback_to_global=True):
        self.local_actions = {}
        self.fallback = fallback_to_global
    
    def get_action(self, name: str):
        # Try new registry first
        if name in self.local_actions:
            return self.local_actions[name]
        # Fall back to global if enabled
        if self.fallback:
            from biomapper.core.strategy_actions.registry import ACTION_REGISTRY
            return ACTION_REGISTRY.get(name)
        return None

# Gradual migration - both systems work
new_registry = PluginRegistry(fallback_to_global=True)
```

**Risk**: LOW - Fallback ensures nothing breaks

#### 2.2 Immutable Context Wrapper
```python
# Wrap existing context without changing it
from dataclasses import dataclass
from typing import Any

@dataclass(frozen=True)
class ImmutableContextView:
    """Read-only view of context - doesn't change existing code."""
    _context: Dict[str, Any]
    
    def get_dataset(self, key: str):
        return self._context.get('datasets', {}).get(key)
    
    def get_output_file(self, key: str):
        return self._context.get('output_files', {}).get(key)

# Use in new actions, old actions unchanged
```

**Risk**: LOW - Additive only, old code unchanged

#### 2.3 Connection Pool for SQLite
```python
# Add connection pooling without changing queries
from sqlalchemy.pool import QueuePool

# Enhanced connection that falls back to direct connection
def get_db_connection():
    try:
        # Try pooled connection
        return pool.connect()
    except:
        # Fall back to direct connection
        return sqlite3.connect('biomapper.db')
```

**Risk**: LOW - Graceful fallback

---

### 🏗️ Phase 3: DEFERRED ARCHITECTURE (Month 3+)
**Priority: Major changes AFTER research results**

⚠️ **DO NOT START UNTIL**:
- Research results are obtained
- Current pipeline has delivered value
- Team has bandwidth for major changes

#### 3.1 Domain Reorganization (3-6 months)
```
# DEFERRED - Current structure works
biomapper/
├── domains/          # Future structure
│   ├── proteins/
│   ├── metabolites/
│   └── chemistry/
```

**When to implement**: After 6 months of stable production

#### 3.2 Database Migration (6 months)
```python
# DEFERRED - SQLite works for current scale
# PostgreSQL migration only when:
# - Concurrent users > 50
# - Data size > 100GB
# - Team has DBA support
```

**Trigger**: Only when SQLite becomes actual bottleneck

#### 3.3 Distributed Processing (9 months)
```python
# DEFERRED - Current in-memory works
# Dask/Ray only when:
# - Single datasets > 10GB
# - Processing time > 2 hours
# - Have DevOps support
```

**Trigger**: Only when memory becomes actual constraint

---

## Risk Mitigation Strategy

### Coexistence Principle
Every architectural improvement runs **alongside** the existing system:

```python
# Pattern for all improvements
class NewSystem:
    def __init__(self, use_legacy=True):
        self.legacy_fallback = use_legacy
    
    def execute(self):
        try:
            # Try new approach
            return self.new_implementation()
        except:
            if self.legacy_fallback:
                # Fall back to working system
                return self.legacy_implementation()
            raise
```

### Rollback Strategy
Every change must be reversible:

1. **Feature flags** for new systems
2. **Git branches** for each phase
3. **Database backups** before migrations
4. **Parallel environments** for testing

### Testing Requirements
Before any architectural change:

```python
# Minimum test coverage for changes
def validate_change():
    # All 26 actions still register ✓
    assert len(ACTION_REGISTRY) >= 26
    
    # All strategies still execute ✓
    for strategy in get_all_strategies():
        assert can_execute(strategy)
    
    # API endpoints still work ✓
    assert api_health_check() == 200
    
    # No performance regression ✓
    assert execution_time < baseline * 1.1
```

---

## Implementation Priorities

### Do Now (Non-Breaking) ✅
1. Monitoring and observability
2. Data version control (DVC)
3. Pre-commit hooks
4. Type hints (gradual)
5. Documentation
6. Test coverage

### Do Later (Potentially Breaking) ⏳
1. Global registry refactoring
2. Context dictionary replacement
3. Database migration
4. Directory reorganization
5. Microservices split
6. Distributed processing

### Never Do (Over-Engineering) ❌
1. Complete rewrite
2. Premature optimization
3. Technology for technology's sake
4. Breaking changes without clear ROI
5. Architecture astronauting

---

## Success Metrics

### Phase 1 Success (1 month)
- [ ] Zero disruption to research pipeline
- [ ] Monitoring dashboard operational
- [ ] DVC managing large files
- [ ] Pre-commit preventing new issues

### Phase 2 Success (2 months)
- [ ] Plugin registry coexisting with global
- [ ] Type safety improving gradually
- [ ] Performance metrics collected
- [ ] Connection pooling reducing timeouts

### Phase 3 Success (6+ months)
- [ ] Clear trigger points identified
- [ ] Migration plan documented
- [ ] Team trained on new architecture
- [ ] Gradual transition started

---

## Communication Plan

### Weekly Updates
```markdown
## Architecture Progress - Week X

### Changes Made
- [Non-breaking improvement]

### System Status
- Pipeline: ✅ Working
- Performance: → No change
- Reliability: ↑ Improved

### Next Week
- [Another non-breaking improvement]
```

### Stakeholder Messaging
- **To Researchers**: "The pipeline continues working while we improve it"
- **To Management**: "Technical debt addressed without disrupting productivity"
- **To Team**: "Gradual improvements with safety nets"

---

## Decision Matrix

| Change | Impact | Risk | Priority | When |
|--------|--------|------|----------|------|
| Monitoring | High | None | NOW | Week 1 |
| DVC | Medium | Low | NOW | Week 2 |
| Type hints | Medium | None | NOW | Week 3 |
| Plugin registry | High | Low | SOON | Month 2 |
| Domain reorg | Medium | High | LATER | Month 6+ |
| PostgreSQL | Low | High | MAYBE | When needed |
| Microservices | Low | Very High | MAYBE | Year 2+ |

---

## Anti-Patterns to Avoid

### ❌ Don't Do This
```python
# Breaking change without fallback
ACTION_REGISTRY = {}  # DON'T clear the working registry!

# All-or-nothing migration
shutil.rmtree('biomapper/core')  # DON'T delete working code!

# Untested architectural change
context = ImmutableContext()  # DON'T replace without coexistence!
```

### ✅ Do This Instead
```python
# Gradual migration with fallback
new_registry = PluginRegistry(fallback_to_global=True)

# Parallel structure during transition
# Keep both old and new paths working

# Coexistence before replacement
context = context if not USE_IMMUTABLE else ImmutableContextView(context)
```

---

## Final Recommendations

### Immediate Actions (This Week)
1. **Set up monitoring** - Understand what you have
2. **Document pain points** - Know what actually needs fixing
3. **Establish baselines** - Measure before improving

### Short Term (This Month)
1. **Add observability** without changing functionality
2. **Improve tooling** for development efficiency
3. **Increase test coverage** for safety net

### Medium Term (3 Months)
1. **Evaluate Phase 2** based on actual needs
2. **Build coexistence systems** if beneficial
3. **Gather metrics** for Phase 3 decisions

### Long Term (6+ Months)
1. **Reassess architecture** based on actual usage
2. **Implement only proven needs** not theoretical ones
3. **Maintain backward compatibility** throughout

---

## Conclusion

This roadmap prioritizes **working software delivering research results** over architectural perfection. Every proposed change:

1. **Preserves current functionality**
2. **Provides fallback mechanisms**
3. **Can be implemented incrementally**
4. **Has clear success metrics**
5. **Can be deferred or cancelled**

The biomapper system is **currently functional and delivering value**. This roadmap ensures it continues to do so while gradually evolving toward a more scalable architecture.

**Remember**: The best architecture is the one that delivers results to researchers, not the one that wins design awards.