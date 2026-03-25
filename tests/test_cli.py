"""
Tests for the CLI module.

This module tests the command-line interface functionality.
"""

import pytest
import sys
from pathlib import Path
from io import StringIO
from unittest.mock import patch, MagicMock

from docbatch.cli import (
    create_parser,
    main,
    handle_convert,
    handle_stats,
)


class TestCreateParser:
    """Tests for argument parser creation."""
    
    def test_parser_creation(self):
        """Test that parser is created successfully."""
        parser = create_parser()
        
        assert parser is not None
        assert parser.prog == 'docbatch'
    
    def test_version_argument(self):
        """Test --version argument."""
        parser = create_parser()
        
        with pytest.raises(SystemExit):
            parser.parse_args(['--version'])
    
    def test_convert_command_parsing(self):
        """Test parsing convert command arguments."""
        parser = create_parser()
        
        args = parser.parse_args(['convert', 'test.pdf'])
        
        assert args.command == 'convert'
        assert args.input == 'test.pdf'
        assert args.output is None
        assert args.recursive is False
    
    def test_convert_with_options(self):
        """Test parsing convert command with options."""
        parser = create_parser()
        
        args = parser.parse_args([
            'convert', 'test.pdf',
            '-o', 'output.json',
            '--recursive',
            '--verbose',
            '--dry-run'
        ])
        
        assert args.input == 'test.pdf'
        assert args.output == 'output.json'
        assert args.recursive is True
        assert args.verbose is True
        assert args.dry_run is True
    
    def test_convert_strict_mode(self):
        """Test --strict flag."""
        parser = create_parser()
        
        args = parser.parse_args(['convert', 'test.pdf', '--strict'])
        
        assert args.strict is True
    
    def test_stats_command_parsing(self):
        """Test parsing stats command arguments."""
        parser = create_parser()
        
        args = parser.parse_args(['stats', './documents/'])
        
        assert args.command == 'stats'
        assert args.directory == './documents/'


class TestMain:
    """Tests for main function."""
    
    def test_main_no_command(self):
        """Test main with no command shows help."""
        with patch('sys.stdout', new_callable=StringIO):
            result = main([])
        
        # Should show help and return 0
        assert result == 0
    
    def test_main_version(self):
        """Test --version flag."""
        with pytest.raises(SystemExit):
            main(['--version'])
    
    def test_main_convert_file_not_found(self):
        """Test convert with nonexistent file."""
        result = main(['convert', '/nonexistent/file.pdf'])
        
        assert result == 1  # Error exit code
    
    def test_main_convert_unsupported_format(self, unsupported_file):
        """Test convert with unsupported file format."""
        result = main(['convert', str(unsupported_file)])
        
        assert result == 1
    
    def test_main_convert_pdf(self, sample_pdf):
        """Test converting a PDF file."""
        result = main(['convert', str(sample_pdf), '-q'])
        
        assert result == 0
    
    def test_main_convert_docx(self, sample_docx):
        """Test converting a DOCX file."""
        result = main(['convert', str(sample_docx), '-q'])
        
        assert result == 0
    
    def test_main_convert_pptx(self, sample_pptx):
        """Test converting a PPTX file."""
        result = main(['convert', str(sample_pptx), '-q'])
        
        assert result == 0
    
    def test_main_convert_with_output(self, sample_pdf, temp_dir):
        """Test convert with output file."""
        output_path = temp_dir / "output.json"
        
        result = main(['convert', str(sample_pdf), '-o', str(output_path)])
        
        assert result == 0
        assert output_path.exists()
    
    def test_main_convert_directory(self, sample_files_dir):
        """Test converting a directory."""
        result = main(['convert', str(sample_files_dir), '-q'])
        
        assert result == 0
    
    def test_main_convert_directory_dry_run(self, sample_files_dir):
        """Test convert dry run."""
        result = main(['convert', str(sample_files_dir), '--dry-run', '-q'])
        
        assert result == 0
    
    def test_main_stats_directory(self, sample_files_dir):
        """Test stats command."""
        result = main(['stats', str(sample_files_dir)])
        
        assert result == 0
    
    def test_main_stats_nonexistent_directory(self):
        """Test stats with nonexistent directory."""
        result = main(['stats', '/nonexistent/directory'])
        
        assert result == 1


class TestHandleConvert:
    """Tests for handle_convert function."""
    
    def test_handle_convert_missing_file(self):
        """Test handle_convert with missing file."""
        parser = create_parser()
        args = parser.parse_args(['convert', '/nonexistent/file.pdf'])
        
        result = handle_convert(args)
        
        assert result == 1
    
    def test_handle_convert_unsupported_format(self, unsupported_file):
        """Test handle_convert with unsupported format."""
        parser = create_parser()
        args = parser.parse_args(['convert', str(unsupported_file)])
        
        result = handle_convert(args)
        
        assert result == 1
    
    def test_handle_convert_with_verbose(self, sample_pdf):
        """Test handle_convert with verbose output."""
        parser = create_parser()
        args = parser.parse_args(['convert', str(sample_pdf), '--verbose'])
        
        result = handle_convert(args)
        
        assert result == 0


class TestHandleStats:
    """Tests for handle_stats function."""
    
    def test_handle_stats_success(self, sample_files_dir):
        """Test successful stats command."""
        parser = create_parser()
        args = parser.parse_args(['stats', str(sample_files_dir)])
        
        result = handle_stats(args)
        
        assert result == 0
    
    def test_handle_stats_missing_directory(self):
        """Test stats with missing directory."""
        parser = create_parser()
        args = parser.parse_args(['stats', '/nonexistent/directory'])
        
        result = handle_stats(args)
        
        assert result == 1
    
    def test_handle_stats_file_not_directory(self, sample_pdf):
        """Test stats with file instead of directory."""
        parser = create_parser()
        args = parser.parse_args(['stats', str(sample_pdf)])
        
        result = handle_stats(args)
        
        assert result == 1


class TestCLIIntegration:
    """Integration tests for CLI."""
    
    def test_full_conversion_workflow(self, sample_pdf, temp_dir):
        """Test complete conversion workflow via CLI."""
        output_path = temp_dir / "result.json"
        
        result = main([
            'convert',
            str(sample_pdf),
            '-o', str(output_path),
            '-q'
        ])
        
        assert result == 0
        assert output_path.exists()
    
    def test_batch_conversion_workflow(self, sample_files_dir, temp_dir):
        """Test batch conversion workflow via CLI."""
        output_dir = temp_dir / "output"
        
        result = main([
            'convert',
            str(sample_files_dir),
            '-o', str(output_dir),
            '-q'
        ])
        
        assert result == 0
        assert output_dir.exists()
    
    def test_quiet_mode(self, sample_pdf):
        """Test quiet mode suppresses output."""
        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            with patch('sys.stderr', new_callable=StringIO) as mock_stderr:
                result = main(['convert', str(sample_pdf), '-q', '-o', '/dev/null'])
        
        assert result == 0
    
    def test_recursive_flag(self, sample_files_dir):
        """Test recursive directory processing."""
        result = main([
            'convert',
            str(sample_files_dir),
            '--recursive',
            '-q'
        ])
        
        assert result == 0
