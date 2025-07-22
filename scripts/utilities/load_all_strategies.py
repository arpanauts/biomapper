#!/usr/bin/env python3
"""
Load all MVP strategies into the database.
"""

import asyncio
import yaml
from pathlib import Path
from biomapper.core.engine_components.mapping_executor_builder import MappingExecutorBuilder
from biomapper.db.models import MappingStrategy, MappingStrategyStep
from sqlalchemy import select

async def load_all_strategies():
    """Load all strategy files into the database."""
    
    # Strategy files to load
    strategy_files = [
        'ukbb_hpa_mapping.yaml',
        'arivale_spoke_mapping.yaml',
        'arivale_kg2c_mapping.yaml',
        'arivale_ukbb_mapping.yaml',
        'hpa_qin_mapping.yaml',
        'hpa_spoke_mapping.yaml',
        'ukbb_kg2c_mapping.yaml',
        'ukbb_qin_mapping.yaml',
        'ukbb_spoke_mapping.yaml'
    ]
    
    # Build executor to get session manager
    builder = MappingExecutorBuilder()
    executor = await builder.build_async()
    session_manager = executor.session_manager
    
    configs_dir = Path('/home/ubuntu/biomapper/configs')
    
    async with session_manager.get_async_metamapper_session() as session:
        for file_name in strategy_files:
            file_path = configs_dir / file_name
            
            if not file_path.exists():
                print(f"❌ File not found: {file_path}")
                continue
                
            print(f"📄 Loading {file_name}...")
            
            with open(file_path, 'r') as f:
                strategy_data = yaml.safe_load(f)
            
            # Check if strategy already exists
            stmt = select(MappingStrategy).where(MappingStrategy.name == strategy_data['name'])
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"  🔄 Updating existing strategy: {strategy_data['name']}")
                await session.delete(existing)
                await session.commit()
            else:
                print(f"  ✨ Creating new strategy: {strategy_data['name']}")
            
            # Create new strategy
            strategy = MappingStrategy(
                name=strategy_data['name'],
                description=strategy_data['description'],
                entity_type="protein",
                is_active=True
            )
            
            # Add steps
            for i, step_data in enumerate(strategy_data['steps']):
                step = MappingStrategyStep(
                    step_id=step_data['name'],
                    step_order=i,
                    action_type=step_data['action']['type'],
                    action_parameters=step_data['action']['params']
                )
                strategy.steps.append(step)
            
            # Save to database
            session.add(strategy)
            await session.commit()
            
            print(f"  ✅ Successfully loaded {strategy_data['name']} with {len(strategy.steps)} steps")
    
    print(f"\n🎉 All strategies loaded successfully!")

if __name__ == "__main__":
    asyncio.run(load_all_strategies())