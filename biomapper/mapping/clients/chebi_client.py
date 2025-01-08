"""Client for interacting with the libChEBI API."""

import logging
from dataclasses import dataclass
from typing import Any, Optional, TYPE_CHECKING
import requests

if TYPE_CHECKING:
    from libchebipy import ChebiEntity  # type: ignore

    def chebi_search(query: str) -> list[Any]:
        ...
else:
    try:
        from libchebipy import ChebiEntity, search as chebi_search  # type: ignore
    except ImportError:
        ChebiEntity = Any

        def chebi_search(query: str) -> list[Any]:
            raise ImportError("libchebipy not installed")


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ChEBIConfig:
    """Configuration for ChEBI client."""

    base_url: str = "https://www.ebi.ac.uk/ols/api"
    timeout: int = 30


@dataclass(frozen=True)
class ChEBIResult:
    """Result from ChEBI entity lookup."""

    chebi_id: str
    name: str
    formula: Optional[str] = None
    charge: Optional[int] = None
    mass: Optional[float] = None
    smiles: Optional[str] = None
    inchikey: Optional[str] = None


class ChEBIError(Exception):
    """Custom exception for ChEBI API errors."""


class ChEBIClient:
    """Client for interacting with the ChEBI database."""

    def __init__(self, config: Optional[ChEBIConfig] = None) -> None:
        """Initialize the ChEBI client."""
        self.config = config or ChEBIConfig()
        self.session = requests.Session()

    def _get_safe_property(
        self, getter: Any, error_types: tuple[type[Exception], ...] = (Exception,)
    ) -> Any:
        """Safely get a property value, returning None on error.

        Args:
            getter: Function to call to get the property
            error_types: Tuple of exception types to catch

        Returns:
            Property value or None if an error occurs
        """
        try:
            return getter()
        except error_types:
            return None

    def _get_entity_result(self, entity: ChebiEntity) -> ChEBIResult:
        """Convert ChebiEntity to ChEBIResult.

        Args:
            entity: LibChEBI entity object

        Returns:
            ChEBIResult containing entity information

        Raises:
            ChEBIError: If entity processing fails
        """
        try:
            # Safely get each property with individual try/except blocks
            formula = charge = mass = smiles = None

            try:
                formula = entity.get_formula()
            except (ValueError, AttributeError):
                pass

            try:
                charge = entity.get_charge()
            except (ValueError, AttributeError):
                pass

            try:
                mass = entity.get_mass()
            except (ValueError, AttributeError):
                pass

            try:
                smiles = entity.get_smiles()
            except (ValueError, AttributeError):
                pass

            # Handle ChEBI ID prefix properly
            entity_id = str(entity.get_id())
            if not entity_id.startswith("CHEBI:"):
                entity_id = f"CHEBI:{entity_id}"
            elif entity_id.startswith("CHEBI:CHEBI:"):
                entity_id = entity_id[6:]  # Remove duplicate prefix

            return ChEBIResult(
                chebi_id=entity_id,
                name=entity.get_name(),
                formula=formula,
                charge=charge,
                mass=mass,
                smiles=smiles,
            )
        except Exception as e:
            logger.error("ChEBI entity processing failed: %s", str(e))
            raise ChEBIError(f"Entity processing failed: {str(e)}") from e

    def get_entity_by_id(self, chebi_id: str) -> Optional[ChEBIResult]:
        """Get ChEBI entity information by ID.

        Args:
            chebi_id: ChEBI ID (with or without 'CHEBI:' prefix)

        Returns:
            ChEBIResult containing entity information

        Raises:
            ChEBIError: If entity lookup fails
        """
        try:
            # Strip CHEBI: prefix if present
            clean_id = (
                chebi_id[6:] if chebi_id.upper().startswith("CHEBI:") else chebi_id
            )
            entity = ChebiEntity(clean_id)
            return self._get_entity_result(entity)
        except Exception as e:
            logger.error("ChEBI entity lookup failed: %s", str(e))
            raise ChEBIError(f"Entity lookup failed: {str(e)}") from e

    def search_by_name(
        self, name: str, max_results: int | None = None
    ) -> list[ChEBIResult] | None:
        """Search ChEBI by a compound name, returning a list of ChEBIResult objects.

        Args:
            name: The compound name to search for.
            max_results: Limit on the number of results to return.

        Returns:
            A list of ChEBIResult objects if successful, an empty list if no results,
            or None if an unexpected error occurs.
        """
        try:
            entities = chebi_search(name)
            if not entities:
                return []

            results: list[ChEBIResult] = []
            for entity in entities:
                if max_results is not None and len(results) >= max_results:
                    break
                try:
                    result = self._get_entity_result(entity)
                    results.append(result)
                except ChEBIError:
                    # Skip this entity if it cannot be processed
                    continue

            return results[:max_results] if max_results is not None else results
        except Exception as e:
            logger.error("ChEBI search failed: %s", str(e))
            return None
