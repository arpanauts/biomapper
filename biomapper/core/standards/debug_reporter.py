"""Debug report generator for edge case analysis."""

from typing import Dict, List, Any, Optional
from datetime import datetime
import pandas as pd
import json
from pathlib import Path

from .known_issues import KnownIssuesRegistry


class DebugReporter:
    """Generate comprehensive debug reports for problematic identifiers."""
    
    @staticmethod
    def generate_identifier_report(
        identifier: str,
        trace_log: List[Dict],
        results: Optional[pd.DataFrame] = None,
        source_data: Optional[pd.DataFrame] = None,
        target_data: Optional[pd.DataFrame] = None
    ) -> str:
        """Generate detailed report for a problematic identifier.
        
        Args:
            identifier: The identifier being investigated
            trace_log: Debug trace log from pipeline execution
            results: Final results dataframe if available
            source_data: Source dataset if available
            target_data: Target dataset if available
            
        Returns:
            Formatted markdown report
        """
        
        report = f"""# Debug Report for {identifier}
Generated: {datetime.now().isoformat()}

## Executive Summary
"""
        # Check if identifier has known issues
        known_issue = KnownIssuesRegistry.check_identifier(identifier)
        if known_issue:
            report += f"""
⚠️ **Known Issue Detected**
- Type: {known_issue.issue_type}
- Status: {known_issue.investigation_status}
- Description: {known_issue.description}
"""
            if known_issue.workaround:
                report += f"- **Workaround**: {known_issue.workaround}\n"
        
        # Add journey through pipeline
        report += f"""
## Journey Through Pipeline
{DebugReporter._format_journey(identifier, trace_log)}

## Final Status
{DebugReporter._get_final_status(identifier, results)}
"""
        
        # Add data presence analysis
        if source_data is not None or target_data is not None:
            report += f"""
## Data Presence Analysis
{DebugReporter._analyze_data_presence(identifier, source_data, target_data)}
"""
        
        # Add known issues section
        report += f"""
## Known Issues Check
{DebugReporter._check_known_issues(identifier)}
"""
        
        # Add recommendations
        report += f"""
## Recommendations
{DebugReporter._generate_recommendations(identifier, trace_log, results)}
"""
        
        # Add technical details
        report += f"""
## Technical Details

### Trace Summary
{DebugReporter._summarize_trace(trace_log)}

### Raw Trace Events
```json
{json.dumps(trace_log, indent=2, default=str)}
```
"""
        
        return report
    
    @staticmethod
    def _format_journey(identifier: str, trace_log: List[Dict]) -> str:
        """Format the identifier's journey through the pipeline."""
        if not trace_log:
            return "No trace data available"
        
        journey = []
        for i, entry in enumerate(trace_log, 1):
            if entry.get('identifier') == identifier:
                timestamp = entry.get('timestamp', 'N/A')
                action = entry.get('action', 'Unknown')
                phase = entry.get('phase', 'unknown')
                details = entry.get('details', {})
                
                # Format entry
                journey_entry = f"{i}. **{action}** ({phase})"
                if phase == 'step_failed':
                    journey_entry += f" ❌ Error: {details.get('error', 'Unknown error')}"
                elif phase == 'step_complete':
                    journey_entry += f" ✅ Output: {details.get('output_count', 'N/A')} identifiers"
                else:
                    journey_entry += f" - {details}"
                
                journey.append(journey_entry)
        
        return "\n".join(journey) if journey else "Identifier not found in trace log"
    
    @staticmethod
    def _get_final_status(identifier: str, results: Optional[pd.DataFrame]) -> str:
        """Get the final status of the identifier after processing."""
        if results is None:
            return "No results data available"
        
        if identifier not in results.index and 'identifier' not in results.columns:
            return f"❌ **Not Found**: {identifier} not present in final results"
        
        # Try to find the identifier
        if 'identifier' in results.columns:
            mask = results['identifier'] == identifier
            if mask.any():
                row = results[mask].iloc[0]
                status = f"✅ **Found in Results**\n"
                for col in results.columns:
                    status += f"- {col}: {row[col]}\n"
                return status
        
        return f"⚠️ **Status Unknown**: Unable to determine final status"
    
    @staticmethod
    def _analyze_data_presence(
        identifier: str,
        source_data: Optional[pd.DataFrame],
        target_data: Optional[pd.DataFrame]
    ) -> str:
        """Analyze presence of identifier in source and target data."""
        analysis = ""
        
        if source_data is not None:
            source_found = False
            source_columns = []
            
            for col in source_data.columns:
                if source_data[col].astype(str).str.contains(identifier, na=False).any():
                    source_found = True
                    source_columns.append(col)
            
            if source_found:
                analysis += f"### Source Data\n✅ Found in columns: {', '.join(source_columns)}\n\n"
            else:
                analysis += f"### Source Data\n❌ Not found in any column\n\n"
        
        if target_data is not None:
            target_found = False
            target_columns = []
            
            for col in target_data.columns:
                if target_data[col].astype(str).str.contains(identifier, na=False).any():
                    target_found = True
                    target_columns.append(col)
            
            if target_found:
                analysis += f"### Target Data\n✅ Found in columns: {', '.join(target_columns)}\n"
            else:
                analysis += f"### Target Data\n❌ Not found in any column\n"
        
        return analysis if analysis else "No data provided for analysis"
    
    @staticmethod
    def _check_known_issues(identifier: str) -> str:
        """Check and format known issues for the identifier."""
        issue = KnownIssuesRegistry.check_identifier(identifier)
        
        if not issue:
            return "✅ No known issues for this identifier"
        
        issues_text = f"""
### Issue Details
- **Identifier**: {issue.identifier}
- **Type**: {issue.issue_type}
- **Status**: {issue.investigation_status}
- **First Observed**: {issue.first_observed}
- **Last Verified**: {issue.last_verified}

### Description
{issue.description}

### Affected Datasets
{', '.join(issue.affected_datasets)}
"""
        
        if issue.workaround:
            issues_text += f"""
### Workaround
{issue.workaround}
"""
        
        if issue.resolution:
            issues_text += f"""
### Resolution
{issue.resolution}
"""
        
        if issue.related_files:
            issues_text += f"""
### Related Files
{chr(10).join(['- ' + f for f in issue.related_files])}
"""
        
        return issues_text
    
    @staticmethod
    def _generate_recommendations(
        identifier: str,
        trace_log: List[Dict],
        results: Optional[pd.DataFrame]
    ) -> str:
        """Generate actionable recommendations based on analysis."""
        recommendations = []
        
        # Check for known issues
        issue = KnownIssuesRegistry.check_identifier(identifier)
        if issue and issue.workaround:
            recommendations.append(f"💡 **Apply Known Workaround**: {issue.workaround}")
        
        # Analyze trace for failures
        failures = [e for e in trace_log if e.get('phase') == 'step_failed']
        if failures:
            recommendations.append(f"🔧 **Debug Failures**: {len(failures)} step(s) failed during processing")
            for failure in failures[:3]:  # Show first 3 failures
                recommendations.append(f"  - {failure.get('action', 'Unknown')}: {failure.get('details', {}).get('error', 'Unknown error')}")
        
        # Check if identifier made it through pipeline
        if trace_log:
            last_event = trace_log[-1]
            if last_event.get('phase') != 'step_complete':
                recommendations.append("⚠️ **Incomplete Processing**: Pipeline did not complete successfully")
        
        # Data presence recommendations
        if not recommendations:
            recommendations.append("✅ **No Issues Detected**: Identifier processed normally")
        
        return "\n".join(recommendations)
    
    @staticmethod
    def _summarize_trace(trace_log: List[Dict]) -> str:
        """Provide a summary of the trace log."""
        if not trace_log:
            return "No trace events recorded"
        
        summary = f"""
- Total Events: {len(trace_log)}
- Unique Actions: {len(set(e.get('action', 'unknown') for e in trace_log))}
- Phases: {dict((phase, sum(1 for e in trace_log if e.get('phase') == phase)) for phase in set(e.get('phase', 'unknown') for e in trace_log))}
- Errors: {sum(1 for e in trace_log if 'error' in e.get('details', {}))}
"""
        return summary
    
    @staticmethod
    def save_report(report: str, identifier: str, output_dir: str = "/tmp") -> str:
        """Save the report to a file.
        
        Args:
            report: The report content
            identifier: The identifier being reported on
            output_dir: Directory to save the report
            
        Returns:
            Path to the saved report
        """
        output_path = Path(output_dir) / f"debug_report_{identifier}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w') as f:
            f.write(report)
        
        return str(output_path)
    
    @staticmethod
    def generate_batch_report(identifiers: List[str], trace_logs: Dict[str, List[Dict]]) -> str:
        """Generate a report for multiple problematic identifiers.
        
        Args:
            identifiers: List of identifiers to report on
            trace_logs: Dictionary mapping identifiers to their trace logs
            
        Returns:
            Formatted markdown report for all identifiers
        """
        report = f"""# Batch Debug Report
Generated: {datetime.now().isoformat()}
Total Identifiers: {len(identifiers)}

## Summary
"""
        
        # Check for known issues
        known_issues = []
        unknown_issues = []
        
        for identifier in identifiers:
            if KnownIssuesRegistry.check_identifier(identifier):
                known_issues.append(identifier)
            else:
                unknown_issues.append(identifier)
        
        report += f"""
- Known Issues: {len(known_issues)}
- Unknown Issues: {len(unknown_issues)}

### Known Issues
{', '.join(known_issues) if known_issues else 'None'}

### Unknown Issues
{', '.join(unknown_issues) if unknown_issues else 'None'}

## Individual Reports
"""
        
        for identifier in identifiers:
            trace_log = trace_logs.get(identifier, [])
            report += f"""
---
### {identifier}
{DebugReporter._format_journey(identifier, trace_log)}
{DebugReporter._check_known_issues(identifier)}
"""
        
        return report