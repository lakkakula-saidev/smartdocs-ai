"""
Text processing utilities for SmartDocs AI Backend.

This module contains functions for text chunking, markdown enhancement,
and other text processing operations extracted from the original main.py.
"""

import re
from typing import List

from ..config import get_settings
from ..logger import get_logger

logger = get_logger("text_processing")

# Markdown enhancement patterns (from original main.py)
LIST_TITLE_PATTERN = re.compile(r'^(\s*(?:\d+\.|[-*])\s+)([A-Z][^:\n]{2,80}?)(:)(\s+)')
QUOTED_PATTERN = re.compile(r'"([^"\n]{3,120})"')
LIST_SENTENCE_PATTERN = re.compile(r'^(\s*(?:\d+\.|[-*])\s+)([A-Za-z][^\n]*)$')

# Auxiliary verbs for noun phrase detection
AUX_OR_VERB = {
    "is", "are", "was", "were", "be", "being", "been",
    "has", "have", "had",
    "can", "could", "may", "might", "must",
    "shall", "should", "will", "would",
    "does", "do", "did"
}


def split_text_into_chunks(text: str, chunk_size: int = None, chunk_overlap: int = None) -> List[str]:
    """
    Split text into chunks using RecursiveCharacterTextSplitter.
    
    Args:
        text: Text to split
        chunk_size: Maximum size of each chunk (uses config default if None)
        chunk_overlap: Overlap between chunks (uses config default if None)
        
    Returns:
        List of text chunks
        
    Raises:
        ImportError: If langchain is not installed
    """
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
    except ImportError as e:
        logger.error("langchain not installed", extra={"error": str(e)})
        raise ImportError("langchain not installed. Install with: pip install langchain") from e
    
    settings = get_settings()
    
    # Use provided values or fall back to configuration
    chunk_size = chunk_size or settings.chunk_size
    chunk_overlap = chunk_overlap or settings.chunk_overlap
    
    logger.debug(f"Splitting text into chunks", 
                extra={"text_length": len(text), "chunk_size": chunk_size, "chunk_overlap": chunk_overlap})
    
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", " ", ""]
    )
    
    # Create documents and extract text
    docs = splitter.create_documents([text])
    chunks = [doc.page_content for doc in docs]
    
    logger.info(f"Split text into {len(chunks)} chunks", 
               extra={"original_length": len(text), "num_chunks": len(chunks),
                     "avg_chunk_size": sum(len(chunk) for chunk in chunks) // len(chunks) if chunks else 0})
    
    return chunks


def enhance_markdown(answer: str) -> str:
    """
    Add lightweight markdown emphasis to improve readability when the LLM
    output does not include formatting on its own.

    Heuristics (in order):
      1. Bold list item 'title' segments before first colon.
      2. Bold first quoted phrase (likely a document or section title).
      3. For plain enumerated sentences, bold an initial noun phrase.
      
    Args:
        answer: Raw text answer to enhance
        
    Returns:
        Enhanced markdown text
    """
    logger.debug(f"Enhancing markdown for text of length {len(answer)}")
    
    lines = answer.splitlines()
    
    # 1: title segments with colon
    lines = [_bold_list_titles(l) for l in lines]
    
    # 3: noun phrase for enumerated sentences lacking colon
    lines = [_bold_initial_noun_phrase(l) for l in lines]
    
    enhanced = "\n".join(lines)
    
    # 2: quoted phrase after structural per-line adjustments
    enhanced = _bold_first_quoted_phrase(enhanced)
    
    logger.debug(f"Markdown enhancement complete", 
                extra={"original_length": len(answer), "enhanced_length": len(enhanced)})
    
    return enhanced


def _bold_list_titles(line: str) -> str:
    """
    Bold list item titles that appear before a colon.
    
    Args:
        line: Text line to process
        
    Returns:
        Line with bolded titles
    """
    def repl(m: re.Match) -> str:
        prefix, title, colon, space = m.groups()
        if '**' in title:
            return m.group(0)  # Already formatted
        return f'{prefix}**{title.strip()}**{colon}{space}'
    
    return LIST_TITLE_PATTERN.sub(repl, line)


def _bold_first_quoted_phrase(text: str) -> str:
    """
    Bold the first quoted phrase if it looks like a document title (no existing ** inside).
    
    Args:
        text: Text to process
        
    Returns:
        Text with first quoted phrase bolded
    """
    def repl(m: re.Match) -> str:
        phrase = m.group(1)
        if '**' in phrase:
            return m.group(0)  # Already formatted
        # Keep surrounding quotes out of bold for clarity:
        return f'"**{phrase.strip()}**"'
    
    return QUOTED_PATTERN.sub(repl, text, count=1)


def _bold_initial_noun_phrase(line: str) -> str:
    """
    For enumerated list sentences WITHOUT a colon, bold a concise leading noun phrase.
    
    Heuristic:
      - Stop before first auxiliary/verb token (AUX_OR_VERB) or punctuation.
      - Limit to max 6 tokens, min 2 tokens.
      - Skip if line already contains **.
      
    Args:
        line: Text line to process
        
    Returns:
        Line with initial noun phrase bolded
    """
    if '**' in line:
        return line
    
    m = LIST_SENTENCE_PATTERN.match(line)
    if not m:
        return line
    
    prefix, rest = m.groups()
    if ':' in rest:  # already handled by title heuristic
        return line
    
    tokens = rest.split()
    if len(tokens) < 2:
        return line
    
    end_idx = 0
    for i, tok in enumerate(tokens):
        raw = tok.rstrip('.,;:!?')
        lower = raw.lower()
        
        if i > 0 and (lower in AUX_OR_VERB or raw.endswith(':')):
            break
        if i == 5:  # cap at 6 tokens (0..5)
            end_idx = i
            break
        
        end_idx = i
        if lower in AUX_OR_VERB:
            break
    
    phrase_tokens = tokens[: end_idx + 1]
    
    # Avoid bolding pronoun-only phrase
    if len(phrase_tokens) == 1 and phrase_tokens[0].lower() in {"it", "there", "this", "that"}:
        return line
    
    phrase = " ".join(phrase_tokens)
    
    # Reconstruct
    remainder = " ".join(tokens[end_idx + 1 :])
    if not remainder:
        return line
    
    return f"{prefix}**{phrase}** {remainder}"


def clean_text(text: str) -> str:
    """
    Clean and normalize text content.
    
    Args:
        text: Raw text to clean
        
    Returns:
        Cleaned text
    """
    if not text:
        return ""
    
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    
    # Remove excessive newlines
    text = re.sub(r'\n\s*\n\s*\n+', '\n\n', text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def extract_key_phrases(text: str, max_phrases: int = 10) -> List[str]:
    """
    Extract key phrases from text using simple heuristics.
    
    Args:
        text: Text to analyze
        max_phrases: Maximum number of phrases to return
        
    Returns:
        List of key phrases
    """
    if not text:
        return []
    
    # Simple approach: look for capitalized phrases
    phrases = []
    
    # Find quoted phrases
    quoted_matches = re.findall(r'"([^"]{3,50})"', text)
    phrases.extend(quoted_matches)
    
    # Find title-case phrases (2-4 words)
    title_matches = re.findall(r'\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3}\b', text)
    phrases.extend(title_matches)
    
    # Remove duplicates and sort by length (longer phrases first)
    unique_phrases = list(set(phrases))
    unique_phrases.sort(key=len, reverse=True)
    
    return unique_phrases[:max_phrases]


def truncate_text(text: str, max_length: int = 500, ellipsis: str = "...") -> str:
    """
    Truncate text to specified length, preserving word boundaries.
    
    Args:
        text: Text to truncate
        max_length: Maximum length including ellipsis
        ellipsis: String to append when truncating
        
    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text
    
    # Account for ellipsis length
    target_length = max_length - len(ellipsis)
    
    if target_length <= 0:
        return ellipsis
    
    # Find last word boundary within target length
    truncated = text[:target_length]
    last_space = truncated.rfind(' ')
    
    if last_space > 0:
        truncated = truncated[:last_space]
    
    return truncated + ellipsis


def count_tokens_estimate(text: str) -> int:
    """
    Rough estimate of token count for text.
    
    Uses simple heuristic: ~4 characters per token for English text.
    For more accurate counting, use tiktoken when available.
    
    Args:
        text: Text to count tokens for
        
    Returns:
        Estimated token count
    """
    if not text:
        return 0
    
    # Try to use tiktoken if available
    try:
        import tiktoken
        encoding = tiktoken.get_encoding("cl100k_base")  # GPT-4 encoding
        return len(encoding.encode(text))
    except ImportError:
        # Fallback to simple estimation
        return len(text) // 4


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Formatted size string
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024.0:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024.0
    return f"{size_bytes:.1f} TB"