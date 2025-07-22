#!/usr/bin/env python
"""Quick script to check what strategies are in metamapper.db"""
import asyncio
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from biomapper.db.models import MappingStrategy, MappingStrategyStep

async def check_strategies():
    """Check what strategies are in the database."""
    engine = create_async_engine("sqlite+aiosqlite:///data/metamapper.db")
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    async with AsyncSessionLocal() as session:
        # Get all strategies
        stmt = select(MappingStrategy)
        result = await session.execute(stmt)
        strategies = result.scalars().all()
        
        print(f"Found {len(strategies)} strategies in database:")
        for strategy in strategies:
            print(f"\n- {strategy.name} (Entity: {strategy.entity_type})")
            print(f"  Description: {strategy.description[:100]}...")
            
            # Get steps for this strategy
            stmt_steps = select(MappingStrategyStep).where(MappingStrategyStep.strategy_id == strategy.id).order_by(MappingStrategyStep.step_order)
            result_steps = await session.execute(stmt_steps)
            steps = result_steps.scalars().all()
            
            print(f"  Steps ({len(steps)}):")
            for step in steps:
                print(f"    {step.step_order}. {step.step_id} - {step.action_type}")

if __name__ == "__main__":
    asyncio.run(check_strategies())