"""
Command-line interface for Document Batch Converter.

This module provides the CLI entry point and command handlers
for the docbatch tool.
"""

import argparse
import logging
import sys
from pathlib import Path
from typing import List, Optional

from docbatch import __version__
from docbatch.converter import DocumentConverter, UnsupportedFormatError, ConversionStats
from docbatch.models import DocumentOutput


# Configure module logger
logger = logging.getLogger(__name__)


def create_parser() -> argparse.ArgumentParser:
    """
    Create and configure the argument parser.
    
    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog='docbatch',
        description=(
            'A Python CLI tool that batch-converts PDF, DOCX, and PPTX files '
            'into structured JSON with section-aware text extraction.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s convert document.pdf                    Convert a single file
  %(prog)s convert document.pdf -o output.json     Convert with specific output
  %(prog)s convert ./documents/ -o ./output/       Batch convert directory
  %(prog)s convert ./docs/ --recursive             Convert with subdirectories
  %(prog)s convert ./docs/ --dry-run               Preview files to process
  %(prog)s --version                               Show version info

Supported formats: PDF, DOCX, PPTX

For more information, visit: https://github.com/KZeyrox45/docbatch
        """,
    )
    
    # Global options
    parser.add_argument(
        '--version',
        action='version',
        version=f'%(prog)s {__version__}',
    )
    
    # Subcommands
    subparsers = parser.add_subparsers(
        dest='command',
        title='commands',
        description='Available commands',
    )
    
    # Convert command
    convert_parser = subparsers.add_parser(
        'convert',
        help='Convert document(s) to JSON',
        description='Convert one or more documents to structured JSON format.',
    )
    
    # Input argument (required)
    convert_parser.add_argument(
        'input',
        type=str,
        help='Input file or directory to convert',
    )
    
    # Output argument
    convert_parser.add_argument(
        '-o', '--output',
        type=str,
        default=None,
        help='Output file (for single file) or directory (for batch). '
             'If not specified, output is written to stdout for single files.',
    )
    
    # Recursive option
    convert_parser.add_argument(
        '-r', '--recursive',
        action='store_true',
        help='Process subdirectories recursively (for directory input)',
    )
    
    # Skip errors option
    convert_parser.add_argument(
        '--skip-errors',
        action='store_true',
        default=True,
        help='Continue processing on errors (default: True)',
    )
    
    # Strict mode (opposite of skip-errors)
    convert_parser.add_argument(
        '--strict',
        action='store_true',
        help='Stop on first error (opposite of --skip-errors)',
    )
    
    # Dry run option
    convert_parser.add_argument(
        '--dry-run',
        action='store_true',
        help='Preview files to be processed without converting',
    )
    
    # Verbose option
    convert_parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Enable verbose output with detailed logging',
    )
    
    # Quiet option (hide progress bar)
    convert_parser.add_argument(
        '-q', '--quiet',
        action='store_true',
        help='Suppress progress bar and non-essential output',
    )
    
    # Stats command
    stats_parser = subparsers.add_parser(
        'stats',
        help='Show file statistics without converting',
        description='Display statistics about supported files in a directory.',
    )
    
    stats_parser.add_argument(
        'directory',
        type=str,
        help='Directory to analyze',
    )
    
    stats_parser.add_argument(
        '-r', '--recursive',
        action='store_true',
        help='Scan subdirectories recursively',
    )
    
    return parser


def handle_convert(args: argparse.Namespace) -> int:
    """
    Handle the convert command.
    
    Args:
        args: Parsed command-line arguments.
    
    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    input_path = Path(args.input)
    
    # Determine skip_errors setting
    skip_errors = args.skip_errors and not args.strict
    
    # Determine show_progress setting
    show_progress = not args.quiet
    
    # Create converter
    converter = DocumentConverter(
        skip_errors=skip_errors,
        verbose=args.verbose,
        show_progress=show_progress,
    )
    
    try:
        # Check if input is file or directory
        if input_path.is_file():
            # Single file conversion
            return _convert_single_file(converter, args, input_path)
        
        elif input_path.is_dir():
            # Directory batch conversion
            return _convert_directory(converter, args, input_path)
        
        else:
            print(f"Error: Path not found: {input_path}", file=sys.stderr)
            return 1
            
    except UnsupportedFormatError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1


def _convert_single_file(
    converter: DocumentConverter,
    args: argparse.Namespace,
    input_path: Path,
) -> int:
    """Handle single file conversion."""
    # Check if format is supported
    if not converter.is_supported(input_path):
        print(f"Error: Unsupported file format: {input_path.suffix}", file=sys.stderr)
        return 1
    
    # Convert the file
    output = converter.convert_file(input_path, args.output)
    
    # Print output to stdout if no output file specified
    if not args.output:
        print(output.to_json())
    
    # Print summary
    if not args.quiet:
        print(f"\nConverted: {input_path.name}", file=sys.stderr)
        print(f"  Sections: {len(output.sections)}", file=sys.stderr)
        print(f"  Tables: {len(output.tables)}", file=sys.stderr)
        print(f"  Images: {len(output.images)}", file=sys.stderr)
        print(f"  Time: {output.conversion_time:.2f}s", file=sys.stderr)
        
        if output.warnings:
            print(f"  Warnings: {len(output.warnings)}", file=sys.stderr)
    
    return 0


def _convert_directory(
    converter: DocumentConverter,
    args: argparse.Namespace,
    input_path: Path,
) -> int:
    """Handle directory batch conversion."""
    results, stats = converter.convert_directory(
        input_path,
        output_dir=args.output,
        recursive=args.recursive,
        dry_run=args.dry_run,
    )
    
    # Print summary
    if not args.quiet:
        print(f"\n{stats}", file=sys.stderr)
        
        if args.dry_run:
            return 0
        
        # Print per-file summary
        if args.verbose and results:
            print("\nDetails:", file=sys.stderr)
            for output in results:
                print(
                    f"  {output.filename}: "
                    f"{len(output.sections)} sections, "
                    f"{output.conversion_time:.2f}s",
                    file=sys.stderr
                )
    
    # Return non-zero if there were failures
    return 1 if stats.failed > 0 else 0


def handle_stats(args: argparse.Namespace) -> int:
    """
    Handle the stats command.
    
    Args:
        args: Parsed command-line arguments.
    
    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    directory = Path(args.directory)
    
    if not directory.exists():
        print(f"Error: Directory not found: {directory}", file=sys.stderr)
        return 1
    
    if not directory.is_dir():
        print(f"Error: Not a directory: {directory}", file=sys.stderr)
        return 1
    
    # Create converter to access file finding logic
    converter = DocumentConverter(show_progress=False)
    files = converter._find_files(directory, args.recursive)
    
    # Group by extension
    by_extension: dict = {}
    for f in files:
        ext = f.suffix.lower()
        if ext not in by_extension:
            by_extension[ext] = []
        by_extension[ext].append(f)
    
    # Print statistics
    print(f"\nDirectory: {directory}")
    print(f"Recursive: {args.recursive}")
    print(f"\nTotal files: {len(files)}")
    print("\nBy format:")
    
    for ext, file_list in sorted(by_extension.items()):
        print(f"  {ext}: {len(file_list)} files")
    
    if args.recursive:
        print("\nFiles:")
        for f in files[:20]:  # Limit output
            print(f"  {f.relative_to(directory)}")
        if len(files) > 20:
            print(f"  ... and {len(files) - 20} more")
    
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """
    Main entry point for the CLI.
    
    Args:
        argv: Command-line arguments. If None, uses sys.argv.
    
    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    parser = create_parser()
    args = parser.parse_args(argv)
    
    # Configure logging based on verbose flag
    log_level = logging.DEBUG if getattr(args, 'verbose', False) else logging.WARNING
    logging.basicConfig(
        level=log_level,
        format='%(levelname)s: %(message)s',
    )
    
    # Handle commands
    if args.command == 'convert':
        return handle_convert(args)
    elif args.command == 'stats':
        return handle_stats(args)
    else:
        # No command specified, show help
        parser.print_help()
        return 0


if __name__ == '__main__':
    sys.exit(main())
