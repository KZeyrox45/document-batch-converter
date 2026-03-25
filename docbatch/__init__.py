"""
Document Batch Converter - A Python CLI tool for batch converting documents to JSON.

This package provides functionality to convert PDF, DOCX, and PPTX files
into structured JSON format with section-aware text extraction.
"""

__version__ = "1.0.0"
__author__ = "Nguyen Trung Hieu"

from docbatch.converter import DocumentConverter
from docbatch.cli import main

__all__ = ["DocumentConverter", "main"]
