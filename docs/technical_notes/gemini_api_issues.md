# Gemini API Integration Issues - Technical Notes

## Overview
We've been experiencing persistent 500 Internal Server Error responses from the Gemini API endpoint (`https://us-west1-ph-dev-338002.cloudfunctions.net/ph-core-gemini`) during our compound mapping implementation. This document outlines our findings and troubleshooting efforts.

## What Works
- Basic API connectivity (endpoint is reachable)
- API key authentication appears functional (no auth errors)
- Simple, short prompts occasionally succeed

## What Doesn't Work
- Complex prompts consistently fail with 500 errors
- Multiple compound ranking requests
- Long-running batch processing of compounds
- Requests with detailed chemical descriptions

## Troubleshooting Steps Taken

### 1. Prompt Engineering
- Simplified prompts from multi-step to single-step queries
- Reduced prompt complexity and length
- Standardized response format requirements
- Removed chemical structure details from prompts

### 2. Request Optimization
- Implemented exponential backoff for retries
- Added delays between API calls (2 seconds)
- Reduced batch sizes
- Simplified JSON payload structure

### 3. Error Handling
- Added comprehensive error logging
- Implemented fallback to vector similarity scores
- Added request/response debugging information
- Tracked API call patterns and failure rates

## Current Implementation
```python
ranking_prompt = f"""Which compound is most chemically similar to '{compound.name}'?

Candidates:
{chr(10).join(candidates_brief)}

Respond with just the number of the most similar compound, e.g. if compound #3 is most similar, respond with: 3"""
```

## Error Details
```
500 Internal Server Error: The server encountered an internal error and was unable to complete your request. Either the server is overloaded or there is an error in the application.
```

## Impact
- Unable to reliably use Gemini API for compound mapping
- Forced to fall back to vector similarity scores
- Reduced accuracy in compound matching
- Increased processing time due to retry attempts

## System Information
- Python Version: 3.10+
- Dependencies: requests, backoff
- Environment: Production
- Timestamp of Latest Test: 2025-02-15 23:22:08 UTC

## Recommendations
1. **API Endpoint Investigation**
   - Check server logs for error patterns
   - Verify if there are request size limits
   - Investigate potential rate limiting issues
   - Consider load balancing if server overload is the issue

2. **Alternative Solutions**
   - Consider implementing a queue system for API requests
   - Add circuit breaker pattern to prevent cascading failures
   - Explore alternative LLM APIs (OpenAI, Claude, PaLM)
   - Enhance vector similarity-based matching as primary solution

## Questions for API Team
1. Are there known limitations on prompt size or complexity?
2. What is the recommended rate limiting for the endpoint?
3. Are there specific prompt formats that are known to work better?
4. Is there a more stable endpoint available for production use?

## Additional Context
The API is being used as part of a larger compound mapping system that combines:
- Vector similarity search (ChromaDB)
- Sentence transformers for embeddings
- Confidence scoring mechanisms
- Fallback strategies

The system processes hundreds of compounds in batch, requiring reliable API performance for production use.
