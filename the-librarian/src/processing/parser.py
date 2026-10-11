"""
Document parser for markdown files with YAML frontmatter.

Parses markdown documents, extracts frontmatter, validates based on doc_type,
and returns ParsedDocument objects ready for chunking and embedding.
"""

import os
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional
import frontmatter
from .models import ParsedDocument, Document


def validate_file_path(file_path: str, allowed_directories: Optional[List[str]] = None) -> bool:
    """
    Validate file path to prevent path traversal attacks.

    Args:
        file_path: File path to validate
        allowed_directories: Optional list of allowed base directories

    Returns:
        True if path is valid, False otherwise

    Raises:
        ValueError: If path contains dangerous patterns
    """
    # Convert to absolute path
    abs_path = os.path.abspath(file_path)

    # Check for path traversal attempts
    if '..' in file_path:
        raise ValueError(f"Path traversal detected: {file_path}")

    # Check for suspicious patterns
    dangerous_patterns = [
        r'\.\./+',      # Parent directory traversal
        r'/\.\.',       # Parent directory at end
        r'\.\.\\',      # Windows path traversal
        r'~/',          # Home directory expansion
        r'\$',          # Variable expansion
        r'`',           # Command substitution
    ]

    for pattern in dangerous_patterns:
        if re.search(pattern, file_path):
            raise ValueError(f"Dangerous pattern in path: {file_path}")

    # If allowed directories specified, check against them
    if allowed_directories:
        path_obj = Path(abs_path)
        allowed = False

        for allowed_dir in allowed_directories:
            allowed_path = Path(os.path.abspath(allowed_dir))
            try:
                # Check if path is within allowed directory
                path_obj.relative_to(allowed_path)
                allowed = True
                break
            except ValueError:
                continue

        if not allowed:
            raise ValueError(
                f"Path outside allowed directories: {file_path}\n"
                f"Allowed: {allowed_directories}"
            )

    return True


class DocumentParser:
    """Parser for markdown documents with YAML frontmatter."""

    def __init__(self, allowed_directories: Optional[List[str]] = None):
        """Initialize the parser.

        Args:
            allowed_directories: Optional list of allowed base directories for parsing
        """
        self.supported_extensions = ['.md', '.markdown']
        self.allowed_directories = allowed_directories

    def can_parse(self, file_path: str) -> bool:
        """Check if this parser can handle the given file.

        Args:
            file_path: Path to the file

        Returns:
            True if file extension is supported
        """
        _, ext = os.path.splitext(file_path)
        return ext.lower() in self.supported_extensions

    def parse(self, file_path: str) -> ParsedDocument:
        """Parse a markdown file with frontmatter.

        Args:
            file_path: Path to the markdown file

        Returns:
            ParsedDocument with extracted content and metadata

        Raises:
            ValueError: If frontmatter is missing or invalid or path is invalid
            FileNotFoundError: If file doesn't exist
        """
        # Validate file path for security
        validate_file_path(file_path, self.allowed_directories)

        if not os.path.exists(file_path):
            raise FileNotFoundError(f"File not found: {file_path}")

        # Read file content
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # Parse frontmatter
        post = frontmatter.loads(content)

        # Extract doc_type from frontmatter
        if 'doc' not in post.metadata:
            raise ValueError(f"Missing 'doc' field in frontmatter: {file_path}")

        doc_type = post.metadata['doc']

        # Get file stats
        stat = os.stat(file_path)
        modified_at = datetime.fromtimestamp(stat.st_mtime)
        size_bytes = stat.st_size

        # Extract sections from markdown
        sections = self._extract_sections(post.content)

        # Build metadata
        metadata = {
            'file_name': os.path.basename(file_path),
            'file_dir': os.path.dirname(file_path),
            'section_count': len(sections),
            'has_frontmatter': True
        }

        # Create ParsedDocument (this will validate frontmatter)
        return ParsedDocument(
            path=file_path,
            doc_type=doc_type,
            content=content,
            frontmatter=post.metadata,
            hash=Document.from_file(file_path, content, doc_type, post.metadata).hash,
            metadata=metadata,
            sections=sections,
            modified_at=modified_at,
            size_bytes=size_bytes
        )

    def _extract_sections(self, content: str) -> List[Dict[str, Any]]:
        """Extract sections from markdown content based on headers.

        Args:
            content: Markdown content (without frontmatter)

        Returns:
            List of section dictionaries with title, level, content, start, end
        """
        sections = []
        lines = content.split('\n')

        current_section = None
        current_content = []
        start_line = 0

        for i, line in enumerate(lines):
            # Check if line is a header
            header_match = re.match(r'^(#{1,6})\s+(.+)$', line)

            if header_match:
                # Save previous section if exists
                if current_section is not None:
                    sections.append({
                        'title': current_section['title'],
                        'level': current_section['level'],
                        'content': '\n'.join(current_content).strip(),
                        'start_line': start_line,
                        'end_line': i - 1
                    })

                # Start new section
                level = len(header_match.group(1))
                title = header_match.group(2).strip()
                current_section = {'level': level, 'title': title}
                current_content = []
                start_line = i
            else:
                current_content.append(line)

        # Save last section
        if current_section is not None:
            sections.append({
                'title': current_section['title'],
                'level': current_section['level'],
                'content': '\n'.join(current_content).strip(),
                'start_line': start_line,
                'end_line': len(lines) - 1
            })

        return sections

    def extract_code_blocks(self, content: str) -> List[Dict[str, str]]:
        """Extract code blocks from markdown content.

        Args:
            content: Markdown content

        Returns:
            List of code block dictionaries with language and content
        """
        code_blocks = []
        pattern = r'```(\w+)?\n(.*?)```'

        for match in re.finditer(pattern, content, re.DOTALL):
            language = match.group(1) or 'text'
            code = match.group(2).strip()
            code_blocks.append({
                'language': language,
                'content': code
            })

        return code_blocks

    def extract_links(self, content: str) -> List[str]:
        """Extract markdown links from content.

        Args:
            content: Markdown content

        Returns:
            List of URLs found in markdown links
        """
        # Match markdown links: [text](url)
        pattern = r'\[([^\]]+)\]\(([^\)]+)\)'
        links = []

        for match in re.finditer(pattern, content):
            url = match.group(2)
            # Filter out internal anchors
            if not url.startswith('#'):
                links.append(url)

        return links

    def validate_frontmatter_fields(self, frontmatter: Dict[str, Any], doc_type: str) -> List[str]:
        """Validate frontmatter has required fields for doc_type.

        Args:
            frontmatter: Frontmatter dictionary
            doc_type: Document type

        Returns:
            List of missing fields (empty if all present)
        """
        # Required fields for all documents
        required = ['doc', 'subsystem', 'id', 'version', 'status', 'owners']

        # Additional required fields for architecture documents
        if doc_type == 'architecture':
            required.extend(['compliance_level', 'drift_tolerance'])

        missing = [field for field in required if field not in frontmatter]
        return missing
