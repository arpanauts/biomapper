"""Transitive relationship builder for entity mappings."""

import datetime
import logging
from collections import defaultdict
from typing import Any, Dict, List, Optional, Set, Tuple

from sqlalchemy import and_, or_, func
from sqlalchemy.orm import Session

from ..cache.manager import CacheManager
from ..db.models import EntityMapping, TransitiveJobLog
from ..db.session import get_session

# Configure logging
logger = logging.getLogger(__name__)


class TransitivityBuilder:
    """Builder for deriving transitive mappings from existing relationships."""

    def __init__(
        self,
        cache_manager: Optional[CacheManager] = None,
        min_confidence: float = 0.5,
        max_chain_length: int = 3,
        confidence_decay: float = 0.9,
    ) -> None:
        """Initialize the transitivity builder.

        Args:
            cache_manager: Cache manager instance
            min_confidence: Minimum confidence for derived mappings
            max_chain_length: Maximum length of derivation chains
            confidence_decay: Factor to reduce confidence with each step
        """
        self.cache_manager = cache_manager or CacheManager()
        self.min_confidence = min_confidence
        self.max_chain_length = max_chain_length
        self.confidence_decay = confidence_decay
        logger.info(
            f"Initialized TransitivityBuilder (min_confidence: {min_confidence}, "
            f"max_chain_length: {max_chain_length}, confidence_decay: {confidence_decay})"
        )

    def _find_candidate_pairs(self, session: Session) -> List[Tuple[int, int]]:
        """Find candidate pairs of mappings that may form transitive relationships.

        Args:
            session: Database session

        Returns:
            List of mapping ID pairs forming potential transitive relationships
        """
        # Find pairs where mapping1.target = mapping2.source
        candidates = []

        # Get all mappings above minimum confidence
        mappings = (
            session.query(EntityMapping)
            .filter(EntityMapping.confidence >= self.min_confidence)
            .all()
        )

        # Build indices for faster lookup
        target_to_mapping: Dict[Tuple[str, str], List[EntityMapping]] = defaultdict(
            list
        )
        source_to_mapping: Dict[Tuple[str, str], List[EntityMapping]] = defaultdict(
            list
        )

        for mapping in mappings:
            target_key = (mapping.target_id, mapping.target_type)
            source_key = (mapping.source_id, mapping.source_type)

            target_to_mapping[target_key].append(mapping)
            source_to_mapping[source_key].append(mapping)

        # Find candidates where mapping1.target = mapping2.source
        for mapping1 in mappings:
            mapping1_target = (mapping1.target_id, mapping1.target_type)

            for mapping2 in source_to_mapping.get(mapping1_target, []):
                # Skip if it would create a self-reference
                if (
                    mapping1.source_id == mapping2.target_id
                    and mapping1.source_type == mapping2.target_type
                ):
                    continue

                # Skip if the pair would create a mapping that already exists
                existing = False
                source_target_key = (
                    (mapping1.source_id, mapping1.source_type),
                    (mapping2.target_id, mapping2.target_type),
                )

                candidates.append((mapping1.id, mapping2.id))

        return candidates

    def _derive_mapping(
        self, session: Session, mapping_chain: List[EntityMapping]
    ) -> Optional[Dict[str, Any]]:
        """Derive a new mapping from a chain of existing mappings.

        Args:
            session: Database session
            mapping_chain: Chain of mappings for derivation

        Returns:
            Dictionary of new derived mapping or None if invalid
        """
        if not mapping_chain or len(mapping_chain) < 2:
            return None

        # First and last mappings determine the end points
        first_mapping = mapping_chain[0]
        last_mapping = mapping_chain[-1]

        # Check for existing direct mapping
        existing = (
            session.query(EntityMapping)
            .filter(
                EntityMapping.source_id == first_mapping.source_id,
                EntityMapping.source_type == first_mapping.source_type,
                EntityMapping.target_id == last_mapping.target_id,
                EntityMapping.target_type == last_mapping.target_type,
            )
            .first()
        )

        if existing:
            # If existing mapping has higher confidence, don't replace it
            if existing.confidence >= self.min_confidence and not existing.is_derived:
                return None

        # Calculate confidence based on chain
        # Confidence decays with each step in the chain
        confidence = 1.0
        for mapping in mapping_chain:
            confidence *= mapping.confidence * self.confidence_decay

        # If confidence falls below threshold, skip
        if confidence < self.min_confidence:
            return None

        # Build derivation path
        derivation_path = [mapping.id for mapping in mapping_chain]

        # Create new mapping
        return {
            "source_id": first_mapping.source_id,
            "source_type": first_mapping.source_type,
            "target_id": last_mapping.target_id,
            "target_type": last_mapping.target_type,
            "confidence": confidence,
            "mapping_source": "derived",
            "is_derived": True,
            "derivation_path": derivation_path,
            "metadata": {
                "derivation_method": "transitive",
                "derivation_date": datetime.datetime.utcnow().isoformat(),
                "derivation_chain_length": str(len(mapping_chain)),
            },
        }

    def build_transitive_mappings(self) -> int:
        """Build transitive mappings from existing relationships.

        Returns:
            Number of new mappings created
        """
        start_time = datetime.datetime.utcnow()
        created_count = 0
        processed_count = 0

        session = get_session()
        try:
            # Create job log entry
            job = TransitiveJobLog(job_date=start_time, status="running")
            session.add(job)
            session.commit()

            # Find candidate pairs
            candidates = self._find_candidate_pairs(session)
            processed_count = len(candidates)

            # Process in batches to avoid memory issues
            batch_size = 1000
            for i in range(0, len(candidates), batch_size):
                batch = candidates[i : i + batch_size]
                batch_mappings = []

                for mapping1_id, mapping2_id in batch:
                    # Get full mapping objects
                    mapping1 = session.query(EntityMapping).get(mapping1_id)
                    mapping2 = session.query(EntityMapping).get(mapping2_id)

                    if not mapping1 or not mapping2:
                        continue

                    # Derive new mapping
                    new_mapping = self._derive_mapping(session, [mapping1, mapping2])

                    if new_mapping:
                        batch_mappings.append(new_mapping)

                # Add derived mappings to cache
                created_count += self.cache_manager.bulk_add_mappings(batch_mappings)

            # Update job log
            duration = (datetime.datetime.utcnow() - start_time).total_seconds()
            job.mappings_processed = processed_count
            job.new_mappings_created = created_count
            job.duration_seconds = duration
            job.status = "completed"
            session.commit()

            logger.info(
                f"Transitive mapping job completed: processed {processed_count} "
                f"candidates, created {created_count} new mappings in {duration:.2f}s"
            )

            return created_count
        except Exception as e:
            # Update job log with error
            if job:
                job.status = f"error: {str(e)}"
                session.commit()

            logger.error(f"Error in transitive mapping job: {e}")
            raise
        finally:
            session.close()

    def build_extended_transitive_mappings(self) -> int:
        """Build extended transitive mappings with chains longer than 2.

        Returns:
            Number of new mappings created
        """
        start_time = datetime.datetime.utcnow()
        created_count = 0
        processed_count = 0

        # Skip if max chain length <= 2
        if self.max_chain_length <= 2:
            logger.info("Skipping extended transitive mapping (max_chain_length <= 2)")
            return 0

        session = get_session()
        try:
            # Create job log entry
            job = TransitiveJobLog(job_date=start_time, status="running_extended")
            session.add(job)
            session.commit()

            # For each chain length from 3 to max_chain_length
            for chain_length in range(3, self.max_chain_length + 1):
                logger.info(f"Building transitive mappings of length {chain_length}")

                # Get all mappings above minimum confidence
                mappings = (
                    session.query(EntityMapping)
                    .filter(EntityMapping.confidence >= self.min_confidence)
                    .all()
                )

                # Build graph of connections
                graph = defaultdict(list)
                for mapping in mappings:
                    source_key = (mapping.source_id, mapping.source_type)
                    target_key = (mapping.target_id, mapping.target_type)

                    graph[source_key].append((target_key, mapping))

                # Find all paths of length chain_length
                paths = []
                for mapping in mappings:
                    source_key = (mapping.source_id, mapping.source_type)

                    # Find all paths starting from this source
                    self._find_paths(graph, source_key, [], set(), chain_length, paths)

                processed_count += len(paths)

                # Process paths in batches
                batch_size = 100
                for i in range(0, len(paths), batch_size):
                    batch = paths[i : i + batch_size]
                    batch_mappings = []

                    for path in batch:
                        # Derive new mapping from path
                        new_mapping = self._derive_mapping(session, path)

                        if new_mapping:
                            batch_mappings.append(new_mapping)

                    # Add derived mappings to cache
                    created_count += self.cache_manager.bulk_add_mappings(
                        batch_mappings
                    )

            # Update job log
            duration = (datetime.datetime.utcnow() - start_time).total_seconds()
            job.mappings_processed = processed_count
            job.new_mappings_created = created_count
            job.duration_seconds = duration
            job.status = "completed_extended"
            session.commit()

            logger.info(
                f"Extended transitive mapping job completed: processed {processed_count} "
                f"paths, created {created_count} new mappings in {duration:.2f}s"
            )

            return created_count
        except Exception as e:
            # Update job log with error
            if job:
                job.status = f"error: {str(e)}"
                session.commit()

            logger.error(f"Error in extended transitive mapping job: {e}")
            raise
        finally:
            session.close()

    def _find_paths(
        self,
        graph: Dict[Tuple[str, str], List[Tuple[Tuple[str, str], EntityMapping]]],
        current: Tuple[str, str],
        path: List[EntityMapping],
        visited: Set[Tuple[str, str]],
        remaining_steps: int,
        result: List[List[EntityMapping]],
    ) -> None:
        """Find all paths of given length in the mapping graph.

        Args:
            graph: Adjacency list representation of mapping graph
            current: Current node (entity ID, type)
            path: Current path of mappings
            visited: Set of visited nodes
            remaining_steps: Remaining steps in the path
            result: List to store found paths
        """
        # If we've seen this node before, skip
        if current in visited:
            return

        # Add to visited set
        visited = visited.union({current})

        # If no more steps needed, we found a valid path
        if remaining_steps == 0:
            if len(path) >= 2:  # Ensure at least 2 mappings
                result.append(path[:])
            return

        # Explore neighbors
        for neighbor, mapping in graph.get(current, []):
            # Skip self-references
            if neighbor == current:
                continue

            # Add mapping to path and continue search
            path.append(mapping)
            self._find_paths(
                graph, neighbor, path, visited, remaining_steps - 1, result
            )
            path.pop()  # Backtrack
