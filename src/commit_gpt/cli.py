"""Main CLI interface for commit-gpt."""

import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

import typer
from pydantic import BaseModel

from .gitio import staged_diff, recent_subjects, current_branch, repo_name, suggest_commit_groups
from .redact import scrub, estimate_tokens
from .llm import summarize_diff, have_llm, is_diff_too_large
from .formatters import format_conventional, format_casual, enforce_limits
from .risk import assess


def load_env_file():
    """Automatically load .env file if it exists."""
    # Look for .env in current directory and parent directories
    current_dir = Path.cwd()
    search_dirs = [current_dir] + list(current_dir.parents)
    
    # Also look in the commit-gpt installation directory
    try:
        import commit_gpt
        commit_gpt_dir = Path(commit_gpt.__file__).parent.parent.parent
        search_dirs.append(commit_gpt_dir)
    except ImportError:
        pass
    
    for parent in search_dirs:
        env_file = parent / '.env'
        if env_file.exists():
            try:
                with open(env_file, 'r') as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith('#') and '=' in line:
                            key, value = line.split('=', 1)
                            os.environ[key.strip()] = value.strip()
                return True
            except Exception:
                pass
    return False

app = typer.Typer(add_completion=False, help="AI-powered git commit message generator")


class CommitOutput(BaseModel):
    """Output structure for commit messages."""
    subject: str
    body: Optional[str] = None
    pr_title: Optional[str] = None
    pr_summary: Optional[str] = None


@app.command()
def main(
    purpose: Optional[str] = typer.Argument(None, help="Your purpose/intent for these changes (e.g., 'updated the tool chain')"),
    write: bool = typer.Option(False, "--write", "-w", help="Write commit to git"),
    style: str = typer.Option("conventional", "--style", "-s", help="Commit style: conventional or casual"),
    pr: bool = typer.Option(False, "--pr", help="Generate PR title and summary"),
    explain: bool = typer.Option(False, "--explain", "-e", help="Show rationale and cost estimate"),
    risk_check: bool = typer.Option(False, "--risk-check", help="Exit with code 2 if risk > threshold"),
    range: Optional[str] = typer.Option(None, "--range", "-r", help="Git range to analyze"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Use heuristic fallback only (offline)"),
    max_cost: float = typer.Option(None, "--max-$", help="Maximum cost in dollars"),
    suggest_groups: bool = typer.Option(False, "--suggest-groups", help="Suggest how to split large diffs into multiple focused commits"),
    force_write: bool = typer.Option(False, "--force-write", help="Force write even for very large diffs (not recommended)"),
) -> None:
    """Generate commit messages from git diffs using AI.
    
    Features:
    - AI-powered commit message generation
    - Risk assessment for potential issues
    - Automatic secret redaction
    - Large diff orchestration (--suggest-groups)
    - Offline heuristic fallback (--no-llm)
    """
    # Automatically load .env file if it exists
    load_env_file()
    
    try:
        # Get diff
        if range:
            diff = subprocess.check_output(
                ["git", "diff", range, "--no-ext-diff", "-U3", "--minimal"], 
                text=True, 
                stderr=subprocess.PIPE
            )
        else:
            diff = staged_diff()
        
        if not diff.strip():
            typer.echo("No diff to summarize.", err=True)
            raise typer.Exit(1)

        # Risk assessment
        risk = assess(diff)
        if risk_check and risk.score >= 0.7:
            typer.echo(risk.report, err=True)
            raise typer.Exit(2)

        # Build context
        ctx = {
            "repo": repo_name(),
            "branch": current_branch(),
            "subjects": recent_subjects(5),
            "diff": scrub(diff),
            "purpose": purpose  # Add user-provided purpose
        }

        # Generate commit message
        use_llm = have_llm() and not no_llm
        diff = ctx.get('diff', '')
        
        # Get max cost from environment if not provided
        if max_cost is None:
            import os
            max_cost = float(os.getenv('COMMIT_GPT_MAX_COST', '0.02'))
        
        # Check if diff is too large for safe AI processing
        estimated_tokens = estimate_tokens(diff)
        is_too_large = is_diff_too_large(diff)
        
        if is_too_large and not no_llm:
            if explain:
                typer.echo(f"[explain] Large diff detected ({estimated_tokens} tokens). Using offline mode for reliability.", err=True)
                typer.echo(f"[explain] Use '--suggest-groups' to split into multiple AI-powered commits.", err=True)
            use_llm = False
        
        if use_llm:
            out, rationale, cost = summarize_diff(ctx, style=style, want_pr=pr, max_cost=max_cost)
            if explain:
                typer.echo(f"[explain] ${cost:.4f} :: {rationale}", err=True)
            subject, body, pr_title, pr_sum = out.subject, out.body, out.pr_title, out.pr_summary
        else:
            formatter = format_casual if style == "casual" else format_conventional
            subject, body = enforce_limits(formatter.offline(ctx))
            pr_title = pr_sum = None

        # Handle suggest_groups for large diffs
        if suggest_groups and is_too_large:
            groups = suggest_commit_groups(diff)
            
            typer.echo(typer.style("[INFO]", fg=typer.colors.BLUE, bold=True) + f" Large diff detected ({estimated_tokens} tokens). Suggested commit groups:", err=True)
            typer.echo(f"", err=True)
            
            for i, group in enumerate(groups, 1):
                group_files = group['files']
                group_diff = group['diff']
                group_tokens = estimate_tokens(group_diff)
                
                typer.echo(f"Group {i} ({group_tokens} tokens):", err=True)
                typer.echo(f"  Files: {', '.join(group_files)}", err=True)
                typer.echo(f"", err=True)
            
            typer.echo(typer.style("[HELP]", fg=typer.colors.GREEN, bold=True) + f" To commit each group separately:", err=True)
            typer.echo(f"  1. git reset HEAD~  # Unstage all changes", err=True)
            typer.echo(f"  2. Stage files for each group: git add <files>", err=True)
            typer.echo(f"  3. Run commit-gpt for each group", err=True)
            
            typer.echo(f"", err=True)
            typer.echo(typer.style("[TIP]", fg=typer.colors.YELLOW, bold=True) + f" Large commits like this ({estimated_tokens} tokens) make code review harder", err=True)
            typer.echo(f"      and can hide important changes. Consider making smaller, focused commits", err=True)
            typer.echo(f"      as you work - it makes debugging and collaboration much easier!", err=True)
            return

        # Debug: Check if we got a valid subject
        if not subject or not subject.strip():
            typer.echo("Error: No commit subject generated", err=True)
            raise typer.Exit(1)

        # Check if this is a very large diff with a poor commit message
        very_large_threshold = 8000  # tokens
        is_very_large = estimated_tokens > very_large_threshold
        poor_message_indicators = [
            "add .env",
            "update files", 
            "modify",
            "add",
            "update",
            "change"
        ]
        has_poor_message = any(indicator in subject.lower() for indicator in poor_message_indicators)
        
        # Prevent writing poor commit messages for very large diffs
        if is_very_large and has_poor_message and write and not force_write:
            typer.echo(typer.style("[WARNING]", fg=typer.colors.RED, bold=True) + f" Refusing to write commit for very large diff ({estimated_tokens} tokens).", err=True)
            typer.echo(f"", err=True)
            typer.echo(f"The generated message '{subject}' is too generic for such a large change.", err=True)
            typer.echo(f"", err=True)
            typer.echo(typer.style("[HELP]", fg=typer.colors.GREEN, bold=True) + f" Recommended actions:", err=True)
            typer.echo(f"  1. Use --suggest-groups to split into focused commits", err=True)
            typer.echo(f"  2. Use --explain to see what's happening", err=True)
            typer.echo(f"  3. Use --force-write if you really want this message", err=True)
            typer.echo(f"", err=True)
            raise typer.Exit(1)

        # Output
        typer.echo(subject)
        if body:
            typer.echo(f"\n{body}")
        if pr and pr_title:
            typer.echo(f"\nPR_TITLE: {pr_title}\nPR_SUMMARY:\n{pr_sum}")

        # Write to git if requested
        if write:
            msg = subject + (f"\n\n{body}" if body else "")
            subprocess.run(["git", "commit", "-m", msg], check=False)

    except subprocess.CalledProcessError as e:
        typer.echo(f"Git command failed: {e}", err=True)
        raise typer.Exit(1)
    except Exception as e:
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
