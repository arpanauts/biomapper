# BiOMapper Strategy Development Command

## Command Specification

### **Primary Command:**
```bash
/biomapper-strategy <entity_type>
```

### **Supported Entity Types:**
- `metabolites` - Metabolite/compound mapping strategies
- `proteins` - Protein identifier harmonization  
- `chemistry` - Clinical chemistry/LOINC mapping
- `custom` - User-defined entity type

### **Usage Examples:**
```bash
/biomapper-strategy metabolites
/biomapper-strategy proteins  
/biomapper-strategy chemistry
/biomapper-strategy custom
```

---

## Agent Response Workflow

### **Phase 1: Strategic Context Discovery**

**Initial Response Template:**
```
🧬 BiOMapper Strategy Development Assistant

Entity Type: {entity_type}

Before we begin development, I need to understand your strategic context through a series of focused questions. This systematic approach has proven successful with our protein mapping strategies, where we achieved 99.3% coverage through careful planning.

Let's start with the most important question:

STRATEGIC CONTEXT QUESTION 1:
What is the primary biological challenge you're trying to solve with this {entity_type} mapping strategy?

This helps me understand whether we should optimize for:
- Maximum biological coverage across diverse {entity_type} classes
- High-confidence matches for downstream analysis
- Integration with existing {domain_specific} workflows
- Research exploration of novel {entity_type} relationships

Your answer will guide our entire development approach...
```

### **Phase 2: Requirements Clarification**

**Follow-up Question Categories:**

#### **Coverage & Success Definition:**
```
QUESTION 2: Success Metrics & Expectations

Based on your response about "{user_primary_goal}"...

What success rate would demonstrate that this strategy is working well for your biological research needs?

- 70-80% (good for exploratory research)
- 80-90% (strong for most {entity_type} applications)  
- 90%+ (exceptional, may require advanced semantic matching)

Also, are there specific {entity_type} classes that are most critical for your research, or should we optimize for broad coverage?

This helps me set realistic stage-by-stage coverage targets for the progressive mapping framework...
```

#### **Data Characteristics:**
```
QUESTION 3: Data Source Analysis

To design the optimal pipeline, I need to understand your data:

1. Data Scale & Source:
   - Approximate dataset size (hundreds, thousands, tens of thousands)?
   - Source system (Arivale, clinical database, research dataset)?
   - Update frequency (one-time analysis, regular processing)?

2. Identifier Patterns:
   - What types of {entity_type} identifiers do you expect to see?
   - Any known problematic patterns or edge cases from previous work?
   - Composite identifiers or multi-value fields?

3. Quality Expectations:
   - Any known data quality issues we should plan for?
   - Tolerance for false positives vs. false negatives?

This information helps me choose the right normalization and matching strategies...
```

#### **Technical Integration:**
```
QUESTION 4: Integration & Performance Requirements

1. Timeline Constraints:
   - Do you need rapid prototyping results or production-ready development?
   - Any immediate deadlines or blocking requirements?

2. Integration Needs:
   - Does this need to integrate with existing BiOMapper strategies?
   - Specific output formats required for downstream analysis?
   - Will this be used by other team members or automated systems?

3. Performance Priorities:
   - Processing speed vs. maximum coverage trade-offs?
   - Memory/computational constraints?
   - Real-time vs. batch processing requirements?
```

### **Phase 3: Development Planning & Action Analysis**

**System Analysis Response:**
```
Based on your responses, I'm analyzing the BiOMapper ecosystem for {entity_type} mapping:

🔍 DISCOVERING AVAILABLE ACTIONS...
✅ Found {X} existing actions suitable for {entity_type}
⚠️  Identified {Y} actions that need development
📊 Estimated coverage progression: {stage1}% → {stage2}% → {stage3}%+

PROGRESSIVE MAPPING FRAMEWORK DESIGN:
Stage 1 - Direct Matching: {method1} (Expected: {stage1}%)
Stage 2 - {enhancement_method}: {method2} (Expected: {stage2}% cumulative)
Stage 3 - {advanced_method}: {method3} (Expected: {stage3}%+ cumulative)

REQUIRED NEW ACTIONS IDENTIFIED:
1. {ACTION_TYPE_1}
   - Purpose: {biological_purpose}
   - Complexity: {complexity_level}
   - Development time: ~{hours} hours with TDD
   - Why needed: {biological_justification}

2. {ACTION_TYPE_2}
   - Purpose: {biological_purpose}
   - Complexity: {complexity_level}
   - Development time: ~{hours} hours with comprehensive testing
   - Why needed: {biological_justification}

EXISTING ACTIONS READY TO USE:
✅ {EXISTING_ACTION_1} - {purpose}
✅ {EXISTING_ACTION_2} - {purpose}
✅ {EXISTING_ACTION_3} - {purpose}
```

### **Phase 4: Development Approach Decision**

**Implementation Strategy Options:**
```
DEVELOPMENT STRATEGY QUESTION:

Based on the analysis, I can proceed with development in several ways:

OPTION A: Sequential Development (Lower Risk)
- Start with {simplest_action} to validate approach
- Build pipeline incrementally with frequent testing
- Timeline: ~{timeline_sequential} weeks
- Pros: Validates each component thoroughly
- Cons: Longer time to see full pipeline results

OPTION B: Parallel Action Development (Faster Results)  
- Develop {action1} and {action2} simultaneously
- Integrate into complete pipeline once actions are ready
- Timeline: ~{timeline_parallel} weeks
- Pros: Faster overall completion
- Cons: More complex integration testing

OPTION C: Hybrid Approach (Balanced)
- Start with strategy skeleton using existing actions
- Develop new actions iteratively based on initial results
- Timeline: ~{timeline_hybrid} weeks  
- Pros: Early results + systematic enhancement
- Cons: May require pipeline refactoring

Which approach aligns best with your timeline and risk tolerance?

Additionally, should I:
- Generate the complete strategy YAML configuration now?
- Create TDD test suites for the new actions?
- Set up the development environment and file structure?
```

### **Phase 5: Implementation Kickoff**

**Final Setup & Next Steps:**
```
🚀 Ready to begin {entity_type} strategy development!

DEVELOPMENT PLAN CONFIRMED:
- Entity Type: {entity_type}
- Primary Goal: {user_goal}  
- Target Coverage: {target_coverage}%
- Development Approach: {chosen_approach}
- Timeline Estimate: {timeline}

GENERATED ARTIFACTS:
📄 Strategy Configuration: /strategies/{entity_type}_progressive_v1.0.yaml
🧪 Test Suite Templates: /tests/test_{entity_type}_strategy.py
🔧 Action Stubs: /actions/{entity_type}/{action_files}
📚 Documentation: Added to CLAUDE.md

IMMEDIATE NEXT STEPS:
1. {next_step_1}
2. {next_step_2}  
3. {next_step_3}

Would you like me to:
[A] Start implementing {first_action} with TDD approach
[B] Generate the complete pipeline skeleton first
[C] Begin with data analysis of your {entity_type} dataset
[D] Create comprehensive test scenarios before any implementation

Type your preference and I'll begin development immediately!
```

---

## Entity-Specific Customizations

### **For Metabolites:**
- **Domain Focus:** "metabolomics workflows", "metabolite classes", "chemical databases"
- **Expected Actions:** CTS_BRIDGE, HMDB normalization, semantic matching
- **Coverage Expectations:** 40% → 75% → 85%+
- **Key Challenges:** Synonym variations, structural isomers, vendor naming

### **For Proteins:**  
- **Domain Focus:** "proteomics analysis", "protein families", "sequence databases"
- **Expected Actions:** UniProt extraction, composite parsing, isoform handling
- **Coverage Expectations:** 65% → 80% → 95%+
- **Key Challenges:** Isoforms, version numbers, composite identifiers

### **For Chemistry:**
- **Domain Focus:** "clinical chemistry", "laboratory tests", "diagnostic codes"  
- **Expected Actions:** LOINC matching, fuzzy name matching, vendor harmonization
- **Coverage Expectations:** 30% → 65% → 75%+
- **Key Challenges:** High naming variability, vendor-specific formats

### **For Custom:**
- **Domain Focus:** User-defined biological entity type
- **Expected Actions:** Analyzed based on user description
- **Coverage Expectations:** Estimated based on complexity analysis
- **Key Challenges:** Discovered through systematic questioning

---

## Implementation Notes for Claude Code Agent

### **Required Agent Behaviors:**

1. **Progressive Questioning:** Ask one focused question at a time, build on previous answers
2. **Context Preservation:** Reference user's previous responses in follow-up questions  
3. **Biological Awareness:** Adapt questions based on entity type characteristics
4. **Coverage Estimation:** Provide realistic expectations based on biological complexity
5. **Action Analysis:** Scan existing BiOMapper actions and identify gaps
6. **TDD Enforcement:** Always include test-driven development in planning
7. **File Generation:** Create all necessary strategy files, tests, and documentation
8. **Next Step Clarity:** Always end with clear, actionable next steps

### **Success Criteria:**

- ✅ User provides complete strategic context through systematic questioning
- ✅ Realistic coverage expectations set for each progressive stage  
- ✅ Required new actions identified with biological justification
- ✅ Development timeline estimated based on complexity analysis
- ✅ Complete strategy skeleton generated with proper file structure
- ✅ TDD test suites created for all new actions
- ✅ Clear implementation path established for immediate execution

This command transforms BiOMapper strategy development from complex configuration into guided, systematic, biological-domain-aware development conversation.