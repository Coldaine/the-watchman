"""
Text chunker for intelligent document segmentation.

Chunks documents using multiple strategies while preserving semantic boundaries,
paragraph structure, code blocks, and header hierarchy. Uses tiktoken for
accurate token counting.
"""

import re
from typing import List, Dict, Any
import tiktoken
from .models import ParsedDocument, Chunk


class TextChunker:
    """Intelligent text chunker that preserves semantic boundaries."""

    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        min_chunk_size: int = 100,
        encoding_name: str = "cl100k_base"  # GPT-4 encoding
    ):
        """Initialize the chunker.

        Args:
            chunk_size: Target chunk size in tokens
            chunk_overlap: Number of overlapping tokens between chunks
            min_chunk_size: Minimum chunk size in tokens
            encoding_name: Tiktoken encoding to use for token counting
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.min_chunk_size = min_chunk_size
        self.encoding = tiktoken.get_encoding(encoding_name)

    def count_tokens(self, text: str) -> int:
        """Count tokens in text using tiktoken.

        Args:
            text: Text to count tokens for

        Returns:
            Number of tokens
        """
        return len(self.encoding.encode(text))

    def chunk_document(self, doc: ParsedDocument) -> List[Chunk]:
        """Create chunks from a parsed document.

        Args:
            doc: Parsed document to chunk

        Returns:
            List of chunks with metadata
        """
        # Choose chunking strategy based on doc_type
        if doc.doc_type in ['architecture', 'design', 'research']:
            # Chunk by sections for structured documents
            chunks = self._chunk_by_sections(doc)
        elif doc.doc_type == 'code':
            # Chunk by code components
            chunks = self._chunk_by_components(doc)
        else:
            # Default: sliding window chunking
            chunks = self._chunk_by_sliding_window(doc.content)

        # Add document metadata to each chunk
        for i, chunk in enumerate(chunks):
            chunk.metadata.update({
                'doc_id': doc.frontmatter.get('id'),
                'doc_type': doc.doc_type,
                'doc_path': doc.path,
                'chunk_index': i,
                'total_chunks': len(chunks),
                'version': doc.frontmatter.get('version'),
                'subsystem': doc.frontmatter.get('subsystem'),
                'doc_hash': doc.hash
            })

        return chunks

    def _chunk_by_sections(self, doc: ParsedDocument) -> List[Chunk]:
        """Chunk structured documents by sections.

        Args:
            doc: Parsed document with sections

        Returns:
            List of chunks, one or more per section
        """
        chunks = []
        content_position = 0

        for section in doc.sections:
            # Skip empty sections
            if not section['content'].strip():
                continue

            section_title = section['title']
            section_level = section['level']
            section_content = section['content']

            # Build full section text with header
            full_section = f"{'#' * section_level} {section_title}\n\n{section_content}"

            token_count = self.count_tokens(full_section)

            if token_count > self.chunk_size:
                # Section too large, split it
                sub_chunks = self._split_large_section(
                    full_section,
                    section_title,
                    section_level
                )

                for sub_chunk in sub_chunks:
                    chunk = Chunk(
                        content=sub_chunk,
                        start_index=content_position,
                        end_index=content_position + len(sub_chunk),
                        section_title=section_title,
                        section_level=section_level,
                        metadata={}
                    )
                    chunks.append(chunk)
                    content_position += len(sub_chunk)
            else:
                # Keep section as single chunk
                chunk = Chunk(
                    content=full_section,
                    start_index=content_position,
                    end_index=content_position + len(full_section),
                    section_title=section_title,
                    section_level=section_level,
                    metadata={}
                )
                chunks.append(chunk)
                content_position += len(full_section)

        return chunks

    def _split_large_section(
        self,
        section_text: str,
        section_title: str,
        section_level: int
    ) -> List[str]:
        """Split a large section into smaller chunks while preserving structure.

        Args:
            section_text: Full section text with header
            section_title: Section title
            section_level: Header level

        Returns:
            List of chunk strings
        """
        # Try to split by paragraphs first
        paragraphs = self._split_by_paragraphs(section_text)

        chunks = []
        current_chunk = []
        current_tokens = 0

        header = f"{'#' * section_level} {section_title}\n\n"
        header_tokens = self.count_tokens(header)

        for para in paragraphs:
            para_tokens = self.count_tokens(para)

            # If single paragraph exceeds chunk size, split it
            if para_tokens > self.chunk_size:
                # Save current chunk if it has content
                if current_chunk:
                    chunks.append(header + '\n\n'.join(current_chunk))
                    current_chunk = []
                    current_tokens = 0

                # Split paragraph by sentences
                sentences = self._split_by_sentences(para)
                for sentence in sentences:
                    sentence_tokens = self.count_tokens(sentence)

                    if current_tokens + sentence_tokens > self.chunk_size:
                        if current_chunk:
                            chunks.append(header + '\n\n'.join(current_chunk))
                        current_chunk = [sentence]
                        current_tokens = header_tokens + sentence_tokens
                    else:
                        current_chunk.append(sentence)
                        current_tokens += sentence_tokens
            else:
                # Check if adding paragraph exceeds limit
                if current_tokens + para_tokens > self.chunk_size:
                    # Save current chunk and start new one
                    if current_chunk:
                        chunks.append(header + '\n\n'.join(current_chunk))
                    current_chunk = [para]
                    current_tokens = header_tokens + para_tokens
                else:
                    current_chunk.append(para)
                    current_tokens += para_tokens

        # Add remaining content
        if current_chunk:
            chunks.append(header + '\n\n'.join(current_chunk))

        return chunks

    def _chunk_by_components(self, doc: ParsedDocument) -> List[Chunk]:
        """Chunk code documents by logical components (functions/classes).

        Args:
            doc: Parsed document representing code

        Returns:
            List of chunks, one per component
        """
        chunks = []
        position = 0

        for section in doc.sections:
            chunk = Chunk(
                content=section['content'],
                start_index=position,
                end_index=position + len(section['content']),
                section_title=section['title'],
                section_level=section['level'],
                metadata={'is_code': True}
            )
            chunks.append(chunk)
            position += len(section['content'])

        return chunks

    def _chunk_by_sliding_window(self, content: str) -> List[Chunk]:
        """Chunk text using sliding window approach with overlap.

        Args:
            content: Text content to chunk

        Returns:
            List of chunks
        """
        # Split into paragraphs to preserve boundaries
        paragraphs = self._split_by_paragraphs(content)

        chunks = []
        current_chunk = []
        current_tokens = 0
        position = 0

        for para in paragraphs:
            para_tokens = self.count_tokens(para)

            if current_tokens + para_tokens > self.chunk_size:
                # Save current chunk
                if current_chunk:
                    chunk_text = '\n\n'.join(current_chunk)
                    chunk = Chunk(
                        content=chunk_text,
                        start_index=position - len(chunk_text),
                        end_index=position,
                        metadata={}
                    )
                    chunks.append(chunk)

                    # Start new chunk with overlap
                    # Keep last few paragraphs for overlap
                    overlap_paras = []
                    overlap_tokens = 0

                    for p in reversed(current_chunk):
                        p_tokens = self.count_tokens(p)
                        if overlap_tokens + p_tokens <= self.chunk_overlap:
                            overlap_paras.insert(0, p)
                            overlap_tokens += p_tokens
                        else:
                            break

                    current_chunk = overlap_paras
                    current_tokens = overlap_tokens

            current_chunk.append(para)
            current_tokens += para_tokens
            position += len(para) + 2  # +2 for \n\n

        # Add final chunk
        if current_chunk and current_tokens >= self.min_chunk_size:
            chunk_text = '\n\n'.join(current_chunk)
            chunk = Chunk(
                content=chunk_text,
                start_index=position - len(chunk_text),
                end_index=position,
                metadata={}
            )
            chunks.append(chunk)

        return chunks

    def _split_by_paragraphs(self, text: str) -> List[str]:
        """Split text into paragraphs.

        Args:
            text: Text to split

        Returns:
            List of paragraphs
        """
        # Split by double newlines, but preserve code blocks
        code_block_pattern = r'```.*?```'
        code_blocks = []

        # Extract code blocks
        def save_code_block(match):
            code_blocks.append(match.group(0))
            return f"<<<CODE_BLOCK_{len(code_blocks) - 1}>>>"

        text_with_placeholders = re.sub(
            code_block_pattern,
            save_code_block,
            text,
            flags=re.DOTALL
        )

        # Split by paragraphs
        paragraphs = re.split(r'\n\s*\n', text_with_placeholders)

        # Restore code blocks
        result = []
        for para in paragraphs:
            # Check for code block placeholders
            if '<<<CODE_BLOCK_' in para:
                for i, code_block in enumerate(code_blocks):
                    para = para.replace(f'<<<CODE_BLOCK_{i}>>>', code_block)
            if para.strip():
                result.append(para.strip())

        return result

    def _split_by_sentences(self, text: str) -> List[str]:
        """Split text into sentences.

        Args:
            text: Text to split

        Returns:
            List of sentences
        """
        # Simple sentence splitting (can be improved with NLTK if needed)
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s.strip() for s in sentences if s.strip()]
