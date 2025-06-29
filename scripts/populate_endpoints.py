#!/usr/bin/env python
"""
Quick script to populate endpoints into the database.
"""
import asyncio
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select

from biomapper.db.models import Endpoint

async def populate_endpoints():
    """Create the required endpoints."""
    # Create database connection
    engine = create_async_engine("sqlite+aiosqlite:////home/ubuntu/biomapper/data/metamapper.db")
    AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    endpoints = [
        {
            'name': 'UKBB_PROTEIN_ASSAY_ID',
            'description': 'UK Biobank protein assay identifiers',
            'connection_details': '{"file_path": "/procedure/data/local_data/MAPPING_ONTOLOGIES/ukbb/UKBB_Protein_Meta.tsv"}',
            'type': 'file',
            'primary_property_name': 'Assay'
        },
        {
            'name': 'HPA_GENE_NAME', 
            'description': 'Human Protein Atlas gene names',
            'connection_details': '{"file_path": "/procedure/data/local_data/MAPPING_ONTOLOGIES/isb_osp/hpa_osps.csv"}',
            'type': 'file',
            'primary_property_name': 'gene'
        }
    ]
    
    async with AsyncSessionLocal() as session:
        for ep_data in endpoints:
            # Check if endpoint already exists
            stmt = select(Endpoint).where(Endpoint.name == ep_data['name'])
            result = await session.execute(stmt)
            existing = result.scalar_one_or_none()
            
            if existing:
                print(f"Endpoint '{ep_data['name']}' already exists")
                continue
                
            endpoint = Endpoint(**ep_data)
            session.add(endpoint)
            print(f"Created endpoint: {ep_data['name']}")
        
        await session.commit()

async def main():
    await populate_endpoints()

if __name__ == "__main__":
    asyncio.run(main())