from abc import ABC, abstractmethod
from typing import List, AsyncGenerator

from ..schemas.domain_schema import DomainDocument


class BaseDataProcessor(ABC):
    """Base class for all data processors."""

    @abstractmethod
    async def process_batch(
        self, batch_size: int = 100
    ) -> AsyncGenerator[List[DomainDocument], None]:
        """Process data in batches.

        Args:
            batch_size: Number of items to process in each batch

        Yields:
            List of processed DomainDocument objects
        """
        pass
