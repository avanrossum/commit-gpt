"""Redaction utilities for scrubbing sensitive data from diffs."""

import re
import tiktoken
from typing import List


# Patterns for sensitive data
SECRET_PATTERNS = [
    # AWS keys
    r'AKIA[0-9A-Z]{16}',
    r'aws_access_key_id\s*=\s*[^\s]+',
    r'aws_secret_access_key\s*=\s*[^\s]+',
    
    # API keys
    r'api_key\s*[:=]\s*["\']?[a-zA-Z0-9]{32,}["\']?',
    r'api_token\s*[:=]\s*["\']?[a-zA-Z0-9]{32,}["\']?',
    
    # JWT tokens
    r'eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*',
    
    # Private keys
    r'-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----',
    r'-----BEGIN\s+OPENSSH\s+PRIVATE\s+KEY-----',
    r'-----BEGIN\s+DSA\s+PRIVATE\s+KEY-----',
    
    # Passwords
    r'password\s*[:=]\s*["\']?[^\s"\']+["\']?',
    r'passwd\s*[:=]\s*["\']?[^\s"\']+["\']?',
    
    # Database URLs
    r'postgresql://[^@]+@[^\s]+',
    r'mysql://[^@]+@[^\s]+',
    r'mongodb://[^@]+@[^\s]+',
    
    # OAuth tokens
    r'access_token\s*[:=]\s*["\']?[a-zA-Z0-9]{32,}["\']?',
    r'refresh_token\s*[:=]\s*["\']?[a-zA-Z0-9]{32,}["\']?',
]

# File patterns to completely exclude
EXCLUDED_FILES = [
    r'\.env$',
    r'\.env\..*$',
    r'id_rsa$',
    r'id_rsa\.pub$',
    r'\.pem$',
    r'\.key$',
    r'secrets\.json$',
    r'config\.json$',
    r'credentials\.json$',
]


def scrub(diff: str, max_lines_per_file: int = 50) -> str:
    """Scrub sensitive information from a git diff."""
    if not diff.strip():
        return diff
    
    lines = diff.split('\n')
    scrubbed_lines = []
    current_file = None
    file_line_count = 0
    
    for line in lines:
        # Check if this is a file header
        if line.startswith('diff --git') or line.startswith('+++') or line.startswith('---'):
            current_file = line
            file_line_count = 0
            scrubbed_lines.append(line)
            continue
        
        # Skip excluded files entirely
        if any(re.search(pattern, line) for pattern in EXCLUDED_FILES):
            continue
        
        # Limit lines per file
        if current_file and file_line_count >= max_lines_per_file:
            if file_line_count == max_lines_per_file:
                scrubbed_lines.append("... (truncated)")
            continue
        
        # Scrub sensitive patterns
        scrubbed_line = line
        for pattern in SECRET_PATTERNS:
            scrubbed_line = re.sub(pattern, "***REDACTED***", scrubbed_line, flags=re.IGNORECASE)
        
        scrubbed_lines.append(scrubbed_line)
        file_line_count += 1
    
    return '\n'.join(scrubbed_lines)


def estimate_tokens(text: str) -> int:
    """Estimate token count using tiktoken."""
    try:
        # Use GPT-3.5-turbo tokenizer (closest to what we're using)
        encoding = tiktoken.encoding_for_model("gpt-3.5-turbo")
        return len(encoding.encode(text))
    except Exception:
        # Fallback to rough approximation: 1 token ≈ 4 characters
        return len(text) // 4


def truncate_for_tokens(text: str, max_tokens: int = 4000) -> str:
    """Truncate text to stay within token limits."""
    estimated_tokens = estimate_tokens(text)
    if estimated_tokens <= max_tokens:
        return text
    
    # Truncate to approximately max_tokens
    max_chars = max_tokens * 4
    truncated = text[:max_chars]
    
    # Try to break at a reasonable point
    last_newline = truncated.rfind('\n')
    if last_newline > max_chars * 0.8:  # If we can break at 80% or later
        truncated = truncated[:last_newline]
    
    return truncated + "\n... (truncated)"


def get_redaction_summary(original: str, scrubbed: str) -> dict:
    """Get a summary of what was redacted."""
    original_lines = len(original.split('\n'))
    scrubbed_lines = len(scrubbed.split('\n'))
    
    redacted_count = sum(1 for line in scrubbed.split('\n') if '***REDACTED***' in line)
    
    return {
        'original_lines': original_lines,
        'scrubbed_lines': scrubbed_lines,
        'redacted_lines': redacted_count,
        'truncated': original_lines > scrubbed_lines
    }
