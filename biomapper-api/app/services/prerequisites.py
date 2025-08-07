"""Prerequisite checking service for strategy execution."""

import asyncio
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

import aiohttp

from app.models.strategy_execution import PrerequisiteCheck, PrerequisiteReport

logger = logging.getLogger(__name__)


class PrerequisiteChecker:
    """Check prerequisites before strategy execution."""

    def __init__(self):
        self.checks_performed = 0
        self.checks_passed = 0
        self.checks_failed = 0

    async def check_all(self, strategy: Dict[str, Any]) -> PrerequisiteReport:
        """Run all prerequisite checks for a strategy."""
        report = PrerequisiteReport(
            all_passed=True, checks=[], can_proceed=True, recommendations=[]
        )

        # Reset counters
        self.checks_performed = 0
        self.checks_passed = 0
        self.checks_failed = 0

        # Run all check categories
        checks = []

        # Check input files
        file_checks = await self._check_input_files(strategy)
        checks.extend(file_checks)

        # Check output directories
        dir_checks = await self._check_output_dirs(strategy)
        checks.extend(dir_checks)

        # Check external services
        service_checks = await self._check_services(strategy)
        checks.extend(service_checks)

        # Check API keys and credentials
        credential_checks = await self._check_credentials(strategy)
        checks.extend(credential_checks)

        # Check system resources
        resource_checks = await self._check_system_resources(strategy)
        checks.extend(resource_checks)

        # Check dependencies
        dependency_checks = await self._check_dependencies(strategy)
        checks.extend(dependency_checks)

        # Compile report
        report.checks = checks
        report.total_checks = len(checks)
        report.passed_checks = sum(1 for c in checks if c.passed)
        report.failed_checks = sum(1 for c in checks if not c.passed)

        # Determine if all required checks passed
        required_failed = [c for c in checks if c.required and not c.passed]
        report.all_passed = len(required_failed) == 0
        report.can_proceed = report.all_passed

        # Generate recommendations
        if required_failed:
            report.recommendations.append(
                f"Fix {len(required_failed)} required prerequisite(s) before proceeding:"
            )
            for check in required_failed:
                report.recommendations.append(f"  - {check.name}: {check.message}")

        optional_failed = [c for c in checks if not c.required and not c.passed]
        if optional_failed:
            report.recommendations.append(
                f"Consider fixing {len(optional_failed)} optional prerequisite(s):"
            )
            for check in optional_failed:
                report.recommendations.append(f"  - {check.name}: {check.message}")

        return report

    async def _check_input_files(
        self, strategy: Dict[str, Any]
    ) -> List[PrerequisiteCheck]:
        """Check that all required input files exist and are readable."""
        checks = []

        # Extract file paths from strategy steps
        for step in strategy.get("steps", []):
            params = step.get("params", {})

            # Check for common file parameters
            file_params = [
                params.get("file_path"),
                params.get("input_file"),
                params.get("source_file"),
                params.get("data_file"),
            ]

            for file_path in file_params:
                if file_path and isinstance(file_path, str):
                    check = await self._check_file_exists(
                        file_path,
                        f"Input file for step '{step.get('name', 'unnamed')}'",
                        required=step.get("is_required", True),
                    )
                    checks.append(check)

        return checks

    async def _check_output_dirs(
        self, strategy: Dict[str, Any]
    ) -> List[PrerequisiteCheck]:
        """Check that output directories exist and are writable."""
        checks = []

        # Extract output paths from strategy
        for step in strategy.get("steps", []):
            params = step.get("params", {})

            # Check for common output parameters
            output_params = [
                params.get("output_dir"),
                params.get("output_path"),
                params.get("results_dir"),
            ]

            for dir_path in output_params:
                if dir_path and isinstance(dir_path, str):
                    check = await self._check_directory_writable(
                        dir_path,
                        f"Output directory for step '{step.get('name', 'unnamed')}'",
                        required=True,
                    )
                    checks.append(check)

        # Check default output directory
        default_output = strategy.get("config", {}).get(
            "output_dir", "/tmp/biomapper/results"
        )
        check = await self._check_directory_writable(
            default_output,
            "Default output directory",
            required=True,
            create_if_missing=True,
        )
        checks.append(check)

        return checks

    async def _check_services(
        self, strategy: Dict[str, Any]
    ) -> List[PrerequisiteCheck]:
        """Check that required external services are available."""
        checks = []

        # Check for API dependencies
        services_to_check = set()

        for step in strategy.get("steps", []):
            action_type = step.get("action_type", "")

            # Map action types to required services
            if "CTS" in action_type or "cts" in action_type.lower():
                services_to_check.add("cts")
            if "UNIPROT" in action_type or "uniprot" in action_type.lower():
                services_to_check.add("uniprot")
            if "PUBCHEM" in action_type or "pubchem" in action_type.lower():
                services_to_check.add("pubchem")
            if "HMDB" in action_type or "hmdb" in action_type.lower():
                services_to_check.add("hmdb")

        # Check each service
        service_urls = {
            "cts": "https://cts.fiehnlab.ucdavis.edu/service/heartbeat",
            "uniprot": "https://www.uniprot.org/help/about",
            "pubchem": "https://pubchem.ncbi.nlm.nih.gov/rest/pug/compound/name/water/property/MolecularFormula/JSON",
            "hmdb": "https://hmdb.ca/",
        }

        for service_name in services_to_check:
            if service_name in service_urls:
                check = await self._check_url_accessible(
                    service_urls[service_name],
                    f"{service_name.upper()} API",
                    required=True,
                    timeout=10,
                )
                checks.append(check)

        # Check Qdrant if vector operations are used
        if any(
            "vector" in str(step).lower() or "qdrant" in str(step).lower()
            for step in strategy.get("steps", [])
        ):
            check = await self._check_qdrant_connection()
            checks.append(check)

        return checks

    async def _check_credentials(
        self, strategy: Dict[str, Any]
    ) -> List[PrerequisiteCheck]:
        """Check that required API keys and credentials are configured."""
        checks = []

        # Check for OpenAI API key if LLM operations are used
        if any(
            "llm" in str(step).lower() or "openai" in str(step).lower()
            for step in strategy.get("steps", [])
        ):
            check = PrerequisiteCheck(
                name="OpenAI API Key",
                category="credential",
                passed=bool(os.getenv("OPENAI_API_KEY")),
                message="OpenAI API key is configured"
                if os.getenv("OPENAI_API_KEY")
                else "OpenAI API key not found in environment",
                required=False,
            )
            checks.append(check)

        # Check for other credentials as needed
        # Add more credential checks based on strategy requirements

        return checks

    async def _check_system_resources(
        self, strategy: Dict[str, Any]
    ) -> List[PrerequisiteCheck]:
        """Check system resources (memory, disk space)."""
        checks = []

        # Check available disk space
        import shutil

        stat = shutil.disk_usage("/tmp")
        free_gb = stat.free / (1024**3)

        check = PrerequisiteCheck(
            name="Disk Space",
            category="resource",
            passed=free_gb > 1.0,  # Require at least 1GB free
            message=f"Available disk space: {free_gb:.2f} GB",
            required=True,
            details={"free_gb": free_gb},
        )
        checks.append(check)

        # Check available memory
        import psutil

        mem = psutil.virtual_memory()
        available_gb = mem.available / (1024**3)

        check = PrerequisiteCheck(
            name="Memory",
            category="resource",
            passed=available_gb > 0.5,  # Require at least 500MB free
            message=f"Available memory: {available_gb:.2f} GB",
            required=True,
            details={"available_gb": available_gb, "percent_used": mem.percent},
        )
        checks.append(check)

        return checks

    async def _check_dependencies(
        self, strategy: Dict[str, Any]
    ) -> List[PrerequisiteCheck]:
        """Check that required dependencies are installed."""
        checks = []

        # Check for required Python packages
        required_packages = strategy.get("requirements", {}).get("python", [])

        for package in required_packages:
            try:
                __import__(package)
                check = PrerequisiteCheck(
                    name=f"Python package: {package}",
                    category="dependency",
                    passed=True,
                    message=f"Package {package} is installed",
                    required=True,
                )
            except ImportError:
                check = PrerequisiteCheck(
                    name=f"Python package: {package}",
                    category="dependency",
                    passed=False,
                    message=f"Package {package} is not installed",
                    required=True,
                )
            checks.append(check)

        return checks

    async def _check_file_exists(
        self, file_path: str, description: str, required: bool = True
    ) -> PrerequisiteCheck:
        """Check if a file exists and is readable."""
        path = Path(file_path)
        exists = path.exists() and path.is_file()
        readable = exists and os.access(path, os.R_OK)

        if exists and readable:
            size_mb = path.stat().st_size / (1024 * 1024)
            message = f"File exists and is readable ({size_mb:.2f} MB)"
            passed = True
        elif exists:
            message = "File exists but is not readable"
            passed = False
        else:
            message = f"File does not exist: {file_path}"
            passed = False

        return PrerequisiteCheck(
            name=description,
            category="file",
            passed=passed,
            message=message,
            required=required,
            details={"path": str(file_path), "exists": exists, "readable": readable},
        )

    async def _check_directory_writable(
        self,
        dir_path: str,
        description: str,
        required: bool = True,
        create_if_missing: bool = False,
    ) -> PrerequisiteCheck:
        """Check if a directory exists and is writable."""
        path = Path(dir_path)

        if not path.exists() and create_if_missing:
            try:
                path.mkdir(parents=True, exist_ok=True)
                message = f"Directory created: {dir_path}"
                passed = True
            except Exception as e:
                message = f"Failed to create directory: {e}"
                passed = False
        elif path.exists() and path.is_dir():
            writable = os.access(path, os.W_OK)
            if writable:
                message = "Directory exists and is writable"
                passed = True
            else:
                message = "Directory exists but is not writable"
                passed = False
        elif path.exists():
            message = "Path exists but is not a directory"
            passed = False
        else:
            message = f"Directory does not exist: {dir_path}"
            passed = False

        return PrerequisiteCheck(
            name=description,
            category="directory",
            passed=passed,
            message=message,
            required=required,
            details={"path": str(dir_path)},
        )

    async def _check_url_accessible(
        self, url: str, description: str, required: bool = True, timeout: int = 5
    ) -> PrerequisiteCheck:
        """Check if a URL is accessible."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=timeout) as response:
                    if response.status < 400:
                        message = f"Service is accessible (status: {response.status})"
                        passed = True
                    else:
                        message = f"Service returned error status: {response.status}"
                        passed = False
        except asyncio.TimeoutError:
            message = f"Service request timed out after {timeout} seconds"
            passed = False
        except Exception as e:
            message = f"Failed to connect: {str(e)}"
            passed = False

        return PrerequisiteCheck(
            name=description,
            category="service",
            passed=passed,
            message=message,
            required=required,
            details={"url": url},
        )

    async def _check_qdrant_connection(self) -> PrerequisiteCheck:
        """Check if Qdrant vector database is accessible."""
        qdrant_url = os.getenv("QDRANT_URL", "http://localhost:6333")

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{qdrant_url}/collections", timeout=5
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        collection_count = len(
                            data.get("result", {}).get("collections", [])
                        )
                        message = (
                            f"Qdrant is accessible ({collection_count} collections)"
                        )
                        passed = True
                    else:
                        message = f"Qdrant returned status: {response.status}"
                        passed = False
        except Exception as e:
            message = f"Failed to connect to Qdrant: {str(e)}"
            passed = False

        return PrerequisiteCheck(
            name="Qdrant Vector Database",
            category="service",
            passed=passed,
            message=message,
            required=False,
            details={"url": qdrant_url},
        )
