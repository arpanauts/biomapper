# Biomapper Project Roadmap

This directory contains implementation plans and roadmaps for the various components of the Biomapper toolkit. The roadmap is organized into functional areas to provide clear direction for development efforts.

## Directory Structure

- **architecture/** - System architecture documents and cross-cutting concerns
- **core/** - Core functionality implementation plans
- **api/** - API and service layer implementation plans
- **ui/** - User interface implementation plans

## Current Implementation Status

### In Progress

- **SQLite Mapping Cache** - A high-performance local cache for biological entity mappings
  - Schema implementation ✓
  - Cache manager ✓
  - Transitivity builder ✓
  - Command-line interface ✓
  - Cache-aware mapper ✓
  - Database maintenance ✓
  - Monitoring module ✓
  - SPOKE integration ⚠️ (In progress)

### Upcoming Work

- **Resource Metadata System** - Intelligent orchestration of mapping resources
  - Schema extensions for resource metadata
  - Resource registration mechanism
  - Mapping dispatcher with smart routing
  - Performance tracking and optimization

- **Web UI MVP** - Basic web interface for CSV mapping capabilities
  - FastAPI backend
  - File upload and processing
  - Mapping configuration interface
  - Results download

## Long-term Vision

Biomapper aims to become a comprehensive toolkit for biological data harmonization, supporting seamless translation between different biological ontologies and datasets through a hybrid architecture leveraging:

1. SPOKE Knowledge Graph (ArangoDB)
2. Extension Graph for custom ontologies
3. SQLite Mapping Cache for performance
4. Resource metadata system for intelligent orchestration

## Implementation Timeline

| Component | Status | Target Completion |
|-----------|--------|-------------------|
| SQLite Mapping Cache | 90% Complete | Q1 2025 |
| Resource Metadata System | Planning | Q2 2025 |
| Web UI MVP | Planning | Q2 2025 |
| UKBB Dataset Integration | Not Started | Q3 2025 |
| Arivale Dataset Integration | Not Started | Q3 2025 |
