"""
Base parser class for document conversion.

This module defines the abstract base class that all document parsers
must implement, providing a consistent interface for document conversion.
"""

from abc import ABC, abstractmethod
from typing import Optional, List, Tuple
import re
import time
import logging

from docbatch.models import (
    DocumentOutput,
    DocumentMetadata,
    Section,
    TableData,
    ImageInfo,
    ConversionWarning,
    SECTION_PATTERNS,
    HEADING_KEYWORDS,
)


logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """
    Abstract base class for document parsers.
    
    All document parsers (PDF, DOCX, PPTX) must inherit from this class
    and implement the abstract methods.
    """
    
    # Supported file extensions for this parser
    SUPPORTED_EXTENSIONS: List[str] = []
    
    def __init__(self):
        """Initialize the parser."""
        self.warnings: List[ConversionWarning] = []
        self.logger = logging.getLogger(self.__class__.__name__)
    
    @classmethod
    def supports_file(cls, filepath: str) -> bool:
        """Check if this parser supports the given file."""
        return any(
            filepath.lower().endswith(ext) 
            for ext in cls.SUPPORTED_EXTENSIONS
        )
    
    @abstractmethod
    def parse(self, filepath: str) -> DocumentOutput:
        """
        Parse the document and return structured output.
        
        Args:
            filepath: Path to the document file.
            
        Returns:
            DocumentOutput containing the parsed content.
        """
        pass
    
    @abstractmethod
    def extract_metadata(self, filepath: str) -> DocumentMetadata:
        """
        Extract metadata from the document.
        
        Args:
            filepath: Path to the document file.
            
        Returns:
            DocumentMetadata containing document metadata.
        """
        pass
    
    @abstractmethod
    def extract_text(self, filepath: str) -> str:
        """
        Extract all text content from the document.
        
        Args:
            filepath: Path to the document file.
            
        Returns:
            Complete text content of the document.
        """
        pass
    
    @abstractmethod
    def extract_tables(self, filepath: str) -> List[TableData]:
        """
        Extract all tables from the document.
        
        Args:
            filepath: Path to the document file.
            
        Returns:
            List of TableData objects.
        """
        pass
    
    @abstractmethod
    def extract_images(self, filepath: str) -> List[ImageInfo]:
        """
        Extract information about images in the document.
        
        Args:
            filepath: Path to the document file.
            
        Returns:
            List of ImageInfo objects.
        """
        pass
    
    def detect_sections(self, text: str) -> List[Section]:
        """
        Detect sections in text using explicit markers.
        
        This method identifies sections based on common patterns like:
        - "1. Introduction"
        - "Chapter 1: Background"
        - "Section 1.1 Methods"
        
        Args:
            text: Full text content of the document.
            
        Returns:
            List of detected Section objects.
        """
        sections = []
        lines = text.split('\n')
        
        # Track section boundaries
        section_starts: List[Tuple[int, str, int]] = []  # (line_idx, heading, level)
        
        for i, line in enumerate(lines):
            line = line.strip()
            if not line:
                continue
            
            # Check against section patterns
            for pattern in SECTION_PATTERNS:
                match = re.match(pattern, line, re.IGNORECASE)
                if match:
                    groups = match.groups()
                    if len(groups) >= 2:
                        # Extract heading text
                        heading_text = groups[-1].strip() if groups[-1] else line
                        # Determine level based on numbering
                        level = self._calculate_heading_level(groups[0])
                        section_starts.append((i, heading_text, level))
                        break
            else:
                # Check for heading keywords (single-line headings)
                line_lower = line.lower().strip()
                if line_lower in HEADING_KEYWORDS or any(
                    line_lower.startswith(kw + ':') or line_lower.startswith(kw + ' ')
                    for kw in HEADING_KEYWORDS
                ):
                    # Check if it's likely a heading (short line, possibly all caps or title case)
                    if len(line) < 100 and (
                        line.isupper() or 
                        line.istitle() or
                        line_lower in HEADING_KEYWORDS
                    ):
                        section_starts.append((i, line, 1))
        
        # Create sections from detected boundaries
        for idx, (start_line, heading, level) in enumerate(section_starts):
            # Determine content end (next section or end of document)
            if idx + 1 < len(section_starts):
                end_line = section_starts[idx + 1][0]
            else:
                end_line = len(lines)
            
            # Extract content between sections
            content_lines = lines[start_line + 1:end_line]
            content = '\n'.join(content_lines).strip()
            
            # Skip empty sections
            if content or heading:
                sections.append(Section(
                    heading=heading,
                    content=content,
                    level=level,
                ))
        
        # If no sections detected, create a single section with all content
        if not sections and text.strip():
            sections.append(Section(
                heading="Document Content",
                content=text.strip(),
                level=1,
            ))
        
        return sections
    
    def _calculate_heading_level(self, numbering: str) -> int:
        """
        Calculate heading level from section numbering.
        
        Examples:
            "1" -> level 1
            "1.1" -> level 2
            "1.1.1" -> level 3
            "I" -> level 1
            "A" -> level 1
        """
        if '.' in numbering:
            # Count dots to determine level
            return numbering.count('.') + 1
        elif numbering.isdigit():
            return 1
        elif re.match(r'^[IVXLCDM]+$', numbering, re.IGNORECASE):
            return 1
        elif numbering.isalpha() and len(numbering) == 1:
            return 1
        return 1
    
    def add_warning(self, warning_type: str, message: str, location: Optional[str] = None):
        """Add a conversion warning."""
        warning = ConversionWarning(
            type=warning_type,
            message=message,
            location=location,
        )
        self.warnings.append(warning)
        self.logger.warning(f"{warning_type}: {message}" + (f" at {location}" if location else ""))
    
    def clear_warnings(self):
        """Clear all warnings."""
        self.warnings.clear()
    
    def time_conversion(self, func, *args, **kwargs) -> Tuple[float, any]:
        """
        Time a conversion operation.
        
        Returns:
            Tuple of (elapsed_time, result)
        """
        start = time.perf_counter()
        result = func(*args, **kwargs)
        elapsed = time.perf_counter() - start
        return elapsed, result
