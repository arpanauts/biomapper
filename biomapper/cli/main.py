"""
Main entry point for the Biomapper CLI.

This module initializes the main Click group and registers
command groups from other CLI modules.
"""

import click
import logging

# Import registration functions from command modules
from biomapper.cli import metadata_commands

# Configure basic logging for CLI
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


@click.group()
@click.version_option(package_name="biomapper")  # Reads version from pyproject.toml
def cli():
    """Biomapper: Unified toolkit for biological data mapping & harmonization."""
    pass


# Register command groups from modules
metadata_commands.register_commands(cli)

if __name__ == "__main__":
    cli()
