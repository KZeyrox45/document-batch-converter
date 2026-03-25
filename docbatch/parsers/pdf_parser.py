"""
PDF document parser using pdfplumber.

This module provides functionality to parse PDF files and extract
text, tables, images, and metadata into structured JSON format.
"""

import re
import time
from pathlib import Path
from typing import List, Optional

import pdfplumber

from docbatch.parsers.base import BaseParser
from docbatch.models import (
    DocumentOutput,
    DocumentMetadata,
    DocumentType,
    Section,
    TableData,
    ImageInfo,
)


class PDFParser(BaseParser):
    """
    Parser for PDF documents using pdfplumber.
    
    Extracts:
    - Text content with page information
    - Tables with headers and rows
    - Image metadata (dimensions, format)
    - Document metadata (author, title, etc.)
    """
    
    SUPPORTED_EXTENSIONS = ['.pdf']
    
    def parse(self, filepath: str) -> DocumentOutput:
        """
        Parse a PDF file and return structured output.
        
        Args:
            filepath: Path to the PDF file.
            
        Returns:
            DocumentOutput containing parsed content.
        """
        self.clear_warnings()
        start_time = time.perf_counter()
        
        filename = Path(filepath).name
        self.logger.info(f"Parsing PDF: {filename}")
        
        # Extract all components
        metadata = self.extract_metadata(filepath)
        full_text = self.extract_text(filepath)
        tables = self.extract_tables(filepath)
        images = self.extract_images(filepath)
        
        # Detect sections
        sections = self._detect_sections_with_pages(filepath, full_text)
        
        elapsed = time.perf_counter() - start_time
        
        return DocumentOutput(
            filename=filename,
            metadata=metadata,
            sections=sections,
            tables=tables,
            images=images,
            warnings=self.warnings.copy(),
            conversion_time=elapsed,
        )
    
    def extract_metadata(self, filepath: str) -> DocumentMetadata:
        """Extract metadata from PDF file."""
        try:
            with pdfplumber.open(filepath) as pdf:
                meta = pdf.metadata or {}
                
                return DocumentMetadata(
                    file_type=DocumentType.PDF.value,
                    pages=len(pdf.pages),
                    author=meta.get('Author'),
                    title=meta.get('Title'),
                    subject=meta.get('Subject'),
                    creator=meta.get('Creator'),
                    created=meta.get('CreationDate'),
                    modified=meta.get('ModDate'),
                )
        except Exception as e:
            self.add_warning("metadata_error", str(e))
            return DocumentMetadata(file_type=DocumentType.PDF.value)
    
    def extract_text(self, filepath: str) -> str:
        """Extract all text from PDF file."""
        text_parts = []
        
        try:
            with pdfplumber.open(filepath) as pdf:
                for i, page in enumerate(pdf.pages):
                    try:
                        page_text = page.extract_text() or ""
                        if page_text.strip():
                            text_parts.append(f"[Page {i + 1}]\n{page_text}")
                    except Exception as e:
                        self.add_warning(
                            "page_extraction_error",
                            str(e),
                            f"page {i + 1}"
                        )
        except Exception as e:
            self.add_warning("file_error", str(e))
            raise
        
        return '\n\n'.join(text_parts)
    
    def extract_tables(self, filepath: str) -> List[TableData]:
        """Extract all tables from PDF file."""
        tables = []
        table_index = 0
        
        try:
            with pdfplumber.open(filepath) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        page_tables = page.extract_tables()
                        for table in page_tables:
                            if not table or not any(table):
                                continue
                            
                            # Clean and process table data
                            cleaned_table = self._clean_table(table)
                            if cleaned_table:
                                headers = cleaned_table[0] if cleaned_table else []
                                rows = cleaned_table[1:] if len(cleaned_table) > 1 else []
                                
                                tables.append(TableData(
                                    index=table_index,
                                    headers=headers,
                                    rows=rows,
                                    page=page_num,
                                ))
                                table_index += 1
                    except Exception as e:
                        self.add_warning(
                            "table_extraction_error",
                            str(e),
                            f"page {page_num}"
                        )
        except Exception as e:
            self.add_warning("file_error", str(e))
            raise
        
        return tables
    
    def extract_images(self, filepath: str) -> List[ImageInfo]:
        """Extract image information from PDF file."""
        images = []
        image_index = 0
        
        try:
            with pdfplumber.open(filepath) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        # Get image information from page
                        for img in page.images:
                            images.append(ImageInfo(
                                index=image_index,
                                width=int(img.get('width', 0)),
                                height=int(img.get('height', 0)),
                                page=page_num,
                            ))
                            image_index += 1
                    except Exception as e:
                        self.add_warning(
                            "image_extraction_error",
                            str(e),
                            f"page {page_num}"
                        )
        except Exception as e:
            self.add_warning("file_error", str(e))
            raise
        
        return images
    
    def _detect_sections_with_pages(self, filepath: str, full_text: str) -> List[Section]:
        """
        Detect sections with page number information.
        
        This method enhances section detection by tracking which page
        each section appears on.
        """
        sections = []
        
        try:
            with pdfplumber.open(filepath) as pdf:
                # Build a map of text positions to pages
                page_texts = []
                for i, page in enumerate(pdf.pages, 1):
                    text = page.extract_text() or ""
                    page_texts.append((i, text))
                
                # Detect sections per page
                all_sections = self.detect_sections(full_text)
                
                # Map sections to pages
                for section in all_sections:
                    page_num = self._find_section_page(section, page_texts)
                    section.page = page_num
                    sections.append(section)
                    
        except Exception as e:
            self.add_warning("section_detection_error", str(e))
            # Fall back to basic section detection
            sections = self.detect_sections(full_text)
        
        return sections
    
    def _find_section_page(self, section: Section, page_texts: List[tuple]) -> Optional[int]:
        """Find which page a section appears on."""
        heading = section.heading.lower()
        
        for page_num, text in page_texts:
            if heading in text.lower():
                return page_num
        
        return None
    
    def _clean_table(self, table: List[List]) -> List[List[str]]:
        """Clean and normalize table data."""
        cleaned = []
        
        for row in table:
            cleaned_row = []
            for cell in row:
                if cell is None:
                    cleaned_row.append("")
                else:
                    # Convert to string and clean whitespace
                    cell_str = str(cell).strip()
                    # Remove excessive whitespace
                    cell_str = re.sub(r'\s+', ' ', cell_str)
                    cleaned_row.append(cell_str)
            
            # Skip completely empty rows
            if any(cell for cell in cleaned_row):
                cleaned.append(cleaned_row)
        
        return cleaned
