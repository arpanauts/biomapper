"""Report generation for progressive enhancement results."""

import matplotlib.pyplot as plt
from pathlib import Path
from typing import Dict, Any

class EnhancementReportGenerator:
    """Generates reports for progressive enhancement results."""
    
    def generate_comparison_chart(
        self,
        metrics: Dict[str, Dict[str, Any]],
        output_path: Path
    ) -> None:
        """Generate bar chart comparing stages."""
        stages = []
        match_rates = []
        
        for stage in ['baseline', 'api_enriched', 'vector_enhanced']:
            if stage in metrics:
                stages.append(stage.replace('_', ' ').title())
                rate = metrics[stage].get('match_rate', metrics[stage].get('recall', 0))
                match_rates.append(rate * 100)
        
        plt.figure(figsize=(10, 6))
        bars = plt.bar(stages, match_rates, color=['#3498db', '#2ecc71', '#e74c3c'])
        
        # Add value labels
        for bar, rate in zip(bars, match_rates):
            plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                    f'{rate:.1f}%', ha='center', va='bottom')
        
        plt.xlabel('Enhancement Stage')
        plt.ylabel('Match Rate (%)')
        plt.title('Progressive Enhancement Results')
        plt.ylim(0, 100)
        
        plt.tight_layout()
        plt.savefig(output_path)
        plt.close()