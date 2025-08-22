# Biomapper External Integrations

This directory contains documentation for integrating biomapper with external services and databases.

## Current Integrations

### LIPID MAPS
- **[LIPID_MAPS_STATIC_APPROACH.md](LIPID_MAPS_STATIC_APPROACH.md)**
  - Static file-based matching approach
  - Performance optimizations
  - Data structure and format
  - Implementation details

## Integration Categories

### Database Integrations
- **LIPID MAPS** - Lipid identifier mapping
- **HMDB** - Human Metabolome Database (via API and vector search)
- **UniProt** - Protein sequence and annotation
- **ChEMBL** - Bioactive molecules database
- **KEGG** - Kyoto Encyclopedia of Genes and Genomes

### API Services
- **Chemical Translation Service (CTS)** - Identifier conversion
- **RaMP-DB** - Metabolite and pathway database
- **Nightingale Health** - NMR metabolomics reference

### Cloud Services
- **Google Drive** - Result storage and sharing
- **Qdrant** - Vector database for semantic search

## Integration Patterns

### Static File Integration
Best for:
- Stable reference data
- Offline processing
- High-performance requirements

Example: LIPID MAPS static approach

### API Integration
Best for:
- Real-time data access
- Always up-to-date information
- Small to medium query volumes

Example: CTS API calls

### Hybrid Approach
Best for:
- Balancing performance and freshness
- Fallback mechanisms
- Caching strategies

Example: HMDB with local cache + API fallback

## Implementation Guidelines

### Adding New Integrations

1. **Evaluate Integration Method**
   - Static files for stable data
   - APIs for dynamic data
   - Consider rate limits and quotas

2. **Create Action Class**
   ```python
   @register_action("SERVICE_NAME_MATCH")
   class ServiceNameMatch(TypedStrategyAction):
       # Implementation
   ```

3. **Handle Errors Gracefully**
   - Network timeouts
   - Rate limiting
   - Data format changes

4. **Document Thoroughly**
   - API endpoints used
   - Data formats expected
   - Error conditions

## Configuration

### Environment Variables
Common integration settings:
```bash
# API Keys
export CHEMBL_API_KEY="..."
export UNIPROT_API_KEY="..."

# Service URLs
export CTS_BASE_URL="https://cts.fiehnlab.ucdavis.edu"
export RAMP_DB_URL="..."

# Timeouts and Limits
export API_TIMEOUT=30
export MAX_RETRIES=3
```

### Performance Tuning
- Batch API requests when possible
- Implement caching strategies
- Use connection pooling
- Set appropriate timeouts

## Troubleshooting

### Common Issues
1. **API Rate Limits** - Implement exponential backoff
2. **Network Timeouts** - Increase timeout values
3. **Data Format Changes** - Version lock or adapt parsers
4. **Authentication Failures** - Check credentials and expiry

## Future Integrations

Planned integrations:
- PubChem - Chemical compound database
- Reactome - Pathway database
- STRING - Protein interaction networks
- MetaboAnalyst - Metabolomics analysis

## Related Documentation

- [Guides](../guides/) - Setup guides for specific integrations
- [Workflows](../workflows/) - How integrations fit into pipelines
- [Reports](../reports/) - Feasibility studies and evaluations