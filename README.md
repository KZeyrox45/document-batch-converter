# Document Batch Converter

A Python CLI tool that batch-converts PDF, DOCX, and PPTX files into structured JSON with section-aware text extraction.

## Features

- **Multi-format support**: Convert PDF, DOCX, and PPTX files to JSON
- **Section-aware extraction**: Automatically detects document sections using explicit markers
- **Table extraction**: Extract tables with headers and rows
- **Image detection**: Identify images with dimensions
- **Speaker notes**: Extract speaker notes from PPTX slides
- **Batch processing**: Process entire directories with recursive scanning
- **Progress tracking**: Visual progress bar for batch operations
- **Error resilience**: Skip corrupted files and continue processing
- **Structured logging**: Detailed logging with warning tracking

## Installation

### From Source

```bash
# Clone the repository
git clone <repository>
cd document-batch-converter

# Install in development mode
pip install -e ".[dev]"
```

### From PyPI

```bash
pip install docbatch
```

## Usage

### Convert a Single File

```bash
# Convert and output to stdout
docbatch convert document.pdf

# Convert and save to file
docbatch convert document.pdf -o output.json

# Convert with verbose output
docbatch convert document.pdf -v
```

### Batch Convert a Directory

```bash
# Convert all supported files in a directory
docbatch convert ./documents/ -o ./output/

# Process subdirectories recursively
docbatch convert ./documents/ --recursive -o ./output/

# Preview files without converting (dry run)
docbatch convert ./documents/ --dry-run
```

### Show Statistics

```bash
# Count supported files in a directory
docbatch stats ./documents/

# Count files recursively
docbatch stats ./documents/ --recursive
```

### Command Options

| Option | Description |
|--------|-------------|
| `-o, --output` | Output file (single) or directory (batch) |
| `-r, --recursive` | Process subdirectories recursively |
| `--dry-run` | Preview files without converting |
| `--skip-errors` | Continue on errors (default: True) |
| `--strict` | Stop on first error |
| `-v, --verbose` | Enable detailed logging |
| `-q, --quiet` | Suppress progress bar and non-essential output |

## JSON Output Structure

The converter produces section-aware JSON output:

```json
{
  "filename": "report.pdf",
  "metadata": {
    "file_type": "pdf",
    "pages": 10,
    "author": "John Doe",
    "title": "Annual Report"
  },
  "sections": [
    {
      "heading": "1. Introduction",
      "content": "This is the introduction...",
      "level": 1,
      "page": 1
    },
    {
      "heading": "1.1 Background",
      "content": "Background information...",
      "level": 2,
      "page": 2
    }
  ],
  "tables": [
    {
      "index": 0,
      "headers": ["Name", "Value"],
      "rows": [["Item 1", "100"], ["Item 2", "200"]],
      "page": 5
    }
  ],
  "images": [
    {
      "index": 0,
      "width": 800,
      "height": 600,
      "page": 3
    }
  ],
  "conversion_time": 1.234
}
```

### PPTX-Specific Output

For PowerPoint files, slides are extracted with speaker notes:

```json
{
  "filename": "presentation.pptx",
  "metadata": {
    "file_type": "pptx",
    "slides": 15
  },
  "slides": [
    {
      "slide_number": 1,
      "title": "Introduction",
      "content": "Welcome to the presentation",
      "speaker_notes": "Remember to greet the audience"
    }
  ]
}
```

## Section Detection

The converter detects sections using explicit markers:

- **Numbered sections**: `1. Introduction`, `1.1 Background`, `1.1.1 Details`
- **Chapter markers**: `Chapter 1: Introduction`
- **Part markers**: `Part I: Overview`
- **Section markers**: `Section 1: Methods`
- **Appendix**: `Appendix A: Supplementary Data`
- **Common headings**: `Abstract`, `Introduction`, `Methodology`, `Results`, `Conclusion`

## Supported Formats

| Format | Extension | Features |
|--------|-----------|----------|
| PDF | `.pdf` | Text, tables, images, metadata |
| Word | `.docx`, `.doc` | Text, tables, images, headings, metadata |
| PowerPoint | `.pptx`, `.ppt` | Slides, speaker notes, tables, images |

## Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=docbatch --cov-report=html

# Run specific test file
pytest tests/test_converter.py -v
```

### Project Structure

```
docbatch/
├── docbatch/
│   ├── __init__.py
│   ├── cli.py           # Command-line interface
│   ├── converter.py     # Main converter logic
│   ├── models.py        # Data models and JSON schema
│   └── parsers/
│       ├── __init__.py
│       ├── base.py      # Abstract base parser
│       ├── pdf_parser.py
│       ├── docx_parser.py
│       └── pptx_parser.py
├── tests/
│   ├── conftest.py      # Shared fixtures
│   ├── test_models.py
│   ├── test_parsers.py
│   ├── test_converter.py
│   └── test_cli.py
├── examples/
│   ├── input/           # Sample input files
│   └── output/          # Sample JSON outputs
├── pyproject.toml
└── README.md
```

## License

MIT License - see [LICENSE](LICENSE) for details.
