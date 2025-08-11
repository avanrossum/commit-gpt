"""Git operations and repository information."""

import subprocess
import re
from typing import List, Optional


def staged_diff() -> str:
    """Get the staged diff for the current repository."""
    try:
        result = subprocess.run(
            ["git", "diff", "--staged", "--no-ext-diff", "-U3", "--minimal"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout
    except subprocess.CalledProcessError:
        return ""


def recent_subjects(count: int = 5) -> List[str]:
    """Get recent commit subjects from git log."""
    try:
        result = subprocess.run(
            ["git", "log", f"-{count}", "--pretty=format:%s"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip().split('\n') if result.stdout.strip() else []
    except subprocess.CalledProcessError:
        return []


def current_branch() -> str:
    """Get the current branch name."""
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "unknown"


def repo_name() -> str:
    """Get the repository name from git remote."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True
        )
        url = result.stdout.strip()
        # Extract repo name from various URL formats
        if url.endswith('.git'):
            url = url[:-4]
        if '/' in url:
            return url.split('/')[-1]
        return "unknown"
    except subprocess.CalledProcessError:
        return "unknown"


def uses_conventional_commits() -> bool:
    """Detect if the repository uses conventional commits."""
    subjects = recent_subjects(50)
    if not subjects:
        return False
    
    # Conventional commit pattern
    pattern = r'^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?: .+'
    conventional_count = sum(1 for subject in subjects if re.match(pattern, subject))
    
    return (conventional_count / len(subjects)) >= 0.6


def get_diff_stats(diff: str) -> dict:
    """Extract statistics from a git diff."""
    stats = {
        'files_changed': 0,
        'insertions': 0,
        'deletions': 0,
        'file_types': set(),
        'binary_files': [],
        'renames': []
    }
    
    lines = diff.split('\n')
    for line in lines:
        if line.startswith('diff --git'):
            stats['files_changed'] += 1
        elif line.startswith('Binary files'):
            stats['binary_files'].append(line)
        elif line.startswith('rename from'):
            stats['renames'].append(line)
        elif line.startswith('+') and not line.startswith('+++'):
            stats['insertions'] += 1
        elif line.startswith('-') and not line.startswith('---'):
            stats['deletions'] += 1
    
    # Extract file types
    for line in lines:
        if line.startswith('+++') or line.startswith('---'):
            if '/' in line:
                filename = line.split('/')[-1]
                if '.' in filename:
                    ext = filename.split('.')[-1]
                    stats['file_types'].add(ext)
    
    stats['file_types'] = list(stats['file_types'])
    return stats


def suggest_commit_groups(diff: str) -> list:
    """Suggest logical groups for splitting a large diff into multiple commits."""
    groups = []
    current_group = []
    current_files = []
    
    lines = diff.split('\n')
    i = 0
    
    while i < len(lines):
        line = lines[i]
        
        if line.startswith('diff --git'):
            # Start a new file
            if current_group and len(current_group) > 10:  # Only create groups with substantial content
                groups.append({
                    'files': current_files,
                    'diff': '\n'.join(current_group)
                })
            
            current_group = [line]
            current_files = [line.split()[-1].split('/')[-1]]  # Extract filename
            i += 1
            
            # Collect all lines for this file
            while i < len(lines) and not lines[i].startswith('diff --git'):
                current_group.append(lines[i])
                i += 1
        else:
            current_group.append(line)
            i += 1
    
    # Add the last group
    if current_group and len(current_group) > 10:
        groups.append({
            'files': current_files,
            'diff': '\n'.join(current_group)
        })
    
    return groups
