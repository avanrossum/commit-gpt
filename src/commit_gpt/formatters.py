"""Commit message formatters and validators."""

import re
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class CommitMessage:
    """Structured commit message."""
    subject: str
    body: Optional[str] = None
    pr_title: Optional[str] = None
    pr_summary: Optional[str] = None


class ConventionalFormatter:
    """Conventional commit formatter."""
    
    TYPES = {
        'feat': 'Features',
        'fix': 'Bug fixes',
        'docs': 'Documentation',
        'style': 'Code style changes',
        'refactor': 'Code refactoring',
        'perf': 'Performance improvements',
        'test': 'Adding or updating tests',
        'build': 'Build system changes',
        'ci': 'CI/CD changes',
        'chore': 'Maintenance tasks',
        'revert': 'Reverting changes'
    }
    
    def __init__(self):
        self.type_pattern = re.compile(r'^(feat|fix|docs|style|refactor|perf|test|build|ci|chore|revert)(\(.+\))?: .+')
    
    def validate(self, subject: str) -> bool:
        """Validate conventional commit format."""
        return bool(self.type_pattern.match(subject))
    
    def offline(self, ctx: Dict) -> Tuple[str, Optional[str]]:
        """Generate conventional commit message using heuristics."""
        diff = ctx.get('diff', '')
        repo = ctx.get('repo', 'unknown')
        
        # Analyze diff to determine type and scope
        commit_type, scope = self._analyze_diff(diff, repo)
        
        # Generate subject
        subject = self._generate_subject(diff, commit_type, scope)
        
        # Generate body
        body = self._generate_body(diff)
        
        return subject, body
    
    def _analyze_diff(self, diff: str, repo: str) -> Tuple[str, Optional[str]]:
        """Analyze diff to determine commit type and scope."""
        commit_type = 'chore'
        scope = None
        
        # Check for test files
        if re.search(r'test.*\.py', diff, re.IGNORECASE):
            commit_type = 'test'
        # Check for documentation
        elif re.search(r'\.md$|\.rst$|docs/', diff, re.IGNORECASE):
            commit_type = 'docs'
        # Check for new features (new files, function definitions)
        elif re.search(r'def\s+\w+\(|class\s+\w+', diff, re.IGNORECASE):
            commit_type = 'feat'
        # Check for bug fixes (error handling, bug-related keywords)
        elif re.search(r'fix|bug|error|exception', diff, re.IGNORECASE):
            commit_type = 'fix'
        # Check for performance improvements
        elif re.search(r'perf|optimize|cache|speed', diff, re.IGNORECASE):
            commit_type = 'perf'
        # Check for refactoring
        elif re.search(r'refactor|cleanup|simplify', diff, re.IGNORECASE):
            commit_type = 'refactor'
        
        # Determine scope from file paths
        scope = self._extract_scope(diff, repo)
        
        return commit_type, scope
    
    def _extract_scope(self, diff: str, repo: str) -> Optional[str]:
        """Extract scope from file paths."""
        # Look for top-level directories
        dirs = re.findall(r'[+-]{3} [ab]/([^/]+)/', diff)
        if dirs:
            # Get most common directory
            from collections import Counter
            counter = Counter(dirs)
            return counter.most_common(1)[0][0]
        
        # Look for common package patterns
        if re.search(r'src/', diff):
            return 'src'
        elif re.search(r'tests/', diff):
            return 'test'
        
        return None
    
    def _generate_subject(self, diff: str, commit_type: str, scope: Optional[str]) -> str:
        """Generate commit subject from diff."""
        # Extract file names
        files = re.findall(r'[+-]{3} [ab]/([^\t\n]+)', diff)
        if not files:
            return f"{commit_type}: update files"
        
        # Get primary file
        primary_file = files[0]
        if '/' in primary_file:
            primary_file = primary_file.split('/')[-1]
        
        # Remove extension for cleaner subject
        if '.' in primary_file:
            primary_file = primary_file.rsplit('.', 1)[0]
        
        # Generate verb based on type
        verbs = {
            'feat': 'add',
            'fix': 'fix',
            'docs': 'update',
            'test': 'add',
            'refactor': 'refactor',
            'perf': 'optimize',
            'style': 'style',
            'build': 'update',
            'ci': 'update',
            'chore': 'update'
        }
        
        verb = verbs.get(commit_type, 'update')
        
        # Build subject
        if scope:
            subject = f"{commit_type}({scope}): {verb} {primary_file}"
        else:
            subject = f"{commit_type}: {verb} {primary_file}"
        
        return subject
    
    def _generate_body(self, diff: str) -> Optional[str]:
        """Generate commit body from diff."""
        changes = []
        
        # Count files changed
        files = set(re.findall(r'[+-]{3} [ab]/([^\t\n]+)', diff))
        if files:
            changes.append(f"- modify {len(files)} file(s)")
        
        # Count additions and deletions
        additions = len([line for line in diff.split('\n') if line.startswith('+') and not line.startswith('+++')])
        deletions = len([line for line in diff.split('\n') if line.startswith('-') and not line.startswith('---')])
        
        if additions > 0:
            changes.append(f"- add {additions} line(s)")
        if deletions > 0:
            changes.append(f"- remove {deletions} line(s)")
        
        return '\n'.join(changes) if changes else None


class CasualFormatter:
    """Casual commit formatter."""
    
    def offline(self, ctx: Dict) -> Tuple[str, Optional[str]]:
        """Generate casual commit message using heuristics."""
        diff = ctx.get('diff', '')
        
        # Extract file names
        files = re.findall(r'[+-]{3} [ab]/([^\t\n]+)', diff)
        if not files:
            return "Update files", None
        
        # Get primary file
        primary_file = files[0]
        if '/' in primary_file:
            primary_file = primary_file.split('/')[-1]
        
        # Remove extension
        if '.' in primary_file:
            primary_file = primary_file.rsplit('.', 1)[0]
        
        # Determine action
        if re.search(r'def\s+\w+\(|class\s+\w+', diff, re.IGNORECASE):
            action = "Add"
        elif re.search(r'fix|bug|error', diff, re.IGNORECASE):
            action = "Fix"
        elif re.search(r'test', diff, re.IGNORECASE):
            action = "Add tests for"
        else:
            action = "Update"
        
        subject = f"{action} {primary_file}"
        
        # Simple body
        body = f"Changes to {primary_file}"
        
        return subject, body


def enforce_limits(message: Tuple[str, Optional[str]]) -> Tuple[str, Optional[str]]:
    """Enforce line length limits on commit messages."""
    subject, body = message
    
    # Enforce 72 character limit on subject
    if len(subject) > 72:
        subject = subject[:69] + "..."
    
    # Remove trailing period
    if subject.endswith('.'):
        subject = subject[:-1]
    
    # Enforce 100 character limit on body lines
    if body:
        body_lines = []
        for line in body.split('\n'):
            if len(line) > 100:
                # Try to break at word boundaries
                words = line.split()
                current_line = ""
                for word in words:
                    if len(current_line + word) <= 100:
                        current_line += (word + " ")
                    else:
                        if current_line:
                            body_lines.append(current_line.strip())
                        current_line = word + " "
                if current_line:
                    body_lines.append(current_line.strip())
            else:
                body_lines.append(line)
        body = '\n'.join(body_lines)
    
    return subject, body


# Global formatter instances
format_conventional = ConventionalFormatter()
format_casual = CasualFormatter()
