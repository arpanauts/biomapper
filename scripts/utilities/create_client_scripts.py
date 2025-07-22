#!/usr/bin/env python3
"""
Create client scripts for all protein mapping strategies.
"""

from pathlib import Path

# Define the script template
SCRIPT_TEMPLATE = '''#!/usr/bin/env python
"""
Execute {description} using the MVP action pipeline.

This script demonstrates the complete workflow:
1. Load {source} protein data
2. Load {target} protein data  
3. Merge with UniProt historical resolution
4. Calculate set overlap and generate visualizations

Results are saved to results/{mapping_id}/ directory.
"""
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from biomapper_client import BiomapperClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    """Execute the {description} pipeline."""
    
    logger.info("Starting {description}...")
    
    try:
        # Initialize client using async context manager
        async with BiomapperClient(base_url="http://localhost:8000") as client:
            # Execute strategy
            context = {{
                "source_endpoint_name": "",  # MVP strategies don't use endpoints
                "target_endpoint_name": "",  # MVP strategies don't use endpoints
                "input_identifiers": [],  # MVP strategies load their own data
                "options": {{}}
            }}
            
            result = await client.execute_strategy(
                strategy_name="{strategy_name}",
                context=context
            )
        
        # Log success
        logger.info("✅ {description} completed successfully!")
        
        # Print key results
        if "step_results" in result:
            for step in result["step_results"]:
                if step.get("status") == "success":
                    logger.info(f"  ✅ {{step['step_id']}}: {{step['input_count']}} → {{step['output_count']}}")
                else:
                    logger.error(f"  ❌ {{step['step_id']}}: {{step.get('details', {{}}).get('error', 'Unknown error')}}")
        
        # Check for analysis results
        if "summary" in result and "step_results" in result["summary"]:
            analysis_steps = [s for s in result["summary"]["step_results"] if s.get("action_type") == "CALCULATE_SET_OVERLAP"]
            for step in analysis_steps:
                if step.get("status") == "success":
                    logger.info(f"📊 Analysis complete: {{step['step_id']}}")
                    logger.info(f"📁 Results saved to: results/{mapping_id}/")
        
        return 0
        
    except Exception as e:
        logger.error(f"❌ Pipeline failed: {{e}}")
        logger.exception("Full error details:")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
'''

# Define the mappings
MAPPINGS = [
    {
        "script_name": "run_ukbb_hpa_mapping.py",
        "strategy_name": "UKBB_HPA_PROTEIN_MAPPING",
        "description": "UKBB to HPA protein mapping",
        "source": "UKBB",
        "target": "HPA",
        "mapping_id": "UKBB_HPA"
    },
    {
        "script_name": "run_arivale_spoke_mapping.py",
        "strategy_name": "ARIVALE_SPOKE_PROTEIN_MAPPING",
        "description": "Arivale to SPOKE protein mapping",
        "source": "Arivale",
        "target": "SPOKE",
        "mapping_id": "Arivale_SPOKE"
    },
    {
        "script_name": "run_arivale_kg2c_mapping.py",
        "strategy_name": "ARIVALE_KG2C_PROTEIN_MAPPING",
        "description": "Arivale to KG2C protein mapping",
        "source": "Arivale",
        "target": "KG2C",
        "mapping_id": "Arivale_KG2C"
    },
    {
        "script_name": "run_arivale_ukbb_mapping.py",
        "strategy_name": "ARIVALE_TO_UKBB_PROTEIN_MAPPING",
        "description": "Arivale to UKBB protein mapping",
        "source": "Arivale",
        "target": "UKBB",
        "mapping_id": "Arivale_UKBB"
    },
    {
        "script_name": "run_hpa_qin_mapping.py",
        "strategy_name": "HPA_TO_QIN_PROTEIN_MAPPING",
        "description": "HPA to QIN protein mapping",
        "source": "HPA",
        "target": "QIN",
        "mapping_id": "HPA_QIN"
    },
    {
        "script_name": "run_hpa_spoke_mapping.py",
        "strategy_name": "HPA_TO_SPOKE_PROTEIN_MAPPING",
        "description": "HPA to SPOKE protein mapping",
        "source": "HPA",
        "target": "SPOKE",
        "mapping_id": "HPA_SPOKE"
    },
    {
        "script_name": "run_ukbb_kg2c_mapping.py",
        "strategy_name": "UKBB_TO_KG2C_PROTEIN_MAPPING",
        "description": "UKBB to KG2C protein mapping",
        "source": "UKBB",
        "target": "KG2C",
        "mapping_id": "UKBB_KG2C"
    },
    {
        "script_name": "run_ukbb_qin_mapping.py",
        "strategy_name": "UKBB_TO_QIN_PROTEIN_MAPPING",
        "description": "UKBB to QIN protein mapping",
        "source": "UKBB",
        "target": "QIN",
        "mapping_id": "UKBB_QIN"
    },
    {
        "script_name": "run_ukbb_spoke_mapping.py",
        "strategy_name": "UKBB_TO_SPOKE_PROTEIN_MAPPING",
        "description": "UKBB to SPOKE protein mapping",
        "source": "UKBB",
        "target": "SPOKE",
        "mapping_id": "UKBB_SPOKE"
    }
]

def create_client_scripts():
    """Create all client scripts."""
    
    scripts_dir = Path("/home/ubuntu/biomapper/scripts/main_pipelines")
    scripts_dir.mkdir(exist_ok=True)
    
    for mapping in MAPPINGS:
        script_path = scripts_dir / mapping["script_name"]
        
        # Generate script content
        script_content = SCRIPT_TEMPLATE.format(**mapping)
        
        # Write script
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        # Make executable
        script_path.chmod(0o755)
        
        print(f"✅ Created {mapping['script_name']} for {mapping['strategy_name']}")
    
    print(f"\n🎉 All {len(MAPPINGS)} client scripts created successfully!")

if __name__ == "__main__":
    create_client_scripts()