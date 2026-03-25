"""
Tests for the data models module.

This module tests the JSON output structures and model classes.
"""

import pytest

from docbatch.models import (
    DocumentOutput,
    DocumentMetadata,
    DocumentType,
    Section,
    TableData,
    ImageInfo,
    ConversionWarning,
    SlideContent,
    SECTION_PATTERNS,
    HEADING_KEYWORDS,
)


class TestTableData:
    """Tests for TableData model."""
    
    def test_table_creation(self):
        """Test creating a TableData instance."""
        table = TableData(
            index=0,
            headers=["Name", "Age"],
            rows=[["Alice", "30"], ["Bob", "25"]],
            page=1,
        )
        
        assert table.index == 0
        assert table.headers == ["Name", "Age"]
        assert len(table.rows) == 2
        assert table.page == 1
        assert table.slide is None
    
    def test_table_to_dict(self):
        """Test converting TableData to dictionary."""
        table = TableData(
            index=1,
            headers=["A", "B"],
            rows=[["1", "2"]],
            slide=3,
        )
        
        result = table.to_dict()
        
        assert result["index"] == 1
        assert result["headers"] == ["A", "B"]
        assert result["slide"] == 3
        assert "page" not in result  # None values should not be included


class TestImageInfo:
    """Tests for ImageInfo model."""
    
    def test_image_creation(self):
        """Test creating an ImageInfo instance."""
        image = ImageInfo(
            index=0,
            width=800,
            height=600,
            format="PNG",
            page=2,
        )
        
        assert image.index == 0
        assert image.width == 800
        assert image.height == 600
        assert image.format == "PNG"
        assert image.page == 2
    
    def test_image_minimal(self):
        """Test creating ImageInfo with minimal data."""
        image = ImageInfo(index=0)
        
        assert image.index == 0
        assert image.width is None
        assert image.height is None


class TestSection:
    """Tests for Section model."""
    
    def test_section_creation(self):
        """Test creating a Section instance."""
        section = Section(
            heading="Introduction",
            content="This is the introduction.",
            level=1,
            page=1,
        )
        
        assert section.heading == "Introduction"
        assert section.content == "This is the introduction."
        assert section.level == 1
        assert section.page == 1
    
    def test_section_with_tables(self):
        """Test Section with embedded tables."""
        table = TableData(index=0, headers=["A", "B"], rows=[["1", "2"]])
        section = Section(
            heading="Data Section",
            content="See table below:",
            tables=[table],
        )
        
        assert len(section.tables) == 1
        result = section.to_dict()
        assert "tables" in result
    
    def test_section_to_dict(self):
        """Test converting Section to dictionary."""
        section = Section(
            heading="Methods",
            content="Methodology content",
            level=2,
            page=5,
        )
        
        result = section.to_dict()
        
        assert result["heading"] == "Methods"
        assert result["content"] == "Methodology content"
        assert result["level"] == 2
        assert result["page"] == 5


class TestSlideContent:
    """Tests for SlideContent model."""
    
    def test_slide_creation(self):
        """Test creating a SlideContent instance."""
        slide = SlideContent(
            slide_number=1,
            title="Introduction",
            content="Welcome to the presentation",
            speaker_notes="Remember to greet the audience",
        )
        
        assert slide.slide_number == 1
        assert slide.title == "Introduction"
        assert slide.content == "Welcome to the presentation"
        assert slide.speaker_notes == "Remember to greet the audience"
    
    def test_slide_to_dict(self):
        """Test converting SlideContent to dictionary."""
        slide = SlideContent(
            slide_number=2,
            title="Overview",
            content="Brief overview",
        )
        
        result = slide.to_dict()
        
        assert result["slide_number"] == 2
        assert result["title"] == "Overview"
        assert "speaker_notes" not in result  # Empty, should not be included


class TestDocumentMetadata:
    """Tests for DocumentMetadata model."""
    
    def test_metadata_creation(self):
        """Test creating DocumentMetadata instance."""
        metadata = DocumentMetadata(
            file_type="pdf",
            pages=10,
            author="Test Author",
            title="Test Document",
        )
        
        assert metadata.file_type == "pdf"
        assert metadata.pages == 10
        assert metadata.author == "Test Author"
    
    def test_metadata_to_dict(self):
        """Test converting metadata to dictionary."""
        metadata = DocumentMetadata(
            file_type="docx",
            pages=5,
            author="Author",
        )
        
        result = metadata.to_dict()
        
        assert result["file_type"] == "docx"
        assert result["pages"] == 5
        assert result["author"] == "Author"
        assert "title" not in result  # None, should not be included


class TestConversionWarning:
    """Tests for ConversionWarning model."""
    
    def test_warning_creation(self):
        """Test creating a ConversionWarning instance."""
        warning = ConversionWarning(
            type="missing_font",
            message="Font 'Arial' not found",
            location="page 5",
        )
        
        assert warning.type == "missing_font"
        assert warning.message == "Font 'Arial' not found"
        assert warning.location == "page 5"
    
    def test_warning_to_dict(self):
        """Test converting warning to dictionary."""
        warning = ConversionWarning(
            type="error",
            message="Test error",
        )
        
        result = warning.to_dict()
        
        assert result["type"] == "error"
        assert result["message"] == "Test error"
        assert "location" not in result


class TestDocumentOutput:
    """Tests for DocumentOutput model."""
    
    def test_output_creation(self):
        """Test creating a DocumentOutput instance."""
        metadata = DocumentMetadata(file_type="pdf", pages=5)
        output = DocumentOutput(
            filename="test.pdf",
            metadata=metadata,
        )
        
        assert output.filename == "test.pdf"
        assert output.metadata.file_type == "pdf"
        assert len(output.sections) == 0
    
    def test_output_with_sections(self):
        """Test DocumentOutput with sections."""
        metadata = DocumentMetadata(file_type="docx", pages=10)
        section = Section(heading="Intro", content="Introduction")
        
        output = DocumentOutput(
            filename="test.docx",
            metadata=metadata,
            sections=[section],
        )
        
        assert len(output.sections) == 1
        result = output.to_dict()
        assert "sections" in result
    
    def test_output_to_json(self):
        """Test converting DocumentOutput to JSON string."""
        metadata = DocumentMetadata(file_type="pdf", pages=1)
        output = DocumentOutput(
            filename="test.pdf",
            metadata=metadata,
            conversion_time=1.234,
        )
        
        json_str = output.to_json()
        
        assert '"filename": "test.pdf"' in json_str
        assert '"file_type": "pdf"' in json_str
        assert '"conversion_time": 1.234' in json_str
    
    def test_output_with_warnings(self):
        """Test DocumentOutput with warnings."""
        metadata = DocumentMetadata(file_type="pdf")
        warning = ConversionWarning(type="test", message="Test warning")
        
        output = DocumentOutput(
            filename="test.pdf",
            metadata=metadata,
            warnings=[warning],
        )
        
        result = output.to_dict()
        assert "warnings" in result
        assert len(result["warnings"]) == 1


class TestSectionPatterns:
    """Tests for section detection patterns."""
    
    def test_numbered_pattern(self):
        """Test that numbered section patterns are defined."""
        import re
        
        pattern = SECTION_PATTERNS[0]
        
        # Should match "1. Introduction"
        match = re.match(pattern, "1. Introduction")
        assert match is not None
        
        # Should match "1.1 Background"
        match = re.match(pattern, "1.1 Background")
        assert match is not None
    
    def test_chapter_pattern(self):
        """Test that chapter patterns are defined."""
        import re
        
        for pattern in SECTION_PATTERNS:
            match = re.match(pattern, "Chapter 1: Introduction", re.IGNORECASE)
            if match:
                assert True
                return
        
        # Chapter pattern should be defined
        assert False, "Chapter pattern not found in SECTION_PATTERNS"
    
    def test_heading_keywords(self):
        """Test that heading keywords are defined."""
        assert "introduction" in HEADING_KEYWORDS
        assert "methodology" in HEADING_KEYWORDS
        assert "conclusion" in HEADING_KEYWORDS
