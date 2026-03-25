"""
Main converter module for document batch processing.

This module provides the DocumentConverter class that orchestrates
the conversion of documents to JSON format, handling single files,
directories, and batch processing.
"""

import json
import logging
import time
from pathlib import Path
from typing import List, Dict, Optional, Union, Type

from tqdm import tqdm

from docbatch.parsers.base import BaseParser
from docbatch.parsers.pdf_parser import PDFParser
from docbatch.parsers.docx_parser import DOCXParser
from docbatch.parsers.pptx_parser import PPTXParser
from docbatch.models import DocumentOutput


logger = logging.getLogger(__name__)


class UnsupportedFormatError(Exception):
    """Raised when an unsupported file format is encountered."""
    pass


class ConversionStats:
    """Track conversion statistics."""
    
    def __init__(self):
        self.total_files = 0
        self.successful = 0
        self.skipped = 0
        self.failed = 0
        self.errors: List[Dict[str, str]] = []
        self.start_time: float = 0
        self.end_time: float = 0
    
    @property
    def elapsed_time(self) -> float:
        """Return elapsed time in seconds."""
        return self.end_time - self.start_time if self.end_time else 0
    
    def to_dict(self) -> Dict:
        """Convert stats to dictionary."""
        return {
            "total_files": self.total_files,
            "successful": self.successful,
            "skipped": self.skipped,
            "failed": self.failed,
            "elapsed_time": round(self.elapsed_time, 2),
            "errors": self.errors,
        }
    
    def __str__(self) -> str:
        """Return human-readable stats."""
        return (
            f"Processed: {self.total_files} files | "
            f"Success: {self.successful} | "
            f"Skipped: {self.skipped} | "
            f"Failed: {self.failed} | "
            f"Time: {self.elapsed_time:.1f}s"
        )


class DocumentConverter:
    """
    Main converter class for batch document processing.
    
    Supports:
    - Single file conversion
    - Directory batch processing
    - Recursive directory scanning
    - Multiple output formats
    - Progress tracking
    
    Example:
        >>> converter = DocumentConverter()
        >>> output = converter.convert_file("document.pdf")
        >>> print(output.to_json())
        
        >>> # Batch processing
        >>> results = converter.convert_directory("./documents/", recursive=True)
        >>> for result in results:
        ...     print(f"{result.filename}: {len(result.sections)} sections")
    """
    
    # Registry of available parsers
    PARSERS: Dict[str, Type[BaseParser]] = {
        '.pdf': PDFParser,
        '.docx': DOCXParser,
        '.doc': DOCXParser,
        '.pptx': PPTXParser,
        '.ppt': PPTXParser,
    }
    
    # Supported extensions
    SUPPORTED_EXTENSIONS = list(PARSERS.keys())
    
    def __init__(
        self,
        skip_errors: bool = True,
        verbose: bool = False,
        show_progress: bool = True,
    ):
        """
        Initialize the converter.
        
        Args:
            skip_errors: If True, continue processing on errors; if False, raise exception.
            verbose: Enable verbose logging output.
            show_progress: Show progress bar during batch processing.
        """
        self.skip_errors = skip_errors
        self.verbose = verbose
        self.show_progress = show_progress
        
        # Configure logging
        log_level = logging.DEBUG if verbose else logging.INFO
        logging.basicConfig(
            level=log_level,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        
        # Initialize parser instances
        self._parsers: Dict[str, BaseParser] = {}
    
    def get_parser(self, extension: str) -> BaseParser:
        """
        Get the appropriate parser for a file extension.
        
        Args:
            extension: File extension (e.g., '.pdf', '.docx').
            
        Returns:
            Parser instance for the given extension.
            
        Raises:
            UnsupportedFormatError: If no parser supports the extension.
        """
        ext = extension.lower()
        
        if ext not in self.PARSERS:
            raise UnsupportedFormatError(
                f"Unsupported file format: {ext}. "
                f"Supported formats: {', '.join(self.SUPPORTED_EXTENSIONS)}"
            )
        
        # Cache parser instances
        if ext not in self._parsers:
            self._parsers[ext] = self.PARSERS[ext]()
        
        return self._parsers[ext]
    
    def convert_file(
        self,
        filepath: Union[str, Path],
        output_path: Optional[Union[str, Path]] = None,
    ) -> DocumentOutput:
        """
        Convert a single document file to JSON.
        
        Args:
            filepath: Path to the document file.
            output_path: Optional path to save the JSON output.
                        If None, the result is only returned.
        
        Returns:
            DocumentOutput containing the parsed content.
        
        Raises:
            FileNotFoundError: If the file doesn't exist.
            UnsupportedFormatError: If the file format is not supported.
            Exception: If skip_errors is False and conversion fails.
        """
        filepath = Path(filepath)
        
        # Validate file exists
        if not filepath.exists():
            raise FileNotFoundError(f"File not found: {filepath}")
        
        # Get parser
        parser = self.get_parser(filepath.suffix)
        
        logger.info(f"Converting: {filepath.name}")
        start_time = time.perf_counter()
        
        try:
            # Parse the document
            output = parser.parse(str(filepath))
            
            logger.info(
                f"Completed: {filepath.name} "
                f"({len(output.sections)} sections, "
                f"{output.conversion_time:.2f}s)"
            )
            
            # Save to file if output path specified
            if output_path:
                self._save_output(output, output_path)
            
            return output
            
        except Exception as e:
            logger.error(f"Failed to convert {filepath.name}: {e}")
            
            if not self.skip_errors:
                raise
            
            # Return minimal output with error info
            return DocumentOutput(
                filename=filepath.name,
                metadata={"file_type": filepath.suffix[1:]},
                warnings=[{
                    "type": "conversion_error",
                    "message": str(e),
                }],
            )
    
    def convert_directory(
        self,
        directory: Union[str, Path],
        output_dir: Optional[Union[str, Path]] = None,
        recursive: bool = False,
        dry_run: bool = False,
    ) -> tuple[List[DocumentOutput], ConversionStats]:
        """
        Convert all supported documents in a directory.
        
        Args:
            directory: Path to the directory containing documents.
            output_dir: Directory to save JSON outputs.
                       If None, results are only returned.
            recursive: If True, scan subdirectories recursively.
            dry_run: If True, only list files without converting.
        
        Returns:
            Tuple of (list of DocumentOutput, ConversionStats).
        """
        directory = Path(directory)
        stats = ConversionStats()
        
        # Validate directory exists
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        
        if not directory.is_dir():
            raise ValueError(f"Not a directory: {directory}")
        
        # Find all supported files
        files = self._find_files(directory, recursive)
        stats.total_files = len(files)
        
        if not files:
            logger.warning(f"No supported files found in: {directory}")
            return [], stats
        
        # Dry run: just list files
        if dry_run:
            logger.info(f"Dry run: {len(files)} files would be processed")
            for f in files:
                print(f"  - {f.relative_to(directory)}")
            return [], stats
        
        # Process files
        results: List[DocumentOutput] = []
        stats.start_time = time.perf_counter()
        
        # Create output directory if needed
        if output_dir:
            output_dir = Path(output_dir)
            output_dir.mkdir(parents=True, exist_ok=True)
        
        # Setup progress bar
        iterator = tqdm(files, desc="Converting", disable=not self.show_progress)
        
        for filepath in iterator:
            try:
                # Determine output path
                json_path = None
                if output_dir:
                    json_path = output_dir / f"{filepath.stem}.json"
                
                # Convert file
                output = self.convert_file(filepath, json_path)
                results.append(output)
                stats.successful += 1
                
            except UnsupportedFormatError:
                stats.skipped += 1
                logger.warning(f"Skipped (unsupported): {filepath.name}")
                
            except Exception as e:
                stats.failed += 1
                stats.errors.append({
                    "file": str(filepath),
                    "error": str(e),
                })
                logger.error(f"Failed: {filepath.name} - {e}")
        
        stats.end_time = time.perf_counter()
        
        logger.info(str(stats))
        
        return results, stats
    
    def _find_files(
        self,
        directory: Path,
        recursive: bool = False,
    ) -> List[Path]:
        """
        Find all supported files in a directory.
        
        Args:
            directory: Directory to search.
            recursive: If True, search subdirectories.
        
        Returns:
            List of file paths.
        """
        files = []
        
        if recursive:
            pattern = '**/*'
        else:
            pattern = '*'
        
        for filepath in directory.glob(pattern):
            if filepath.is_file() and filepath.suffix.lower() in self.SUPPORTED_EXTENSIONS:
                files.append(filepath)
        
        return sorted(files)
    
    def _save_output(
        self,
        output: DocumentOutput,
        output_path: Union[str, Path],
    ) -> None:
        """
        Save conversion output to a JSON file.
        
        Args:
            output: DocumentOutput to save.
            output_path: Path to save the JSON file.
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(output.to_json(indent=2))
        
        logger.debug(f"Saved: {output_path}")
    
    @classmethod
    def is_supported(cls, filepath: Union[str, Path]) -> bool:
        """Check if a file format is supported."""
        return Path(filepath).suffix.lower() in cls.SUPPORTED_EXTENSIONS
