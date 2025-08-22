# Biomapper Framework and Architecture Documentation

This directory contains architectural documentation and framework design patterns for biomapper.

## Core Frameworks

### BiOMapper Framework Triad
- **[BIOMAPPER_FRAMEWORK_TRIAD.md](BIOMAPPER_FRAMEWORK_TRIAD.md)**
  - Complete isolation architecture
  - Three-tier framework design
  - Separation of concerns principles
  - Component interaction patterns

### Surgical Framework
- **[SURGICAL_FRAMEWORK_GUIDE.md](SURGICAL_FRAMEWORK_GUIDE.md)**
  - Surgical precision in data processing
  - Error handling and recovery patterns
  - Targeted intervention strategies
  - Performance optimization techniques

## Framework Concepts

### Key Architectural Principles
1. **Isolation** - Components operate independently
2. **Modularity** - Plug-and-play action system
3. **Resilience** - Graceful error handling
4. **Scalability** - Handles large biological datasets

### Design Patterns Used
- **Registry Pattern** - Action registration and discovery
- **Strategy Pattern** - Configurable processing pipelines
- **Chain of Responsibility** - Multi-stage data processing
- **Observer Pattern** - Progress tracking and events

## Framework Components

### Core Services
- MinimalStrategyService - Lightweight strategy execution
- ContextAdapter - Universal context handling
- ActionRegistry - Dynamic action registration

### Supporting Infrastructure
- Parameter resolution
- Type safety with Pydantic
- Async execution support
- Progress tracking

## Implementation Guidelines

### When to Use Each Framework
- **Framework Triad**: For complete end-to-end pipelines
- **Surgical Framework**: For targeted data fixes and interventions

### Best Practices
1. Follow the standardized base classes
2. Use TypedStrategyAction for type safety
3. Implement proper error handling
4. Emit progress events for tracking

## Related Documentation

- [Guides](../guides/) - User and developer guides
- [Workflows](../workflows/) - Concrete implementations
- [Source Architecture](../source/architecture/) - Detailed technical docs