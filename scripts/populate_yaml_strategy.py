#!/usr/bin/env python
"""
Quick script to populate a YAML strategy into the database.
"""
import asyncio
import yaml
from pathlib import Path
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from biomapper.db.models import MappingStrategy, MappingStrategyStep

async def populate_strategy_from_yaml(yaml_path: str):
    """Load a YAML strategy and insert it into the database."""
    # Load YAML
    with open(yaml_path, 'r') as f:
        strategy_data = yaml.safe_load(f)
    
    # Create database connection
    engine = create_async_engine("sqlite+aiosqlite:////home/ubuntu/biomapper/data/metamapper.db")
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        # Check if strategy already exists
        from sqlalchemy import select
        stmt = select(MappingStrategy).where(MappingStrategy.name == strategy_data['name'])
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        
        if existing:
            print(f"Strategy '{strategy_data['name']}' already exists in database")
            return
        
        # Create strategy
        strategy = MappingStrategy(
            name=strategy_data['name'],
            description=strategy_data.get('description', ''),
            entity_type=strategy_data.get('entity_type', 'PROTEIN'),
            is_active=True
        )
        session.add(strategy)
        await session.flush()
        
        # Add steps
        for i, step_config in enumerate(strategy_data.get('steps', [])):
            action = step_config.get('action', {})
            
            # Extract action type
            action_type = action.get('type', '')
            if not action_type and 'action_class_path' in action:
                action_type = action['action_class_path']
            
            # Extract parameters
            if 'params' in action:
                action_params = action['params']
            else:
                action_params = {k: v for k, v in action.items() if k not in ['type', 'action_class_path']}
            
            step = MappingStrategyStep(
                strategy_id=strategy.id,
                step_id=step_config.get('name', f'step_{i+1}'),  # Use 'name' field or generate
                step_order=i + 1,
                description=step_config.get('description', step_config.get('name', '')),
                action_type=action_type,
                action_parameters=action_params,
                is_required=step_config.get('is_required', True),
                is_active=True
            )
            session.add(step)
        
        await session.commit()
        print(f"Successfully populated strategy '{strategy_data['name']}' with {len(strategy_data.get('steps', []))} steps")

async def main():
    yaml_path = "/home/ubuntu/biomapper/configs/ukbb_hpa_analysis_strategy.yaml"
    await populate_strategy_from_yaml(yaml_path)

if __name__ == "__main__":
    asyncio.run(main())