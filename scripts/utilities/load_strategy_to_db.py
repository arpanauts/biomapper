#!/usr/bin/env python3
"""
Quick utility to load a YAML strategy into the database for the MVP test.
"""
import asyncio
import yaml
from pathlib import Path
from biomapper.core.engine_components.mapping_executor_builder import MappingExecutorBuilder
from biomapper.db.models import MappingStrategy, MappingStrategyStep
from biomapper.core.engine_components.session_manager import SessionManager
from biomapper.core.models.strategy import Strategy

async def load_strategy_to_db():
    """Load the UKBB_HPA_PROTEIN_MAPPING strategy from YAML to database."""
    
    # Read the YAML strategy
    strategy_path = Path("/home/ubuntu/biomapper/configs/ukbb_hpa_mapping.yaml")
    print(f"Loading strategy from: {strategy_path}")
    
    with open(strategy_path, 'r') as f:
        strategy_data = yaml.safe_load(f)
    
    print(f"Strategy data: {strategy_data}")
    print(f"Number of steps: {len(strategy_data['steps'])}")
    
    # Build the executor to get the session manager
    builder = MappingExecutorBuilder()
    executor = await builder.build_async()
    
    # Get database session
    session_manager = executor.session_manager
    
    async with session_manager.get_async_metamapper_session() as session:
        # Check if strategy already exists
        from sqlalchemy import select
        stmt = select(MappingStrategy).where(MappingStrategy.name == strategy_data['name'])
        result = await session.execute(stmt)
        existing = result.scalar_one_or_none()
        if existing:
            print(f"Strategy '{strategy_data['name']}' already exists, deleting...")
            await session.delete(existing)
            await session.commit()
        
        # Create the strategy
        strategy = MappingStrategy(
            name=strategy_data['name'],
            description=strategy_data['description'],
            entity_type="protein",  # This is a protein mapping strategy
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
        
        print(f"Successfully loaded strategy '{strategy_data['name']}' with {len(strategy.steps)} steps to database")

if __name__ == "__main__":
    asyncio.run(load_strategy_to_db())