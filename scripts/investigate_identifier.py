#!/usr/bin/env python3
"""
Comprehensive investigation tool for problematic identifiers

Usage:
    python investigate_identifier.py Q6EMK4 \
        --source /path/to/source.tsv \
        --target /path/to/target.csv \
        --strategy production_simple
"""

import argparse
import pandas as pd
from pathlib import Path
import asyncio
import logging
import json
from typing import Dict, Any, List, Optional
import sys

# Add biomapper to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from biomapper.core.minimal_strategy_service import MinimalStrategyService
from biomapper.core.standards.known_issues import KnownIssuesRegistry
from biomapper.core.standards.debug_tracer import DebugTracer

logging.basicConfig(level=logging.INFO, format='%(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def check_identifier_in_file(identifier: str, file_path: str, column: Optional[str] = None) -> Dict[str, Any]:
    """Check if identifier exists in a file."""
    result = {
        'file': file_path,
        'found': False,
        'count': 0,
        'columns': [],
        'sample_rows': []
    }
    
    try:
        # Determine file type and read
        file_ext = Path(file_path).suffix.lower()
        if file_ext == '.csv':
            df = pd.read_csv(file_path)
        elif file_ext in ['.tsv', '.txt']:
            df = pd.read_csv(file_path, sep='\t')
        else:
            logger.warning(f"Unknown file type: {file_ext}")
            return result
        
        # Search for identifier
        if column and column in df.columns:
            mask = df[column].astype(str).str.contains(identifier, na=False)
            result['found'] = mask.any()
            result['count'] = mask.sum()
            if result['found']:
                result['columns'] = [column]
                result['sample_rows'] = df[mask].head(3).to_dict('records')
        else:
            # Search all columns
            for col in df.columns:
                mask = df[col].astype(str).str.contains(identifier, na=False)
                if mask.any():
                    result['found'] = True
                    result['count'] += mask.sum()
                    result['columns'].append(col)
                    if len(result['sample_rows']) < 3:
                        result['sample_rows'].extend(df[mask].head(3 - len(result['sample_rows'])).to_dict('records'))
        
    except Exception as e:
        logger.error(f"Error reading {file_path}: {e}")
        result['error'] = str(e)
    
    return result


async def run_mini_pipeline(identifier: str, strategy_name: str, configs_dir: str) -> Dict[str, Any]:
    """Run a mini pipeline with just the problematic identifier."""
    service = MinimalStrategyService(configs_dir)
    
    # Create debug config
    debug_config = {
        'trace_identifiers': [identifier],
        'save_trace': f'/tmp/trace_{identifier}.json',
        'check_known_issues': True
    }
    
    try:
        result = await service.execute_strategy(
            strategy_name=strategy_name,
            input_identifiers=[identifier],
            debug_config=debug_config
        )
        return {
            'success': True,
            'result': result,
            'trace_file': debug_config['save_trace']
        }
    except Exception as e:
        logger.error(f"Mini pipeline failed: {e}")
        return {
            'success': False,
            'error': str(e),
            'trace_file': debug_config.get('save_trace')
        }


def analyze_trace(trace_file: str) -> Dict[str, Any]:
    """Analyze the debug trace for insights."""
    try:
        with open(trace_file, 'r') as f:
            trace_data = json.load(f)
        
        analysis = {
            'total_events': len(trace_data),
            'actions': {},
            'phases': {},
            'errors': []
        }
        
        for entry in trace_data:
            action = entry.get('action', 'unknown')
            phase = entry.get('phase', 'unknown')
            
            if action not in analysis['actions']:
                analysis['actions'][action] = []
            analysis['actions'][action].append(entry)
            
            if phase not in analysis['phases']:
                analysis['phases'][phase] = 0
            analysis['phases'][phase] += 1
            
            if 'error' in entry.get('details', {}):
                analysis['errors'].append(entry)
        
        return analysis
    except Exception as e:
        logger.error(f"Failed to analyze trace: {e}")
        return {'error': str(e)}


def generate_investigation_report(
    identifier: str,
    source_check: Dict,
    target_check: Dict,
    pipeline_result: Dict,
    trace_analysis: Dict,
    known_issue: Optional[Any] = None
) -> str:
    """Generate a comprehensive investigation report."""
    
    report = f"""
# Investigation Report for {identifier}
{'=' * 60}

## Summary
- Identifier: {identifier}
- Source File Found: {source_check.get('found', False)}
- Target File Found: {target_check.get('found', False)}
- Pipeline Success: {pipeline_result.get('success', False)}
- Known Issue: {'Yes' if known_issue else 'No'}

## Source File Analysis
- File: {source_check.get('file', 'N/A')}
- Found: {source_check.get('found', False)}
- Count: {source_check.get('count', 0)}
- Columns: {', '.join(source_check.get('columns', []))}

## Target File Analysis
- File: {target_check.get('file', 'N/A')}
- Found: {target_check.get('found', False)}
- Count: {target_check.get('count', 0)}
- Columns: {', '.join(target_check.get('columns', []))}

## Pipeline Execution
- Success: {pipeline_result.get('success', False)}
"""
    
    if not pipeline_result.get('success'):
        report += f"- Error: {pipeline_result.get('error', 'Unknown')}\n"
    
    if trace_analysis and 'error' not in trace_analysis:
        report += f"""
## Trace Analysis
- Total Events: {trace_analysis.get('total_events', 0)}
- Actions Executed: {', '.join(trace_analysis.get('actions', {}).keys())}
- Phases: {trace_analysis.get('phases', {})}
- Errors Found: {len(trace_analysis.get('errors', []))}
"""
    
    if known_issue:
        report += f"""
## Known Issue Information
- Type: {known_issue.issue_type}
- Description: {known_issue.description}
- Status: {known_issue.investigation_status}
- Workaround: {known_issue.workaround or 'None'}
- Related Files: {', '.join(known_issue.related_files)}
"""
    
    report += f"""
## Recommendations
"""
    
    if source_check.get('found') and not target_check.get('found'):
        report += "- ⚠️ Identifier exists in source but not in target - possible missing mapping\n"
    elif source_check.get('found') and target_check.get('found') and not pipeline_result.get('success'):
        report += "- ⚠️ Identifier exists in both files but pipeline fails - check matching logic\n"
    elif not source_check.get('found'):
        report += "- ❌ Identifier not found in source file - check data loading\n"
    
    if known_issue and known_issue.workaround:
        report += f"- 💡 Apply workaround: {known_issue.workaround}\n"
    
    report += "\n" + "=" * 60 + "\n"
    
    return report


async def investigate_identifier(
    identifier: str,
    source_file: str,
    target_file: str,
    strategy: str,
    configs_dir: str = "configs/strategies"
) -> None:
    """Run comprehensive investigation of a problematic identifier."""
    
    print(f"🔍 INVESTIGATING: {identifier}")
    print("=" * 60)
    
    # 1. Check for known issues
    known_issue = KnownIssuesRegistry.check_identifier(identifier)
    if known_issue:
        print(f"⚠️ Known issue found: {known_issue.description}")
        if known_issue.workaround:
            print(f"💡 Workaround: {known_issue.workaround}")
    
    # 2. Check presence in source
    print("\n📁 Checking source file...")
    source_check = check_identifier_in_file(identifier, source_file)
    print(f"  Found: {source_check['found']} (Count: {source_check['count']})")
    
    # 3. Check presence in target
    print("\n📁 Checking target file...")
    target_check = check_identifier_in_file(identifier, target_file)
    print(f"  Found: {target_check['found']} (Count: {target_check['count']})")
    
    # 4. Run mini pipeline
    print(f"\n🚀 Running mini pipeline with strategy: {strategy}")
    pipeline_result = await run_mini_pipeline(identifier, strategy, configs_dir)
    print(f"  Success: {pipeline_result['success']}")
    
    # 5. Analyze trace
    trace_analysis = {}
    if pipeline_result.get('trace_file') and Path(pipeline_result['trace_file']).exists():
        print("\n📊 Analyzing trace...")
        trace_analysis = analyze_trace(pipeline_result['trace_file'])
        print(f"  Events: {trace_analysis.get('total_events', 0)}")
        print(f"  Errors: {len(trace_analysis.get('errors', []))}")
    
    # 6. Generate report
    report = generate_investigation_report(
        identifier,
        source_check,
        target_check,
        pipeline_result,
        trace_analysis,
        known_issue
    )
    
    # Save report
    report_file = f"/tmp/investigation_{identifier}.md"
    with open(report_file, 'w') as f:
        f.write(report)
    
    print(f"\n📄 Report saved to: {report_file}")
    print("\n" + report)


def main():
    parser = argparse.ArgumentParser(description="Investigate problematic identifiers")
    parser.add_argument("identifier", help="Identifier to investigate")
    parser.add_argument("--source", required=True, help="Source data file")
    parser.add_argument("--target", required=True, help="Target data file")
    parser.add_argument("--strategy", required=True, help="Strategy name to test")
    parser.add_argument("--configs-dir", default="configs/strategies", help="Strategies directory")
    parser.add_argument("--trace", action="store_true", help="Enable detailed tracing")
    
    args = parser.parse_args()
    
    # Run investigation
    asyncio.run(investigate_identifier(
        args.identifier,
        args.source,
        args.target,
        args.strategy,
        args.configs_dir
    ))


if __name__ == "__main__":
    main()