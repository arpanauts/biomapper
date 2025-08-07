"""Base classes for data processors."""

from abc import ABC, abstractmethod
from typing import Any, AsyncGenerator, List


class BaseDataProcessor(ABC):
    """Base class for data processors."""

    @abstractmethod
    async def process_batch(
        self, batch_size: int = 100
    ) -> AsyncGenerator[List[Any], None]:
        """Process data in batches.

        Args:
            batch_size: Number of items to process in each batch

        Yields:
            Lists of processed data items
        """
        pass
