#!/usr/bin/env python3
"""
Prevent partial victory declarations in BiOMapper development.
Ensures all components work before allowing SUCCESS claims.
"""

import sys
import os
import json
from pathlib import Path
from typing import Dict, List, Tuple


class PartialVictoryBlocker:
    """Block premature success declarations."""
    
    def __init__(self, strategy_name: str = None):
        self.strategy_name = strategy_name
        self.validation_errors = []
        
    def check_parameters_resolve(self) -> bool:
        """Verify YAML parameters substitute correctly."""
        if not self.strategy_name:
            return True  # Skip if no specific strategy
            
        yaml_file = Path(f"src/configs/strategies/{self.strategy_name}.yaml")
        if not yaml_file.exists():
            yaml_file = Path(f"src/configs/strategies/experimental/{self.strategy_name}.yaml")
        
        if not yaml_file.exists():
            self.validation_errors.append(f"Strategy file not found: {self.strategy_name}")
            return False
        
        # Use the parameter checker
        from check_yaml_params import validate_parameter_substitution
        valid, issues = validate_parameter_substitution(yaml_file)
        
        if not valid:
            self.validation_errors.extend(issues)
            
        return valid
    
    def check_outputs_generated(self) -> bool:
        """Verify expected output files were generated."""
        if not self.strategy_name:
            output_dir = Path("/tmp/biomapper")
        else:
            output_dir = Path(f"/tmp/biomapper/{self.strategy_name}")
        
        if not output_dir.exists():
            self.validation_errors.append(f"Output directory missing: {output_dir}")
            return False
        
        # Check for required BiOMapper outputs
        required_files = [
            "mapping_statistics.tsv",
            "mapping_summary.txt",
            "mapping_report.json"
        ]
        
        missing = []
        for file in required_files:
            if not (output_dir / file).exists():
                missing.append(file)
        
        if missing:
            self.validation_errors.append(f"Missing output files: {', '.join(missing)}")
            return False
            
        return True
    
    def check_coverage_authentic(self) -> bool:
        """Verify biological coverage is authentic (no entity duplication)."""
        if not self.strategy_name:
            report_file = Path("/tmp/biomapper/mapping_report.json")
        else:
            report_file = Path(f"/tmp/biomapper/{self.strategy_name}/mapping_report.json")
        
        if not report_file.exists():
            self.validation_errors.append(f"Report file missing: {report_file}")
            return False
        
        try:
            with open(report_file, 'r') as f:
                data = json.load(f)
        except Exception as e:
            self.validation_errors.append(f"Cannot read report: {e}")
            return False
        
        # Check for coverage inflation
        if 'progressive_stats' in data:
            stats = data['progressive_stats']
            
            # Check total doesn't exceed processed
            total_processed = stats.get('total_processed', 0)
            total_matched = stats.get('total_matched', 0)
            
            if total_matched > total_processed:
                self.validation_errors.append(
                    f"Coverage inflation: {total_matched} matches > {total_processed} processed"
                )
                return False
            
            # Check progressive improvement (no reprocessing)
            if 'stages' in stats:
                prev_cumulative = 0
                for stage_num in sorted(stats['stages'].keys()):
                    stage = stats['stages'][str(stage_num)]
                    cumulative = stage.get('cumulative_matched', 0)
                    
                    if cumulative < prev_cumulative:
                        self.validation_errors.append(
                            f"Stage {stage_num} shows coverage decrease"
                        )
                        return False
                    
                    prev_cumulative = cumulative
        
        return True
    
    def check_no_import_errors(self) -> bool:
        """Verify no import errors in API server."""
        try:
            # Try importing key modules
            sys.path.insert(0, 'src')
            from actions.registry import ACTION_REGISTRY
            
            if len(ACTION_REGISTRY) == 0:
                self.validation_errors.append("No actions loaded in registry")
                return False
            
            return True
            
        except ImportError as e:
            self.validation_errors.append(f"Import error: {e}")
            return False
    
    def enforce_complete_success(self) -> bool:
        """Enforce complete success validation."""
        print("🔍 Enforcing Complete Success Validation...")
        print("=" * 50)
        
        checks = [
            ("Parameter Substitution", self.check_parameters_resolve()),
            ("Output Files", self.check_outputs_generated()),
            ("Authentic Coverage", self.check_coverage_authentic()),
            ("Import Paths", self.check_no_import_errors())
        ]
        
        all_passed = True
        for check_name, passed in checks:
            if passed:
                print(f"✅ {check_name}: PASSED")
            else:
                print(f"❌ {check_name}: FAILED")
                all_passed = False
        
        print("=" * 50)
        
        if all_passed:
            print("✅ ALL VALIDATION CHECKS PASSED")
            print("✅ SUCCESS DECLARATION AUTHORIZED")
            return True
        else:
            print("❌ VALIDATION FAILURES DETECTED")
            print("❌ SUCCESS DECLARATION BLOCKED")
            print("\nFailures:")
            for error in self.validation_errors:
                print(f"  • {error}")
            print("\n🚫 FIX ALL ISSUES BEFORE DECLARING SUCCESS")
            return False


def main():
    """CLI interface for victory validation."""
    strategy_name = sys.argv[1] if len(sys.argv) > 1 else None
    
    if strategy_name:
        print(f"📋 Validating strategy: {strategy_name}")
    else:
        print("📋 Validating general BiOMapper state")
    
    blocker = PartialVictoryBlocker(strategy_name)
    
    if not blocker.enforce_complete_success():
        sys.exit(1)
    
    sys.exit(0)


if __name__ == "__main__":
    main()