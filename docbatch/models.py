"""
Data models for document conversion output structures.

This module defines the JSON schema for section-aware document conversion,
including metadata, sections, tables, and images.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional
from enum import Enum
import json


class DocumentType(Enum):
    """Supported document types."""
    PDF = "pdf"
    DOCX = "docx"
    PPTX = "pptx"
    XLSX = "xlsx"


@dataclass
class TableData:
    """Represents a table extracted from a document."""
    index: int  # Table index in the document
    headers: List[str] = field(default_factory=list)
    rows: List[List[str]] = field(default_factory=list)
    page: Optional[int] = None  # Page number (for PDF)
    slide: Optional[int] = None  # Slide number (for PPTX)
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None or k in ['headers', 'rows', 'index']}


@dataclass
class ImageInfo:
    """Represents an image found in a document."""
    index: int  # Image index in the document
    width: Optional[int] = None
    height: Optional[int] = None
    format: Optional[str] = None  # e.g., "PNG", "JPEG"
    page: Optional[int] = None
    slide: Optional[int] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None or k == 'index'}


@dataclass
class Section:
    """Represents a section in a document with heading and content."""
    heading: str
    content: str
    level: int = 1  # Heading level (1 = main, 2 = subsection, etc.)
    page: Optional[int] = None  # Page number where section starts
    slide: Optional[int] = None  # Slide number (for PPTX)
    tables: List[TableData] = field(default_factory=list)
    images: List[ImageInfo] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "heading": self.heading,
            "content": self.content,
            "level": self.level,
        }
        if self.page is not None:
            result["page"] = self.page
        if self.slide is not None:
            result["slide"] = self.slide
        if self.tables:
            result["tables"] = [t.to_dict() for t in self.tables]
        if self.images:
            result["images"] = [i.to_dict() for i in self.images]
        return result


@dataclass
class SlideContent:
    """Represents content from a single slide (PPTX specific)."""
    slide_number: int
    title: Optional[str] = None
    content: str = ""
    speaker_notes: str = ""
    tables: List[TableData] = field(default_factory=list)
    images: List[ImageInfo] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "slide_number": self.slide_number,
            "content": self.content,
        }
        if self.title:
            result["title"] = self.title
        if self.speaker_notes:
            result["speaker_notes"] = self.speaker_notes
        if self.tables:
            result["tables"] = [t.to_dict() for t in self.tables]
        if self.images:
            result["images"] = [i.to_dict() for i in self.images]
        return result


@dataclass
class DocumentMetadata:
    """Metadata extracted from a document."""
    file_type: str
    pages: Optional[int] = None
    slides: Optional[int] = None  # For PPTX
    author: Optional[str] = None
    title: Optional[str] = None
    subject: Optional[str] = None
    creator: Optional[str] = None
    created: Optional[str] = None
    modified: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class ConversionWarning:
    """Represents a warning during conversion."""
    type: str  # e.g., "corrupted_file", "missing_font", "unsupported_element"
    message: str
    location: Optional[str] = None  # e.g., "page 5", "slide 3"
    
    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class DocumentOutput:
    """
    Main output structure for converted documents.
    
    This is the section-aware JSON structure that includes:
    - filename and metadata
    - sections with headings, content, tables, and images
    - slides (for PPTX)
    - conversion warnings
    """
    filename: str
    metadata: DocumentMetadata
    sections: List[Section] = field(default_factory=list)
    slides: List[SlideContent] = field(default_factory=list)  # PPTX specific
    tables: List[TableData] = field(default_factory=list)  # Document-level tables
    images: List[ImageInfo] = field(default_factory=list)  # Document-level images
    warnings: List[ConversionWarning] = field(default_factory=list)
    conversion_time: float = 0.0  # Time in seconds
    
    def to_dict(self) -> Dict[str, Any]:
        result = {
            "filename": self.filename,
            "metadata": self.metadata.to_dict(),
            "conversion_time": round(self.conversion_time, 3),
        }
        
        if self.sections:
            result["sections"] = [s.to_dict() for s in self.sections]
        
        if self.slides:
            result["slides"] = [s.to_dict() for s in self.slides]
        
        if self.tables:
            result["tables"] = [t.to_dict() for t in self.tables]
        
        if self.images:
            result["images"] = [i.to_dict() for i in self.images]
        
        if self.warnings:
            result["warnings"] = [w.to_dict() for w in self.warnings]
        
        return result
    
    def to_json(self, indent: int = 2) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), indent=indent, ensure_ascii=False)


# Section detection patterns for explicit markers
SECTION_PATTERNS = [
    # Numbered sections: "1. Introduction", "1.1 Background", "Chapter 1"
    r'^(\d+(?:\.\d+)*)\s*[.\)]?\s*(.+)$',
    # Chapter markers: "Chapter 1", "CHAPTER 1"
    r'^[Cc]hapter\s+(\d+)\s*[:\-]?\s*(.*)$',
    # Part markers: "Part 1", "PART I"
    r'^[Pp]art\s+([IVXLCDM]+|\d+)\s*[:\-]?\s*(.*)$',
    # Section markers: "Section 1", "SECTION 1"
    r'^[Ss]ection\s+(\d+)\s*[:\-]?\s*(.*)$',
    # Appendix: "Appendix A", "APPENDIX A"
    r'^[Aa]ppendix\s+([A-Z])\s*[:\-]?\s*(.*)$',
]

# Common heading keywords (for additional detection)
HEADING_KEYWORDS = [
    'introduction', 'background', 'methodology', 'methods', 'results',
    'discussion', 'conclusion', 'abstract', 'summary', 'overview',
    'references', 'bibliography', 'appendix', 'acknowledgements',
    'table of contents', 'contents', 'list of figures', 'list of tables',
]
