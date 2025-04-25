# UMLS Terminology Services (UTS) REST API

## Overview

The Unified Medical Language System (UMLS) integrates and distributes key terminology, classification and coding standards, and associated resources to promote creation of more effective and interoperable biomedical information systems and services. The UMLS Terminology Services (UTS) provide RESTful API access to the UMLS Metathesaurus.

Biomapper utilizes the UTS API primarily to map biomedical terms (e.g., disease names, chemical names, concepts) to Concept Unique Identifiers (CUIs).

**Requirement:** Access requires a UMLS Metathesaurus License and a UTS account with an API key.

**Base URL:** `https://uts-ws.nlm.nih.gov/rest`

**Official Documentation:** [https://documentation.uts.nlm.nih.gov/rest/home.html](https://documentation.uts.nlm.nih.gov/rest/home.html)

## Authentication

The UTS API uses a ticket-based authentication system:

1.  **API Key:** Obtain an API key from your UTS profile.
2.  **Ticket-Granting Ticket (TGT):** Authenticate using your API key against the CAS authentication endpoint (`https://utslogin.nlm.nih.gov/cas/v1/api-key`) to receive a TGT. TGTs typically expire after 8 hours.
3.  **Service Ticket (ST):** For each API request, obtain a single-use Service Ticket by presenting your valid TGT to the authentication endpoint.

The `biomapper.mapping.clients.umls_client.UMLSClient` attempts to handle this authentication flow, but requires a valid API key provided in its configuration.

**Reference:** [https://documentation.uts.nlm.nih.gov/rest/authentication.html](https://documentation.uts.nlm.nih.gov/rest/authentication.html)

## Endpoints Used by Biomapper

### 1. Search (`/search/{version}`)

*   **Biomapper Client:** `biomapper.mapping.clients.umls_client.UMLSClient`
*   **Resource Name:** `UMLS_Metathesaurus` (Example, confirm actual name in `metamapper.db`)
*   **Purpose:** Searches the Metathesaurus for terms to find matching CUIs and related information.
*   **Method:** Synchronous GET requests, requiring a valid Service Ticket.
*   **Key Parameters:**
    *   `string`: The term to search for.
    *   `inputType`: The type of the input term (e.g., `string`, `sourceConcept`). Defaults to `string`.
    *   `searchType`: The type of search (e.g., `exact`, `words`, `leftTruncation`). Defaults to `words`.
    *   `resultType`: The type of identifier to return (e.g., `CUI`, `sourceConcept`). Defaults to `CUI`.
    *   `pageSize`: Number of results per page.
    *   `ticket`: The single-use Service Ticket obtained via authentication.
*   **Reference:** [https://documentation.uts.nlm.nih.gov/rest/search/index.html](https://documentation.uts.nlm.nih.gov/rest/search/index.html)

### Other Potential Endpoints (Not yet implemented in Biomapper client)

The UTS API provides many other endpoints for retrieving detailed information about CUIs, atoms, definitions, relationships, source concepts, semantic types, etc., as listed [here](https://documentation.uts.nlm.nih.gov/rest/home.html). These could be added to the `UMLSClient` if needed for more advanced mapping tasks.
