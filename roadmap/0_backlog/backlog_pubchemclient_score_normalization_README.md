# Backlog: PubChemRAGMappingClient - Score Normalization Options

## 1. Overview

Qdrant can use different distance metrics (e.g., Cosine, Euclidean, Dot Product) for similarity search, and the raw scores have different interpretations (e.g., Cosine: 1.0 is best, Euclidean: 0.0 is best). While the `PubChemRAGMappingClient` now exposes these raw scores and includes interpretation metadata, it could be beneficial to offer built-in score normalization.

This task is to add options to the `PubChemRAGMappingClient` to normalize Qdrant similarity scores into a consistent range (e.g., 0.0 to 1.0, where 1.0 always indicates the best similarity), regardless of the underlying Qdrant distance metric.

## 2. Goal

*   Improve the usability and comparability of similarity scores for end-users.
*   Abstract away the complexities of interpreting scores from different distance metrics.
*   Provide clear documentation on the normalization methods used.

## 3. Scope

*   Research and define appropriate normalization formulas for common Qdrant distance metrics.
*   Implement normalization logic within the `PubChemRAGMappingClient`.
*   Add configuration options to enable/disable normalization and potentially select a normalization strategy.
*   Update Pydantic models if necessary to reflect normalized scores.
*   Update tests and documentation.

## 4. Potential Considerations

*   Ensuring the mathematical correctness of normalization.
*   How to handle scores when normalization might not be straightforward (e.g., for metrics without fixed bounds).
*   Impact on performance.
