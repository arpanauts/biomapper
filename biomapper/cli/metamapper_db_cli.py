"""
Command-line interface for managing the metamapper.db database.

This module provides commands for querying, validating, and managing
the metamapper configuration database.
"""

import asyncio
import json
import yaml
import importlib
import logging
from typing import Dict, List, Any, Optional
from pathlib import Path

import click
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from biomapper.config import settings
from biomapper.db.session import get_db_manager
from biomapper.db.models import (
    MappingResource,
    MappingPath,
    MappingPathStep,
    Endpoint,
    EndpointRelationship,
    OntologyPreference,
    PropertyExtractionConfig,
    EndpointPropertyConfig,
    OntologyCoverage,
    Ontology,
    Property,
    RelationshipMappingPath,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


async def get_async_session() -> AsyncSession:
    """Get an async database session for metamapper.db."""
    # Use metamapper_db_url instead of cache_db_url
    db_manager = get_db_manager(db_url=settings.metamapper_db_url)
    return await db_manager.create_async_session()


@click.group("metamapper-db")
def metamapper_db_cli():
    """Commands for managing the metamapper database configuration."""
    pass


# ==================== READ OPERATIONS ====================

@metamapper_db_cli.group("resources")
def resources_group():
    """Commands for managing mapping resources."""
    pass


@resources_group.command("list")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
@click.option("--detailed", is_flag=True, help="Show detailed information")
def list_resources(output_json: bool, detailed: bool):
    """List all mapping resources with their configurations."""
    
    async def _list_resources():
        session = await get_async_session()
        try:
            # Get all resources with their ontology coverage
            stmt = select(MappingResource).order_by(MappingResource.name)
            result = await session.execute(stmt)
            resources = result.scalars().all()
            
            if not resources:
                if not output_json:
                    click.echo("No mapping resources found")
                else:
                    click.echo(json.dumps([]))
                return
            
            resources_data = []
            for resource in resources:
                resource_data = {
                    "id": resource.id,
                    "name": resource.name,
                    "description": resource.description,
                    "resource_type": resource.resource_type,
                    "api_endpoint": resource.api_endpoint,
                    "base_url": resource.base_url,
                    "input_ontology_term": resource.input_ontology_term,
                    "output_ontology_term": resource.output_ontology_term,
                    "client_class_path": resource.client_class_path,
                }
                
                if detailed:
                    # Get ontology coverage for this resource
                    coverage_stmt = select(OntologyCoverage).where(
                        OntologyCoverage.resource_id == resource.id
                    )
                    coverage_result = await session.execute(coverage_stmt)
                    coverage = coverage_result.scalars().all()
                    
                    resource_data["ontology_coverage"] = [
                        {
                            "source_type": c.source_type,
                            "target_type": c.target_type,
                            "support_level": c.support_level,
                        }
                        for c in coverage
                    ]
                    
                    # Get mapping paths that use this resource
                    paths_stmt = select(MappingPathStep.mapping_path_id).where(
                        MappingPathStep.mapping_resource_id == resource.id
                    ).distinct()
                    paths_result = await session.execute(paths_stmt)
                    path_ids = [row[0] for row in paths_result.fetchall()]
                    resource_data["used_in_paths_count"] = len(path_ids)
                
                resources_data.append(resource_data)
            
            if output_json:
                click.echo(json.dumps(resources_data, indent=2))
            else:
                click.echo(f"\nFound {len(resources_data)} mapping resources:\n")
                for resource in resources_data:
                    click.echo(f"ID: {resource['id']} | Name: {resource['name']}")
                    click.echo(f"  Type: {resource['resource_type']}")
                    if resource['input_ontology_term'] and resource['output_ontology_term']:
                        click.echo(f"  Maps: {resource['input_ontology_term']} -> {resource['output_ontology_term']}")
                    if resource['client_class_path']:
                        click.echo(f"  Client: {resource['client_class_path']}")
                    if detailed and "ontology_coverage" in resource:
                        click.echo(f"  Coverage: {len(resource['ontology_coverage'])} ontology pairs")
                        click.echo(f"  Used in paths: {resource['used_in_paths_count']}")
                    if resource['description']:
                        click.echo(f"  Description: {resource['description']}")
                    click.echo()
        finally:
            await session.close()
    
    asyncio.run(_list_resources())


@resources_group.command("show")
@click.argument("resource_name")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def show_resource(resource_name: str, output_json: bool):
    """Show detailed information about a specific resource."""
    
    async def _show_resource():
        session = await get_async_session()
        try:
            stmt = select(MappingResource).where(MappingResource.name == resource_name)
            result = await session.execute(stmt)
            resource = result.scalar_one_or_none()
            
            if not resource:
                click.echo(f"Resource '{resource_name}' not found")
                return
            
            # Get ontology coverage
            coverage_stmt = select(OntologyCoverage).where(
                OntologyCoverage.resource_id == resource.id
            )
            coverage_result = await session.execute(coverage_stmt)
            coverage = coverage_result.scalars().all()
            
            # Get mapping paths that use this resource
            paths_stmt = select(MappingPath, MappingPathStep).join(
                MappingPathStep, MappingPath.id == MappingPathStep.mapping_path_id
            ).where(MappingPathStep.mapping_resource_id == resource.id)
            paths_result = await session.execute(paths_stmt)
            paths = paths_result.all()
            
            # Get property extraction configs
            prop_stmt = select(PropertyExtractionConfig).where(
                PropertyExtractionConfig.resource_id == resource.id
            )
            prop_result = await session.execute(prop_stmt)
            prop_configs = prop_result.scalars().all()
            
            resource_data = {
                "id": resource.id,
                "name": resource.name,
                "description": resource.description,
                "resource_type": resource.resource_type,
                "api_endpoint": resource.api_endpoint,
                "base_url": resource.base_url,
                "input_ontology_term": resource.input_ontology_term,
                "output_ontology_term": resource.output_ontology_term,
                "client_class_path": resource.client_class_path,
                "config_template": resource.config_template,
                "ontology_coverage": [
                    {
                        "source_type": c.source_type,
                        "target_type": c.target_type,
                        "support_level": c.support_level,
                    }
                    for c in coverage
                ],
                "used_in_paths": [
                    {
                        "path_id": path.MappingPath.id,
                        "path_name": path.MappingPath.name,
                        "step_order": path.MappingPathStep.step_order,
                        "source_type": path.MappingPath.source_type,
                        "target_type": path.MappingPath.target_type,
                    }
                    for path in paths
                ],
                "property_extraction_configs": [
                    {
                        "id": prop.id,
                        "ontology_type": prop.ontology_type,
                        "property_name": prop.property_name,
                        "extraction_method": prop.extraction_method,
                        "extraction_pattern": prop.extraction_pattern,
                        "result_type": prop.result_type,
                        "is_active": prop.is_active,
                    }
                    for prop in prop_configs
                ],
            }
            
            if output_json:
                click.echo(json.dumps(resource_data, indent=2))
            else:
                click.echo(f"\nResource: {resource.name}")
                click.echo(f"ID: {resource.id}")
                click.echo(f"Type: {resource.resource_type}")
                click.echo(f"Description: {resource.description or 'N/A'}")
                if resource.input_ontology_term and resource.output_ontology_term:
                    click.echo(f"Maps: {resource.input_ontology_term} -> {resource.output_ontology_term}")
                if resource.client_class_path:
                    click.echo(f"Client Class: {resource.client_class_path}")
                if resource.api_endpoint:
                    click.echo(f"API Endpoint: {resource.api_endpoint}")
                if resource.base_url:
                    click.echo(f"Base URL: {resource.base_url}")
                
                click.echo(f"\nOntology Coverage ({len(coverage)} pairs):")
                for c in coverage:
                    click.echo(f"  {c.source_type} -> {c.target_type} ({c.support_level})")
                
                click.echo(f"\nUsed in Mapping Paths ({len(paths)} paths):")
                for path in paths:
                    click.echo(f"  {path.MappingPath.name} (Step {path.MappingPathStep.step_order})")
                
                if prop_configs:
                    click.echo(f"\nProperty Extraction Configs ({len(prop_configs)} configs):")
                    for prop in prop_configs:
                        click.echo(f"  {prop.ontology_type}.{prop.property_name} -> {prop.extraction_method}")
        finally:
            await session.close()
    
    asyncio.run(_show_resource())


@metamapper_db_cli.group("paths")
def paths_group():
    """Commands for managing mapping paths."""
    pass


@paths_group.command("find")
@click.option("--from", "from_type", required=True, help="Source ontology type")
@click.option("--to", "to_type", required=True, help="Target ontology type")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def find_paths(from_type: str, to_type: str, output_json: bool):
    """Find all possible mapping paths between two ontology types."""
    
    async def _find_paths():
        session = await get_async_session()
        try:
            # Direct paths
            direct_stmt = select(MappingPath).where(
                MappingPath.source_type == from_type,
                MappingPath.target_type == to_type,
                MappingPath.is_active == True
            ).order_by(MappingPath.priority)
            
            direct_result = await session.execute(direct_stmt)
            direct_paths = direct_result.scalars().all()
            
            # Get steps for each path
            all_paths = []
            for path in direct_paths:
                steps_stmt = select(MappingPathStep, MappingResource).join(
                    MappingResource, MappingPathStep.mapping_resource_id == MappingResource.id
                ).where(MappingPathStep.mapping_path_id == path.id).order_by(MappingPathStep.step_order)
                steps_result = await session.execute(steps_stmt)
                steps = steps_result.all()
                
                path_data = {
                    "id": path.id,
                    "name": path.name,
                    "source_type": path.source_type,
                    "target_type": path.target_type,
                    "priority": path.priority,
                    "performance_score": path.performance_score,
                    "success_rate": path.success_rate,
                    "steps": [
                        {
                            "step_order": step.MappingPathStep.step_order,
                            "resource_name": step.MappingResource.name,
                            "resource_type": step.MappingResource.resource_type,
                            "client_class_path": step.MappingResource.client_class_path,
                        }
                        for step in steps
                    ],
                }
                all_paths.append(path_data)
            
            if output_json:
                click.echo(json.dumps(all_paths, indent=2))
            else:
                if not all_paths:
                    click.echo(f"No mapping paths found from {from_type} to {to_type}")
                else:
                    click.echo(f"\nFound {len(all_paths)} paths from {from_type} to {to_type}:\n")
                    for path in all_paths:
                        click.echo(f"Path: {path['name']} (Priority: {path['priority']})")
                        if path['performance_score']:
                            click.echo(f"  Performance Score: {path['performance_score']:.2f}")
                        if path['success_rate']:
                            click.echo(f"  Success Rate: {path['success_rate']:.2%}")
                        click.echo(f"  Steps ({len(path['steps'])}):")
                        for step in path['steps']:
                            click.echo(f"    {step['step_order']}. {step['resource_name']} ({step['resource_type']})")
                        click.echo()
        finally:
            await session.close()
    
    asyncio.run(_find_paths())


# ==================== VALIDATION OPERATIONS ====================

@metamapper_db_cli.group("validate")
def validate_group():
    """Validation operations for the metamapper database."""
    pass


@validate_group.command("clients")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
def validate_clients(output_json: bool):
    """Verify all client_class_paths exist and are importable."""
    
    async def _validate_clients():
        session = await get_async_session()
        try:
            stmt = select(MappingResource).where(MappingResource.client_class_path.isnot(None))
            result = await session.execute(stmt)
            resources = result.scalars().all()
            
            validation_results = []
            
            for resource in resources:
                result_data = {
                    "resource_id": resource.id,
                    "resource_name": resource.name,
                    "client_class_path": resource.client_class_path,
                    "is_valid": False,
                    "error": None,
                }
                
                try:
                    # Try to import the module and get the class
                    module_path, class_name = resource.client_class_path.rsplit(".", 1)
                    module = importlib.import_module(module_path)
                    client_class = getattr(module, class_name)
                    result_data["is_valid"] = True
                except ImportError as e:
                    result_data["error"] = f"ImportError: {str(e)}"
                except AttributeError as e:
                    result_data["error"] = f"AttributeError: {str(e)}"
                except Exception as e:
                    result_data["error"] = f"Error: {str(e)}"
                
                validation_results.append(result_data)
            
            if output_json:
                click.echo(json.dumps(validation_results, indent=2))
            else:
                valid_count = sum(1 for r in validation_results if r["is_valid"])
                total_count = len(validation_results)
                
                click.echo(f"\nClient Class Validation Results: {valid_count}/{total_count} valid\n")
                
                for result in validation_results:
                    status = "✓" if result["is_valid"] else "✗"
                    click.echo(f"{status} {result['resource_name']}")
                    click.echo(f"  Class: {result['client_class_path']}")
                    if result["error"]:
                        click.echo(f"  Error: {result['error']}")
                    click.echo()
        finally:
            await session.close()
    
    asyncio.run(_validate_clients())


# ==================== REGISTRATION ====================

def register_commands(cli):
    """Register the metamapper-db command group with the main CLI."""
    cli.add_command(metamapper_db_cli)


if __name__ == "__main__":
    metamapper_db_cli()