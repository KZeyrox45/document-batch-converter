"""
Tests for the DocumentConverter class.

This module tests the main converter functionality including
single file conversion, batch processing, and error handling.
"""

import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
import json

from docbatch.converter import (
    DocumentConverter,
    UnsupportedFormatError,
    ConversionStats,
)
from docbatch.models import DocumentOutput, DocumentMetadata


class TestConversionStats:
    """Tests for ConversionStats class."""
    
    def test_stats_creation(self):
        """Test creating stats instance."""
        stats = ConversionStats()
        
        assert stats.total_files == 0
        assert stats.successful == 0
        assert stats.skipped == 0
        assert stats.failed == 0
    
    def test_stats_to_dict(self):
        """Test converting stats to dictionary."""
        stats = ConversionStats()
        stats.total_files = 10
        stats.successful = 8
        stats.skipped = 1
        stats.failed = 1
        stats.start_time = 0.0
        stats.end_time = 1.5
        
        result = stats.to_dict()
        
        assert result["total_files"] == 10
        assert result["successful"] == 8
        assert result["elapsed_time"] == 1.5
    
    def test_stats_str(self):
        """Test stats string representation."""
        stats = ConversionStats()
        stats.total_files = 5
        stats.successful = 4
        stats.skipped = 1
        stats.failed = 0
        stats.start_time = 0.0
        stats.end_time = 2.0
        
        result = str(stats)
        
        assert "Processed: 5 files" in result
        assert "Success: 4" in result


class TestDocumentConverter:
    """Tests for DocumentConverter class."""
    
    def test_converter_creation(self):
        """Test creating converter instance."""
        converter = DocumentConverter()
        
        assert converter.skip_errors is True
        assert converter.show_progress is True
    
    def test_converter_custom_settings(self):
        """Test converter with custom settings."""
        converter = DocumentConverter(
            skip_errors=False,
            verbose=True,
            show_progress=False,
        )
        
        assert converter.skip_errors is False
        assert converter.verbose is True
        assert converter.show_progress is False
    
    def test_supported_extensions(self):
        """Test supported extensions list."""
        assert '.pdf' in DocumentConverter.SUPPORTED_EXTENSIONS
        assert '.docx' in DocumentConverter.SUPPORTED_EXTENSIONS
        assert '.pptx' in DocumentConverter.SUPPORTED_EXTENSIONS
    
    def test_is_supported(self):
        """Test is_supported class method."""
        assert DocumentConverter.is_supported("test.pdf")
        assert DocumentConverter.is_supported("test.DOCX")
        assert not DocumentConverter.is_supported("test.xyz")
    
    def test_get_parser_pdf(self):
        """Test getting PDF parser."""
        converter = DocumentConverter()
        
        parser = converter.get_parser('.pdf')
        
        assert parser is not None
    
    def test_get_parser_docx(self):
        """Test getting DOCX parser."""
        converter = DocumentConverter()
        
        parser = converter.get_parser('.docx')
        
        assert parser is not None
    
    def test_get_parser_pptx(self):
        """Test getting PPTX parser."""
        converter = DocumentConverter()
        
        parser = converter.get_parser('.pptx')
        
        assert parser is not None
    
    def test_get_parser_unsupported(self):
        """Test getting parser for unsupported format."""
        converter = DocumentConverter()
        
        with pytest.raises(UnsupportedFormatError):
            converter.get_parser('.xyz')
    
    def test_convert_single_file_pdf(self, sample_pdf):
        """Test converting a single PDF file."""
        converter = DocumentConverter(show_progress=False)
        
        output = converter.convert_file(sample_pdf)
        
        assert output.filename == "sample.pdf"
        assert output.metadata.file_type == "pdf"
    
    def test_convert_single_file_docx(self, sample_docx):
        """Test converting a single DOCX file."""
        converter = DocumentConverter(show_progress=False)
        
        output = converter.convert_file(sample_docx)
        
        assert output.filename == "sample.docx"
        assert output.metadata.file_type == "docx"
    
    def test_convert_single_file_pptx(self, sample_pptx):
        """Test converting a single PPTX file."""
        converter = DocumentConverter(show_progress=False)
        
        output = converter.convert_file(sample_pptx)
        
        assert output.filename == "sample.pptx"
        assert output.metadata.file_type == "pptx"
    
    def test_convert_file_not_found(self):
        """Test handling of nonexistent file."""
        converter = DocumentConverter()
        
        with pytest.raises(FileNotFoundError):
            converter.convert_file("/nonexistent/file.pdf")
    
    def test_convert_unsupported_format(self, unsupported_file):
        """Test handling of unsupported file format."""
        converter = DocumentConverter()
        
        with pytest.raises(UnsupportedFormatError):
            converter.convert_file(unsupported_file)
    
    def test_convert_file_with_output(self, sample_pdf, temp_dir):
        """Test converting file with output path."""
        converter = DocumentConverter(show_progress=False)
        output_path = temp_dir / "output.json"
        
        output = converter.convert_file(sample_pdf, output_path)
        
        assert output_path.exists()
        
        # Verify JSON is valid
        with open(output_path) as f:
            data = json.load(f)
        
        assert data["filename"] == "sample.pdf"
    
    def test_convert_directory(self, sample_files_dir):
        """Test converting a directory of files."""
        converter = DocumentConverter(show_progress=False)
        
        results, stats = converter.convert_directory(sample_files_dir)
        
        assert stats.total_files >= 1
        assert stats.successful >= 1
    
    def test_convert_directory_recursive(self, sample_files_dir, temp_dir):
        """Test recursive directory conversion."""
        # Create subdirectory with a file
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        
        converter = DocumentConverter(show_progress=False)
        
        # Non-recursive
        results, stats = converter.convert_directory(
            sample_files_dir,
            recursive=False
        )
        
        # Recursive
        results, stats = converter.convert_directory(
            sample_files_dir,
            recursive=True
        )
        
        assert stats.total_files >= 1
    
    def test_convert_directory_dry_run(self, sample_files_dir):
        """Test dry run mode."""
        converter = DocumentConverter(show_progress=False)
        
        results, stats = converter.convert_directory(
            sample_files_dir,
            dry_run=True
        )
        
        assert stats.total_files >= 1
        assert stats.successful == 0  # No actual conversion
    
    def test_convert_directory_with_output(self, sample_files_dir, temp_dir):
        """Test directory conversion with output directory."""
        output_dir = temp_dir / "output"
        converter = DocumentConverter(show_progress=False)
        
        results, stats = converter.convert_directory(
            sample_files_dir,
            output_dir=output_dir
        )
        
        assert output_dir.exists()
        # Check that JSON files were created
        json_files = list(output_dir.glob("*.json"))
        assert len(json_files) >= 1
    
    def test_convert_directory_not_found(self):
        """Test handling of nonexistent directory."""
        converter = DocumentConverter()
        
        with pytest.raises(FileNotFoundError):
            converter.convert_directory("/nonexistent/directory")
    
    def test_find_files(self, sample_files_dir):
        """Test file discovery in directory."""
        converter = DocumentConverter(show_progress=False)
        
        files = converter._find_files(sample_files_dir, recursive=False)
        
        assert len(files) >= 1
        assert all(f.is_file() for f in files)
    
    def test_save_output(self, temp_dir):
        """Test saving output to file."""
        converter = DocumentConverter()
        
        metadata = DocumentMetadata(file_type="pdf", pages=1)
        output = DocumentOutput(
            filename="test.pdf",
            metadata=metadata,
        )
        
        output_path = temp_dir / "test.json"
        converter._save_output(output, output_path)
        
        assert output_path.exists()
        
        with open(output_path) as f:
            data = json.load(f)
        
        assert data["filename"] == "test.pdf"
    
    def test_skip_errors_false(self, sample_pdf):
        """Test skip_errors=False behavior."""
        converter = DocumentConverter(skip_errors=False, show_progress=False)
        
        # Should work normally with valid file
        output = converter.convert_file(sample_pdf)
        assert output is not None


class TestConverterIntegration:
    """Integration tests for the converter."""
    
    def test_full_pdf_conversion(self, sample_pdf, temp_dir):
        """Test complete PDF conversion workflow."""
        output_path = temp_dir / "result.json"
        
        converter = DocumentConverter(show_progress=False)
        output = converter.convert_file(sample_pdf, output_path)
        
        # Verify output structure
        assert output.filename == "sample.pdf"
        assert output.metadata.file_type == "pdf"
        assert output.metadata.pages >= 1
        assert output.conversion_time >= 0
        
        # Verify saved file
        assert output_path.exists()
        
        with open(output_path) as f:
            data = json.load(f)
        
        assert "filename" in data
        assert "metadata" in data
    
    def test_full_docx_conversion(self, sample_docx, temp_dir):
        """Test complete DOCX conversion workflow."""
        output_path = temp_dir / "result.json"
        
        converter = DocumentConverter(show_progress=False)
        output = converter.convert_file(sample_docx, output_path)
        
        # Verify output structure
        assert output.filename == "sample.docx"
        assert output.metadata.file_type == "docx"
        
        # Should have tables from our sample
        assert len(output.tables) >= 1
    
    def test_full_pptx_conversion(self, sample_pptx, temp_dir):
        """Test complete PPTX conversion workflow."""
        output_path = temp_dir / "result.json"
        
        converter = DocumentConverter(show_progress=False)
        output = converter.convert_file(sample_pptx, output_path)
        
        # Verify output structure
        assert output.filename == "sample.pptx"
        assert output.metadata.file_type == "pptx"
        
        # Should have slides
        assert len(output.slides) >= 1
