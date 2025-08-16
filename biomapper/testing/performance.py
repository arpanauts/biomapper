"""Performance profiling and testing utilities."""

import time
import psutil
import pandas as pd
import numpy as np
from typing import Callable, Dict, Any, List, Optional, Tuple
from contextlib import contextmanager
from dataclasses import dataclass, field
import tracemalloc
import warnings


@dataclass
class PerformanceMetrics:
    """Container for performance metrics."""
    duration: float
    memory_start: float
    memory_end: float
    memory_peak: float
    memory_delta: float
    cpu_percent: float = 0.0
    
    @property
    def memory_delta_mb(self) -> float:
        """Memory delta in megabytes."""
        return self.memory_delta / (1024 * 1024)
    
    @property
    def duration_ms(self) -> float:
        """Duration in milliseconds."""
        return self.duration * 1000


@dataclass
class ComplexityAnalysis:
    """Results of algorithmic complexity analysis."""
    estimated_complexity: str
    confidence: float
    r_squared: float
    coefficients: Dict[str, float] = field(default_factory=dict)
    warning: Optional[str] = None


class PerformanceProfiler:
    """Profile performance of biomapper actions and detect complexity issues."""
    
    def __init__(self):
        """Initialize the profiler."""
        self.results: Dict[str, PerformanceMetrics] = {}
        self.process = psutil.Process()
        
    @contextmanager
    def profile(self, name: str, track_memory: bool = True):
        """Context manager to profile a code block.
        
        Args:
            name: Name for this profiling run
            track_memory: Whether to track memory usage
            
        Yields:
            None
            
        Example:
            >>> profiler = PerformanceProfiler()
            >>> with profiler.profile("my_operation"):
            ...     result = expensive_operation()
        """
        # Start measurements
        start_time = time.perf_counter()
        start_memory = self.process.memory_info().rss
        
        if track_memory:
            tracemalloc.start()
        
        # Track CPU usage
        self.process.cpu_percent()  # First call to initialize
        
        try:
            yield
        finally:
            # End measurements
            end_time = time.perf_counter()
            end_memory = self.process.memory_info().rss
            cpu_percent = self.process.cpu_percent()
            
            peak_memory = end_memory
            if track_memory:
                current, peak = tracemalloc.get_traced_memory()
                peak_memory = max(peak_memory, start_memory + peak)
                tracemalloc.stop()
            
            # Store results
            self.results[name] = PerformanceMetrics(
                duration=end_time - start_time,
                memory_start=start_memory,
                memory_end=end_memory,
                memory_peak=peak_memory,
                memory_delta=end_memory - start_memory,
                cpu_percent=cpu_percent
            )
    
    def benchmark_scaling(self, 
                         func: Callable[[Any], Any],
                         sizes: List[int],
                         data_generator: Optional[Callable[[int], Any]] = None,
                         warmup: bool = True) -> pd.DataFrame:
        """Benchmark function performance with different data sizes.
        
        Args:
            func: Function to benchmark
            sizes: List of data sizes to test
            data_generator: Function to generate test data for given size
            warmup: Whether to do a warmup run
            
        Returns:
            DataFrame with size, time, and memory columns
        """
        if data_generator is None:
            # Default: generate DataFrame with n rows
            data_generator = lambda n: pd.DataFrame({
                'id': range(n),
                'value': np.random.randn(n)
            })
        
        results = []
        
        # Warmup run
        if warmup and sizes:
            warmup_data = data_generator(min(sizes))
            func(warmup_data)
        
        for size in sizes:
            # Generate test data
            data = data_generator(size)
            
            # Profile the function
            with self.profile(f"size_{size}"):
                func(data)
            
            # Collect results
            metrics = self.results[f"size_{size}"]
            results.append({
                'size': size,
                'time': metrics.duration,
                'memory_mb': metrics.memory_delta_mb,
                'memory_peak_mb': metrics.memory_peak / (1024 * 1024),
                'cpu_percent': metrics.cpu_percent
            })
        
        return pd.DataFrame(results)
    
    def detect_complexity(self, results: pd.DataFrame) -> ComplexityAnalysis:
        """Detect algorithmic complexity from benchmark results.
        
        Args:
            results: DataFrame with 'size' and 'time' columns
            
        Returns:
            ComplexityAnalysis with estimated complexity
        """
        if len(results) < 3:
            return ComplexityAnalysis(
                estimated_complexity="unknown",
                confidence=0.0,
                r_squared=0.0,
                warning="Insufficient data points for analysis"
            )
        
        sizes = results['size'].values
        times = results['time'].values
        
        # Normalize for numerical stability
        size_norm = sizes / sizes.max()
        time_norm = times / times.max()
        
        # Test different complexity models
        models = {
            'O(1)': lambda x: np.ones_like(x),
            'O(log n)': lambda x: np.log(x + 1),
            'O(n)': lambda x: x,
            'O(n log n)': lambda x: x * np.log(x + 1),
            'O(n^2)': lambda x: x ** 2,
            'O(n^3)': lambda x: x ** 3,
            'O(2^n)': lambda x: np.exp(x * 0.693)  # Approximate 2^n
        }
        
        best_model = None
        best_r2 = -np.inf
        best_coeffs = {}
        
        for complexity, model_func in models.items():
            try:
                # Fit the model
                X = model_func(size_norm)
                
                # Handle edge cases
                if np.all(X == X[0]):  # Constant
                    if complexity == 'O(1)':
                        # Check if times are roughly constant
                        cv = np.std(time_norm) / np.mean(time_norm)
                        if cv < 0.1:  # Less than 10% variation
                            r2 = 1.0 - cv
                        else:
                            r2 = 0.0
                    else:
                        r2 = 0.0
                else:
                    # Linear regression
                    A = np.vstack([X, np.ones(len(X))]).T
                    coeffs, residuals, rank, s = np.linalg.lstsq(A, time_norm, rcond=None)
                    
                    # Calculate R-squared
                    y_pred = A @ coeffs
                    ss_res = np.sum((time_norm - y_pred) ** 2)
                    ss_tot = np.sum((time_norm - np.mean(time_norm)) ** 2)
                    r2 = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
                    
                    if r2 > best_r2:
                        best_r2 = r2
                        best_model = complexity
                        best_coeffs = {'slope': coeffs[0], 'intercept': coeffs[1]}
                        
            except Exception as e:
                # Skip models that fail to fit
                continue
        
        # Determine confidence based on R-squared
        if best_r2 > 0.95:
            confidence = 1.0
        elif best_r2 > 0.85:
            confidence = 0.8
        elif best_r2 > 0.70:
            confidence = 0.6
        else:
            confidence = 0.4
        
        # Add warning for concerning complexities
        warning = None
        if best_model in ['O(n^2)', 'O(n^3)', 'O(2^n)']:
            warning = f"High complexity detected: {best_model}. Consider optimization."
        elif best_model == 'O(n^2)' and max(sizes) > 1000:
            warning = "O(n^2) complexity will cause issues with large datasets"
        
        return ComplexityAnalysis(
            estimated_complexity=best_model or 'unknown',
            confidence=confidence,
            r_squared=best_r2,
            coefficients=best_coeffs,
            warning=warning
        )
    
    def assert_complexity(self, 
                         results: pd.DataFrame,
                         max_complexity: str = 'O(n log n)',
                         min_confidence: float = 0.7):
        """Assert that algorithmic complexity is acceptable.
        
        Args:
            results: Benchmark results DataFrame
            max_complexity: Maximum acceptable complexity
            min_confidence: Minimum confidence required
            
        Raises:
            AssertionError: If complexity exceeds maximum
        """
        analysis = self.detect_complexity(results)
        
        # Define complexity ordering
        complexity_order = {
            'O(1)': 0,
            'O(log n)': 1, 
            'O(n)': 2,
            'O(n log n)': 3,
            'O(n^2)': 4,
            'O(n^3)': 5,
            'O(2^n)': 6,
            'unknown': 7
        }
        
        if analysis.confidence >= min_confidence:
            actual_order = complexity_order.get(analysis.estimated_complexity, 7)
            max_order = complexity_order.get(max_complexity, 3)
            
            assert actual_order <= max_order, (
                f"Performance issue: {analysis.estimated_complexity} complexity detected "
                f"(confidence: {analysis.confidence:.2f}, R²: {analysis.r_squared:.3f}). "
                f"Maximum allowed: {max_complexity}. "
                f"{analysis.warning or ''}"
            )
    
    def generate_report(self) -> str:
        """Generate a performance report.
        
        Returns:
            Formatted performance report string
        """
        if not self.results:
            return "No performance data collected."
        
        lines = ["Performance Report", "=" * 50]
        
        for name, metrics in self.results.items():
            lines.extend([
                f"\n{name}:",
                f"  Duration: {metrics.duration:.3f}s ({metrics.duration_ms:.1f}ms)",
                f"  Memory Delta: {metrics.memory_delta_mb:.2f} MB",
                f"  Peak Memory: {metrics.memory_peak / (1024 * 1024):.2f} MB",
                f"  CPU Usage: {metrics.cpu_percent:.1f}%"
            ])
        
        return "\n".join(lines)
    
    def compare_implementations(self,
                               implementations: Dict[str, Callable],
                               test_data: Any) -> pd.DataFrame:
        """Compare performance of multiple implementations.
        
        Args:
            implementations: Dict mapping name to function
            test_data: Data to test with
            
        Returns:
            DataFrame comparing implementations
        """
        results = []
        
        for name, func in implementations.items():
            with self.profile(name):
                func(test_data)
            
            metrics = self.results[name]
            results.append({
                'implementation': name,
                'time_ms': metrics.duration_ms,
                'memory_mb': metrics.memory_delta_mb,
                'cpu_percent': metrics.cpu_percent
            })
        
        df = pd.DataFrame(results)
        df['relative_time'] = df['time_ms'] / df['time_ms'].min()
        df['relative_memory'] = df['memory_mb'] / df['memory_mb'].min()
        
        return df.sort_values('time_ms')