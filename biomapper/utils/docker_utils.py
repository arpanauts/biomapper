"""Docker utilities for managing containers."""

import logging
import subprocess

logger = logging.getLogger(__name__)


class DockerManager:
    """Manages Docker containers for the pipeline."""

    def __init__(self) -> None:
        self.logger = logging.getLogger("docker_manager")

    def start_qdrant(self) -> bool:
        """Start Qdrant container."""
        try:
            # Check if already running
            result = subprocess.run(
                ["docker", "ps", "--filter", "name=qdrant", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
            )

            if "qdrant" in result.stdout:
                self.logger.info("Qdrant container already running")
                return True

            # Start container
            cmd = [
                "docker",
                "run",
                "-d",
                "--name",
                "qdrant",
                "-p",
                "6333:6333",
                "-v",
                "./qdrant_storage:/qdrant/storage",
                "qdrant/qdrant",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True)
            return result.returncode == 0

        except Exception as e:
            self.logger.error(f"Error starting Qdrant: {e}")
            return False

    def stop_qdrant(self) -> bool:
        """Stop Qdrant container."""
        try:
            subprocess.run(["docker", "stop", "qdrant"], capture_output=True)
            subprocess.run(["docker", "rm", "qdrant"], capture_output=True)
            return True
        except Exception as e:
            self.logger.error(f"Error stopping Qdrant: {e}")
            return False
