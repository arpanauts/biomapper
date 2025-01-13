from typing import List, Optional, AsyncGenerator, cast
import xml.etree.ElementTree as ET
from pathlib import Path
import logging
from tqdm.asyncio import tqdm

from ..schemas.metabolite_schema import MetaboliteDocument
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
        count = 0
        try:
            context = ET.iterparse(self.xml_file, events=("end",))
            for _, elem in context:
                if elem.tag.endswith("metabolite"):  # Handle potential namespaces
                    count += 1
                elem.clear()  # Clear to save memory
        except Exception as e:
            logger.error(f"Error counting compounds: {e}")
            raise
        finally:
            logger.info(f"Found {count} compounds in {self.xml_file}")
        return count

    @staticmethod
    def _get_text(element: ET.Element, path: str, default: Optional[str] = None) -> str:
        """Safely extract text from XML element."""
        try:
            # Handle potential namespaces in the XML
            if "/" in path:
                parts = path.split("/")
                node = element
                for part in parts:
                    if node is None:
                        break
                    matches = [n for n in node.findall("*") if n.tag.endswith(part)]
                    node = matches[0] if matches else None
            else:
                matches = [n for n in element.findall("*") if n.tag.endswith(path)]
                node = matches[0] if matches else None
            
            return node.text if node is not None and node.text else default or ""
        except Exception as e:
            logger.warning(f"Error extracting text from {path}: {e}")
            return default or ""

    async def process_batch(self, batch_size: int = 100) -> AsyncGenerator[List[MetaboliteDocument], None]:
        """Process HMDB XML file in batches with progress bar.
        
        Args:
            batch_size: Number of metabolites to process in each batch
            
        Yields:
            List of processed MetaboliteDocument objects
        """
        batch: List[MetaboliteDocument] = []
        processed = 0
        
        try:
            pbar = tqdm(total=self._total_compounds, desc="Processing compounds")
            context = ET.iterparse(self.xml_file, events=("end",))
            
            for _, elem in context:
                if elem.tag.endswith("metabolite"):  # Handle potential namespaces
                    try:
                        # Get all synonyms including IUPAC names
                        synonyms = [
                            cast(str, syn.text) for syn in elem.findall(".//*") 
                            if syn is not None and syn.tag.endswith("synonym") and syn.text and syn.text.strip()
                        ]
                        
                        # Add IUPAC names to synonyms if they exist and aren't already included
                        iupac = self._get_text(elem, "iupac_name")
                        trad_iupac = self._get_text(elem, "traditional_iupac")
                        if iupac and iupac not in synonyms:
                            synonyms.append(iupac)
                        if trad_iupac and trad_iupac not in synonyms:
                            synonyms.append(trad_iupac)
                        
                        doc = MetaboliteDocument(
                            hmdb_id=self._get_text(elem, "accession", "UNKNOWN"),
                            name=self._get_text(elem, "name", "Unknown Compound"),
                            synonyms=synonyms,
                            description=self._get_text(elem, "description")
                        )
                        batch.append(doc)
                        processed += 1
                        pbar.update(1)
                        
                    except Exception as e:
                        logger.error(f"Error processing metabolite: {e}")
                        continue
                    finally:
                        elem.clear()  # Clear to save memory
                    
                    if len(batch) >= batch_size:
                        yield batch
                        batch = []
            
            if batch:  # Return any remaining items
                yield batch
                
        except Exception as e:
            logger.error(f"Error processing XML file: {e}")
            raise
        finally:
            pbar.close()
            logger.info(f"Processed {processed} compounds successfully")
