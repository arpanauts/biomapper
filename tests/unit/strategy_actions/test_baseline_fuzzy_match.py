import pytest
import time
from biomapper.core.strategy_actions.baseline_fuzzy_match import (
    BaselineFuzzyMatchAction,
    BaselineFuzzyMatchParams,
    FuzzyAlgorithm,
    MatchMetrics
)

class TestBaselineFuzzyMatch:
    """Test suite for baseline fuzzy matching - WRITE FIRST!"""
    
    @pytest.fixture
    def action(self):
        """Create action instance."""
        return BaselineFuzzyMatchAction()
    
    @pytest.fixture
    def sample_source_data(self):
        """Sample Arivale metabolite data."""
        return [
            {'BIOCHEMICAL_NAME': 'spermidine', 'HMDB': 'HMDB01257'},
            {'BIOCHEMICAL_NAME': '12,13-DiHOME', 'HMDB': 'HMDB04705'},
            {'BIOCHEMICAL_NAME': 'S-1-pyrroline-5-carboxylate', 'HMDB': ''},
            {'BIOCHEMICAL_NAME': 'cholesterol', 'HMDB': 'HMDB00067'}
        ]
    
    @pytest.fixture
    def sample_target_data(self):
        """Sample Nightingale reference data."""
        return [
            {'unified_name': 'Total cholesterol', 'nightingale_id': 'ng-001'},
            {'unified_name': 'Spermidine', 'nightingale_id': 'ng-002'},
            {'unified_name': 'Glucose', 'nightingale_id': 'ng-003'},
            {'unified_name': 'LDL cholesterol', 'nightingale_id': 'ng-004'}
        ]
    
    def test_preprocessing_handles_variations(self, action):
        """Test metabolite name preprocessing."""
        # Case normalization
        assert action._preprocess_metabolite_name("Cholesterol") == "cholesterol"
        
        # Separator handling
        assert action._preprocess_metabolite_name("12,13-DiHOME") == "12,13 dihome"
        
        # Parentheses removal
        assert action._preprocess_metabolite_name("Glucose (blood)") == "glucose"
        
        # Whitespace normalization
        assert action._preprocess_metabolite_name("  Total   cholesterol  ") == "total cholesterol"
        # This test should FAIL initially
    
    def test_fuzzy_score_calculation(self, action):
        """Test fuzzy score calculation with different algorithms."""
        # Exact match
        score = action._get_fuzzy_score("cholesterol", "cholesterol", FuzzyAlgorithm.RATIO)
        assert score == 1.0
        
        # Token set ratio should handle word order
        score1 = action._get_fuzzy_score(
            "total cholesterol",
            "cholesterol total",
            FuzzyAlgorithm.TOKEN_SET_RATIO
        )
        assert score1 > 0.9
        
        # Partial ratio should handle substrings
        score2 = action._get_fuzzy_score(
            "cholesterol",
            "total cholesterol",
            FuzzyAlgorithm.PARTIAL_RATIO
        )
        assert score2 > 0.8
        # This test should FAIL initially
    
    def test_confidence_bucket_calculation(self, action):
        """Test confidence score bucketing."""
        assert action._calculate_confidence_bucket(0.98) == "very_high"
        assert action._calculate_confidence_bucket(0.92) == "high"
        assert action._calculate_confidence_bucket(0.87) == "medium"
        assert action._calculate_confidence_bucket(0.82) == "low"
        assert action._calculate_confidence_bucket(0.75) == "very_low"
        # This test should FAIL initially
    
    @pytest.mark.asyncio
    async def test_basic_matching(self, action, sample_source_data, sample_target_data):
        """Test basic fuzzy matching functionality."""
        params = BaselineFuzzyMatchParams(
            source_dataset_key="source",
            target_dataset_key="target",
            source_column="BIOCHEMICAL_NAME",
            target_column="unified_name",
            threshold=0.80,
            algorithm=FuzzyAlgorithm.TOKEN_SET_RATIO,
            output_key="matches"
        )
        
        context = {
            'datasets': {
                'source': sample_source_data,
                'target': sample_target_data
            }
        }
        
        result = await action.execute(params, context)
        
        assert result.success
        matches = context['datasets']['matches']
        
        # Should match at least cholesterol and spermidine
        assert len(matches) >= 2
        
        # Check match structure
        for match in matches:
            assert 'source' in match
            assert 'target' in match
            assert 'score' in match
            assert match['score'] >= 0.80
            assert match['stage'] == 'baseline'
        # This test should FAIL initially
    
    @pytest.mark.asyncio
    async def test_unmatched_tracking(self, action):
        """Test tracking of unmatched items."""
        params = BaselineFuzzyMatchParams(
            source_dataset_key="source",
            target_dataset_key="target",
            source_column="BIOCHEMICAL_NAME",
            target_column="unified_name",
            threshold=0.95,  # High threshold to force unmatched
            algorithm=FuzzyAlgorithm.RATIO,
            output_key="matches"
        )
        
        context = {
            'datasets': {
                'source': [
                    {'BIOCHEMICAL_NAME': 'unknown-metabolite-xyz'},
                    {'BIOCHEMICAL_NAME': 'cholesterol'}
                ],
                'target': [
                    {'unified_name': 'Total cholesterol'}
                ]
            }
        }
        
        result = await action.execute(params, context)
        
        unmatched_key = "unmatched.baseline.source"
        assert unmatched_key in context['datasets']
        unmatched = context['datasets'][unmatched_key]
        
        # Unknown metabolite should be unmatched
        assert len(unmatched) >= 1
        assert any(u['BIOCHEMICAL_NAME'] == 'unknown-metabolite-xyz' for u in unmatched)
        # This test should FAIL initially
    
    @pytest.mark.asyncio
    async def test_metrics_tracking(self, action, sample_source_data, sample_target_data):
        """Test comprehensive metrics tracking."""
        params = BaselineFuzzyMatchParams(
            source_dataset_key="source",
            target_dataset_key="target",
            source_column="BIOCHEMICAL_NAME",
            target_column="unified_name",
            threshold=0.80,
            algorithm=FuzzyAlgorithm.TOKEN_SET_RATIO,
            output_key="matches",
            track_metrics=True
        )
        
        context = {
            'datasets': {
                'source': sample_source_data,
                'target': sample_target_data
            }
        }
        
        result = await action.execute(params, context)
        
        assert 'metrics' in context
        assert 'baseline' in context['metrics']
        
        metrics = context['metrics']['baseline']
        assert metrics['stage'] == 'baseline'
        assert metrics['total_source'] == len(sample_source_data)
        assert metrics['matched'] >= 0
        assert metrics['unmatched'] >= 0
        assert metrics['execution_time'] > 0
        assert 'confidence_distribution' in metrics
        assert metrics['algorithm_used'] == 'token_set_ratio'
        # This test should FAIL initially
    
    @pytest.mark.asyncio
    async def test_limit_per_source(self, action):
        """Test limiting matches per source item."""
        params = BaselineFuzzyMatchParams(
            source_dataset_key="source",
            target_dataset_key="target",
            source_column="name",
            target_column="name",
            threshold=0.70,
            algorithm=FuzzyAlgorithm.TOKEN_SET_RATIO,
            output_key="matches",
            limit_per_source=2
        )
        
        context = {
            'datasets': {
                'source': [
                    {'name': 'cholesterol'}
                ],
                'target': [
                    {'name': 'Total cholesterol'},
                    {'name': 'LDL cholesterol'},
                    {'name': 'HDL cholesterol'},
                    {'name': 'VLDL cholesterol'}
                ]
            }
        }
        
        result = await action.execute(params, context)
        
        matches = context['datasets']['matches']
        # Should have at most 2 matches for cholesterol
        cholesterol_matches = [m for m in matches if m['source']['name'] == 'cholesterol']
        assert len(cholesterol_matches) <= 2
        
        # Should be the highest scoring matches
        if len(cholesterol_matches) == 2:
            assert cholesterol_matches[0]['score'] >= cholesterol_matches[1]['score']
        # This test should FAIL initially
    
    @pytest.mark.asyncio
    async def test_performance_tracking(self, action):
        """Test execution time tracking."""
        params = BaselineFuzzyMatchParams(
            source_dataset_key="source",
            target_dataset_key="target",
            source_column="name",
            target_column="name",
            threshold=0.80,
            algorithm=FuzzyAlgorithm.RATIO,
            output_key="matches"
        )
        
        # Create larger dataset for meaningful timing
        source_data = [{'name': f'metabolite_{i}'} for i in range(100)]
        target_data = [{'name': f'metabolite_{i}'} for i in range(50)]
        
        context = {
            'datasets': {
                'source': source_data,
                'target': target_data
            }
        }
        
        start = time.time()
        result = await action.execute(params, context)
        actual_time = time.time() - start
        
        # Check that reported time is reasonable
        reported_time = result.data['execution_time']
        assert abs(reported_time - actual_time) < 0.1  # Within 100ms
        # This test should FAIL initially