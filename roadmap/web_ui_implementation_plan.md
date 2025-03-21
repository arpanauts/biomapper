# Biomapper Web UI Implementation Plan

This document outlines the plan for developing a web-based user interface for the Biomapper biological data harmonization and ontology mapping toolkit.

## 1. Architecture Overview

```
+-----------------------+      +-------------------------+      +----------------------+
|                       |      |                         |      |                      |
|  Frontend (Web UI)    |<---->|  Backend API Service    |<---->|  Biomapper Library   |
|                       |      |                         |      |                      |
+-----------------------+      +-------------------------+      +----------------------+
                                          |                              |
                                          v                              v
                               +----------------------+      +----------------------+
                               |                      |      |                      |
                               |  SQL Mapping Cache   |      |  Knowledge Graphs    |
                               |  (SQLite/PostgreSQL) |      |  (SPOKE & Extension) |
                               |                      |      |                      |
                               +----------------------+      +----------------------+
```

The architecture leverages the existing hybrid design with:
- SPOKE Knowledge Graph (ArangoDB) as the primary source of biological relationships
- A custom Extension Graph (also ArangoDB) to fill gaps in SPOKE's coverage
- A Unified Ontology Layer to coordinate between both graphs
- A SQL-based Mapping Cache (SQLite/PostgreSQL) to optimize performance

## 2. Technology Stack

### Backend:
- **FastAPI**: A modern, fast web framework for building APIs with Python
- **Pydantic**: For data validation and settings management
- **Uvicorn/Gunicorn**: ASGI server for production deployment
- **SQLAlchemy**: For the SQL mapping cache component
- **ArangoDB Client**: For interaction with the SPOKE and Extension knowledge graphs
- **Biomapper Library**: Core mapping functionality

### Frontend:
- **React**: For building the user interface
- **TypeScript**: For type safety
- **Tailwind CSS**: For styling
- **Chart.js/D3.js**: For data visualization
- **React Query**: For API data fetching and caching

## 3. Core Features

1. **Metabolite Mapping Interface**
   - Upload compounds list (CSV/TST format)
   - Paste compound names directly
   - Map individual compounds interactively
   - View and export mapping results

2. **RAG & LLM-Powered Mapping**
   - Interface for AI-powered mapping
   - Configuration of RAG parameters
   - Prompt customization options
   - Confidence thresholds adjustment

3. **Pathway Analysis with SPOKE**
   - Visualize pathway connections
   - Explore compound relationships
   - Pathway enrichment analysis
   - Knowledge graph navigation

4. **Results Dashboard**
   - Mapping statistics
   - Success/failure rates
   - Confidence distribution
   - Interactive filtering and sorting

5. **Configuration Management**
   - API key management (OpenAI, etc.)
   - Database connection settings
   - Model preferences (embedding models, LLMs)
   - Cache configuration

## 4. Implementation Plan

### Phase 1: Core API Development (3-4 weeks)
1. Set up FastAPI project structure
2. Create RESTful API endpoints for Biomapper functionality
3. Implement authentication and rate limiting
4. Connect to the existing Biomapper library
5. Develop basic data validation and error handling
6. Set up SQLite for local development (migrate to PostgreSQL later)

### Phase 2: Frontend Development (4-5 weeks)
1. Set up React application structure with TypeScript
2. Develop UI components and layouts
3. Implement forms for data input and configuration
4. Create results visualization components
5. Implement authentication UI
6. Connect to backend APIs

### Phase 3: Advanced Features (3-4 weeks)
1. Implement interactive graph visualization for pathways
2. Add batch processing capability
3. Develop user settings and preferences storage
4. Create administrative interface for system monitoring
5. Implement export functionality for various formats

### Phase 4: Testing, Documentation & Deployment (2-3 weeks)
1. Write unit and integration tests
2. Develop user documentation
3. Set up CI/CD pipeline
4. Deploy to production environment
5. Monitor and fix issues

## 5. API Endpoints Design

```
# Authentication
POST   /api/auth/login
POST   /api/auth/logout

# Compound Mapping
POST   /api/mapping/single         # Map a single compound
POST   /api/mapping/batch          # Map multiple compounds
POST   /api/mapping/file           # Upload and map from file

# RAG & LLM
POST   /api/rag/map                # RAG-based mapping
POST   /api/llm/analyze            # LLM analysis of results

# SPOKE Integration
GET    /api/spoke/entity/{id}      # Get SPOKE entity details
POST   /api/spoke/pathways         # Analyze pathways for compounds
GET    /api/spoke/graph/{query}    # Get subgraph for visualization

# Configuration
GET    /api/config                 # Get user configuration
PUT    /api/config                 # Update configuration
```

## 6. Frontend UI Structure

1. **Landing Page / Dashboard**
   - Summary of recent mappings
   - Quick mapping form
   - System status

2. **Mapping Interface**
   - Input options (file upload, paste, single input)
   - Configuration panel
   - Mapping execution controls

3. **Results View**
   - Table of mapping results
   - Filtering and sorting options
   - Export functionality
   - Confidence visualization

4. **Pathway Explorer**
   - Interactive graph visualization
   - Pathway details panel
   - Entity information sidebar

5. **Settings**
   - API keys management
   - Database configuration
   - Model selection
   - UI preferences

## 7. Development Considerations

1. **Asynchronous Processing**
   - Implement queue for long-running tasks
   - Use WebSockets for real-time updates
   - Consider using Celery for task queue management

2. **Data Security**
   - Implement proper authentication and authorization
   - Secure API keys storage
   - Consider data encryption for sensitive information

3. **Scalability**
   - Design for horizontal scaling
   - Implement caching strategies
   - Consider containerization with Docker

4. **User Experience**
   - Focus on intuitive workflow
   - Provide helpful tooltips and guidance
   - Implement progressive disclosure of complex features

## 8. Next Steps

For immediate development:

1. Set up a basic FastAPI backend to expose core Biomapper functionality
2. Develop a simple React frontend for compound mapping
3. Implement file upload and basic results visualization
4. Create a proof-of-concept for the pathway visualization component
