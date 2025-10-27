"""
Text chunking utilities for document processing.
"""

import re
from typing import List, Dict, Any, Optional

from .exceptions import get_logger, TextChunk


class TextChunker:
    """
    Simple text chunking utility that replaces LangChain text splitters.
    
    Implements smart text chunking with sentence-boundary preservation
    and configurable overlap for better context retention.
    """
    
    def __init__(
        self,
        chunk_size: int = 1000,
        chunk_overlap: int = 150,
        preserve_sentences: bool = True
    ):
        """
        Initialize text chunker.
        
        Args:
            chunk_size: Maximum size of each chunk
            chunk_overlap: Overlap between consecutive chunks
            preserve_sentences: Whether to prefer sentence boundaries
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.preserve_sentences = preserve_sentences
        self.logger = get_logger("text_chunker")
        
        # Sentence boundary patterns
        self.sentence_endings = re.compile(r'[.!?]+\s+')
        self.paragraph_breaks = re.compile(r'\n\s*\n')
    
    def chunk_text(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> List[TextChunk]:
        """
        Split text into chunks with smart boundary detection.
        
        Args:
            text: Text to chunk
            metadata: Optional metadata to include with each chunk
            
        Returns:
            List of text chunks
        """
        if not text or not text.strip():
            return []
        
        metadata = metadata or {}
        text = text.strip()
        
        self.logger.debug(
            f"Chunking text",
            extra={
                "text_length": len(text),
                "chunk_size": self.chunk_size,
                "chunk_overlap": self.chunk_overlap,
                "preserve_sentences": self.preserve_sentences
            }
        )
        
        # If text is smaller than chunk size, return as single chunk
        if len(text) <= self.chunk_size:
            return [TextChunk(
                content=text,
                metadata={**metadata, "chunk_index": 0},
                chunk_id=f"chunk_0"
            )]
        
        chunks = []
        
        if self.preserve_sentences:
            chunks = self._chunk_by_sentences(text, metadata)
        else:
            chunks = self._chunk_by_characters(text, metadata)
        
        self.logger.info(
            f"Text chunking completed",
            extra={
                "original_length": len(text),
                "num_chunks": len(chunks),
                "avg_chunk_size": sum(len(chunk.content) for chunk in chunks) // len(chunks) if chunks else 0
            }
        )
        
        return chunks
    
    def _chunk_by_sentences(self, text: str, metadata: Dict[str, Any]) -> List[TextChunk]:
        """Chunk text preserving sentence boundaries."""
        chunks = []
        
        # Split by paragraphs first
        paragraphs = self.paragraph_breaks.split(text)
        
        current_chunk = ""
        chunk_index = 0
        
        for paragraph in paragraphs:
            if not paragraph.strip():
                continue
            
            # Split paragraph into sentences
            sentences = self.sentence_endings.split(paragraph)
            sentences = [s.strip() for s in sentences if s.strip()]
            
            for sentence in sentences:
                # Check if adding this sentence would exceed chunk size
                potential_chunk = current_chunk + (" " if current_chunk else "") + sentence
                
                if len(potential_chunk) > self.chunk_size and current_chunk:
                    # Save current chunk and start new one
                    chunks.append(TextChunk(
                        content=current_chunk.strip(),
                        metadata={**metadata, "chunk_index": chunk_index},
                        chunk_id=f"chunk_{chunk_index}"
                    ))
                    
                    # Start new chunk with overlap
                    overlap_text = self._get_overlap_text(current_chunk)
                    current_chunk = overlap_text + (" " if overlap_text else "") + sentence
                    chunk_index += 1
                else:
                    current_chunk = potential_chunk
        
        # Add final chunk
        if current_chunk.strip():
            chunks.append(TextChunk(
                content=current_chunk.strip(),
                metadata={**metadata, "chunk_index": chunk_index},
                chunk_id=f"chunk_{chunk_index}"
            ))
        
        return chunks
    
    def _chunk_by_characters(self, text: str, metadata: Dict[str, Any]) -> List[TextChunk]:
        """Chunk text by character count with overlap."""
        chunks = []
        chunk_index = 0
        start = 0
        
        while start < len(text):
            # Calculate end position
            end = start + self.chunk_size
            
            # Extract chunk
            chunk_text = text[start:end]
            
            # If not at the end, try to break at word boundary
            if end < len(text) and not text[end].isspace():
                # Find last space in chunk
                last_space = chunk_text.rfind(' ')
                if last_space > 0:
                    end = start + last_space
                    chunk_text = text[start:end]
            
            chunks.append(TextChunk(
                content=chunk_text.strip(),
                metadata={**metadata, "chunk_index": chunk_index},
                chunk_id=f"chunk_{chunk_index}"
            ))
            
            # Move start position with overlap
            start = end - self.chunk_overlap
            if start < 0:
                start = 0
            
            chunk_index += 1
            
            # Prevent infinite loop
            if start >= end:
                break
        
        return chunks
    
    def _get_overlap_text(self, text: str) -> str:
        """Extract overlap text from the end of current chunk."""
        if len(text) <= self.chunk_overlap:
            return text
        
        overlap_start = len(text) - self.chunk_overlap
        overlap_text = text[overlap_start:]
        
        # Try to start overlap at sentence boundary
        if self.preserve_sentences:
            sentences = self.sentence_endings.split(overlap_text)
            if len(sentences) > 1:
                # Use complete sentences for overlap
                overlap_text = " ".join(sentences[1:])
        
        return overlap_text.strip()