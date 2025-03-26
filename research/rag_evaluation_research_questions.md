# Research Questions: Measuring RAG Performance for Ontological Mapping

## Core Research Questions

1. **What constitutes appropriate baseline/null hypotheses for RAG-based ontological mapping?**
   - How do we define "chance performance" in ontological mapping tasks?
   - What simple heuristics (e.g., string matching, frequency-based mapping) should serve as minimum performance thresholds?
   - How should we account for the non-uniform distribution of entities across different biological ontologies?

2. **How do we establish ground truth for novel or complex biological entity mappings?**
   - What consensus methods can validate mappings that lack established references?
   - When expert opinions diverge, what resolution mechanisms are most effective?
   - How can we quantify uncertainty in "ground truth" mappings?

3. **What metrics best capture the biological relevance of RAG-based mappings?**
   - Do standard NLP metrics (precision, recall, F1) adequately capture biological accuracy?
   - How can ontological structure (hierarchy, relationships) be incorporated into evaluation metrics?
   - What weighted scoring systems best reflect the utility of mappings in downstream biological applications?

4. **How does RAG performance vary across different types of biological entities?**
   - Are there systematic differences in mapping performance between entity types (metabolites, genes, proteins, etc.)?
   - Which entity characteristics predict mapping difficulty?
   - How do we account for biological domain expertise embedded in different LLMs?

5. **What constitutes a hallucination in biological ontology mapping?**
   - How do we distinguish between creative but valid interpretations vs. hallucinations?
   - What is the appropriate tolerance for structural vs. semantic errors?
   - How do we measure the "biological plausibility" of a novel mapping?

## Methodology Questions

1. **Retrieval Component Evaluation**
   - What is the optimal retrieval corpus composition for biological ontology mapping?
   - How should retrieval evaluation differ for established vs. novel biological entities?
   - What embedding approaches best capture biological semantic similarity?
   - How do we measure the impact of retrieval depth and diversity on mapping quality?

2. **Generation Component Evaluation**
   - What prompt structures yield the most accurate ontological mappings?
   - How do we measure the quality of explanations/reasoning for mappings?
   - What is the relationship between generation confidence and mapping accuracy?
   - How should the evaluation handle "I don't know" or uncertain responses?

3. **Integrated System Evaluation**
   - How do we isolate and attribute errors to retrieval vs. generation components?
   - What ablation studies best reveal component contributions to overall performance?
   - How should end-to-end evaluation differ from component-level evaluation?
   - What is the appropriate trade-off between coverage and precision in ontological mapping?

## Comparative Benchmarking Questions

1. **Against Traditional Methods**
   - How does RAG compare to established database-driven approaches (string matching, etc.)?
   - What are the appropriate comparison metrics for deterministic vs. probabilistic approaches?
   - In what scenarios should RAG replace vs. augment traditional mapping approaches?
   - How do we quantify the "novelty advantage" of RAG approaches for previously unmapped entities?

2. **Against Other LLM Approaches**
   - What is the value-add of retrieval compared to pure LLM-based mapping?
   - How do different retrieval strategies affect mapping performance?
   - What prompt engineering approaches yield the greatest performance improvements?
   - How does model size interact with retrieval quality in determining mapping accuracy?

3. **Against Human Experts**
   - What is the appropriate protocol for expert evaluation of mappings?
   - How do we measure RAG performance against varying levels of human expertise?
   - What disagreement resolution methods best capture mapping quality?
   - How should time/efficiency be factored into human vs. RAG comparisons?

## Statistical Analysis Approaches

1. **Null Hypothesis Design**
   - H₀: RAG-based ontological mapping performs no better than random assignment
   - H₀: RAG-based mapping performs no better than simple string matching
   - H₀: Adding retrieval context does not improve mapping accuracy compared to pure LLM approaches
   - H₀: There is no difference in mapping performance across biological entity types

2. **Baseline Establishment**
   - Random mapping within ontology constraints (respecting type compatibility)
   - Naive Bayes classifier using token-level features
   - Term frequency-inverse document frequency (TF-IDF) with cosine similarity
   - Edit distance/Levenshtein distance for string similarity

3. **Significance Testing**
   - Paired t-tests for comparing RAG vs. baseline approaches on identical mapping tasks
   - McNemar's test for comparing binary success/failure outcomes
   - Permutation tests for evaluating retrieval component contribution
   - Bootstrap confidence intervals for performance metrics

## Data Requirements

1. **Gold Standard Development**
   - Minimum dataset size for statistical power
   - Stratified sampling across biological domains
   - Balance between common and rare entity types
   - Coverage of edge cases and ambiguous mappings

2. **Test Set Design**
   - Held-out evaluation set requirements
   - Cross-validation approaches for limited data scenarios
   - Generation of synthetic test cases
   - Time-based splitting to evaluate concept drift

## Practical Implementation

1. **Evaluation Frequency**
   - Continuous vs. milestone-based evaluation
   - Computational requirements for comprehensive evaluation
   - Real-time vs. batch evaluation approaches
   - Detecting performance degradation over time

2. **Metrics Integration**
   - Dashboard design for performance tracking
   - Alerting thresholds for performance changes
   - Visualization approaches for multi-dimensional metrics
   - Automated reporting workflows

## Open Research Challenges

1. What constitutes a "fair" comparison between deterministic database approaches and probabilistic RAG approaches?
2. How do we evaluate mappings for entities that exist in a scientific knowledge gap?
3. What is the appropriate balance between precision and creativity in biological entity mapping?
4. How should RAG evaluation adapt to the rapid evolution of biological ontologies?
5. What is the role of explainability in evaluating RAG mapping quality?

## Interdisciplinary Considerations

1. How can methods from information retrieval evaluation be adapted to biological ontology mapping?
2. What can we learn from medical coding evaluation approaches?
3. How should linguistic semantic evaluation be modified for biological semantics?
4. What statistical approaches from other fields might apply to this unique evaluation challenge?
