from pathlib import Path
from typing import List, Optional, AsyncGenerator, cast, Any
import xml.etree.ElementTree as ET
import logging
from tqdm.asyncio import tqdm

from ..schemas.domain_schema import DomainDocument, DomainType
from .base import BaseDataProcessor

logger = logging.getLogger(__name__)


class HMDBProcessor(BaseDataProcessor):
    """Process HMDB metabolite XML data, focusing on names and identifiers."""

    xml_file: Path
    _total_compounds: int

    def __init__(self, xml_file: Path) -> None:
        """Initialize with path to HMDB XML file.

        Args:
            xml_file: Path to HMDB metabolites XML file
        """
        self.xml_file = xml_file
        self._total_compounds = self._count_compounds()
        logger.info(f"Found {self._total_compounds} compounds in {xml_file}")

    def _count_compounds(self) -> int:
        """Count total number of compounds in XML file."""
        try:
            tree = ET.parse(self.xml_file)
            root = tree.getroot()
            return len(root.findall(".//metabolite"))
        except Exception as e:
            logger.error(f"Error counting compounds: {e}")
            return 0

    @staticmethod
    def _get_text(element: ET.Element, path: str, default: Optional[str] = None) -> str:
        """Safely extract text from XML element."""
        try:
            matches = element.findall(path)
            if not matches:
                return default or ""

            node = matches[0] if matches else None

            return node.text if node is not None and node.text else default or ""
        except Exception as e:
            logger.warning(f"Error extracting text from {path}: {e}")
            return default or ""

    async def process_batch(
        self, batch_size: int = 100
    ) -> AsyncGenerator[List[DomainDocument], None]:
        """Process HMDB XML file in batches with progress bar.

        Args:
            batch_size: Number of metabolites to process in each batch

        Yields:
            List of processed DomainDocument objects
        """
        batch: List[DomainDocument] = []
        processed = 0

        try:
            tree = ET.parse(self.xml_file)
            root = tree.getroot()
            compounds = root.findall(".//metabolite")

            for compound in tqdm(
                compounds,
                total=self._total_compounds,
                desc="Processing compounds",
            ):
                try:
                    # Get all synonyms including IUPAC names
                    synonyms = [
                        cast(str, syn.text)
                        for syn in compound.findall(".//*")
                        if syn is not None
                        and syn.tag.endswith("synonym")
                        and syn.text
                        and syn.text.strip()
                    ]

                    # Add IUPAC names to synonyms if they exist and aren't already included
                    iupac = self._get_text(compound, "iupac_name")
                    trad_iupac = self._get_text(compound, "traditional_iupac")
                    if iupac and iupac not in synonyms:
                        synonyms.append(iupac)
                    if trad_iupac and trad_iupac not in synonyms:
                        synonyms.append(trad_iupac)

                    doc = DomainDocument(domain_type=DomainType.COMPOUND)
                    batch.append(doc)
                    processed += 1

                    if len(batch) >= batch_size:
                        yield batch
                        batch = []

                except Exception as e:
                    logger.error(f"Error processing compound: {e}")
                    continue

            if batch:  # Yield any remaining items
                yield batch

        except Exception as e:
            logger.error(f"Error processing XML file: {e}")
            raise

        finally:
            logger.info(f"Processed {processed} compounds")
