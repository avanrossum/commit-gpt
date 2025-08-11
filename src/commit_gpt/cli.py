"""Main CLI interface for commit-gpt."""

import os
import subprocess
from pathlib import Path
from typing import Optional

import typer
from pydantic import BaseModel

from .formatters import enforce_limits, format_casual, format_conventional
from .gitio import current_branch, recent_subjects, repo_name, staged_diff, suggest_commit_groups
from .llm import build_prompt, have_llm, is_diff_too_large, parse_llm_response, summarize_diff
from .redact import estimate_tokens, scrub
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
        env_file = parent / ".env"
        if env_file.exists():
            try:
                with open(env_file, "r") as f:
                    for line in f:
                        line = line.strip()
                        if line and not line.startswith("#") and "=" in line:
                            key, value = line.split("=", 1)
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
    purpose: Optional[str] = typer.Argument(
        None, help="Your purpose/intent for these changes (e.g., 'updated the tool chain')"
    ),
    write: bool = typer.Option(False, "--write", "-w", help="Write commit to git"),
    style: str = typer.Option(
        "conventional", "--style", "-s", help="Commit style: conventional or casual"
    ),
    pr: bool = typer.Option(False, "--pr", help="Generate PR title and summary"),
    explain: bool = typer.Option(False, "--explain", "-e", help="Show rationale and cost estimate"),
    risk_check: bool = typer.Option(
        False, "--risk-check", help="Exit with code 2 if risk > threshold"
    ),
    range: Optional[str] = typer.Option(None, "--range", "-r", help="Git range to analyze"),
    no_llm: bool = typer.Option(False, "--no-llm", help="Use heuristic fallback only (offline)"),
    max_cost: float = typer.Option(None, "--max-$", help="Maximum cost in dollars"),
    suggest_groups: bool = typer.Option(
        False,
        "--suggest-groups",
        help="Suggest how to split large diffs into multiple focused commits",
    ),
    force_write: bool = typer.Option(
        False, "--force-write", help="Force write even for very large diffs (not recommended)"
    ),
    amend: bool = typer.Option(
        False, "--amend", help="Edit the most recent commit message in your system editor"
    ),
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
                stderr=subprocess.PIPE,
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
            "purpose": purpose,  # Add user-provided purpose
        }

        # Generate commit message
        use_llm = have_llm() and not no_llm
        diff = ctx.get("diff", "")

        # Get max cost from environment if not provided
        if max_cost is None:
            import os

            max_cost = float(os.getenv("COMMIT_GPT_MAX_COST", "0.02"))

        # Check if diff is too large for safe AI processing
        estimated_tokens = estimate_tokens(diff)
        is_too_large = is_diff_too_large(diff)

        if is_too_large and not no_llm:
            if explain:
                typer.echo(
                    f"[explain] Large diff detected ({estimated_tokens} tokens). Using offline mode for reliability.",
                    err=True,
                )
                typer.echo(
                    "[explain] Use '--suggest-groups' to split into multiple AI-powered commits.",
                    err=True,
                )
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

            typer.echo(
                typer.style("[INFO]", fg=typer.colors.BLUE, bold=True)
                + f" Large diff detected ({estimated_tokens} tokens). Suggested commit groups:",
                err=True,
            )
            typer.echo("", err=True)

            for i, group in enumerate(groups, 1):
                group_files = group["files"]
                group_diff = group["diff"]
                group_tokens = estimate_tokens(group_diff)

                typer.echo(f"Group {i} ({group_tokens} tokens):", err=True)
                typer.echo(f"  Files: {', '.join(group_files)}", err=True)
                typer.echo("", err=True)

            typer.echo(
                typer.style("[HELP]", fg=typer.colors.GREEN, bold=True)
                + " To commit each group separately:",
                err=True,
            )
            typer.echo("  1. git reset HEAD~  # Unstage all changes", err=True)
            typer.echo("  2. Stage files for each group: git add <files>", err=True)
            typer.echo("  3. Run commit-gpt for each group", err=True)

            typer.echo("", err=True)
            typer.echo(
                typer.style("[TIP]", fg=typer.colors.YELLOW, bold=True)
                + f" Large commits like this ({estimated_tokens} tokens) make code review harder",
                err=True,
            )
            typer.echo(
                "      and can hide important changes. Consider making smaller, focused commits",
                err=True,
            )
            typer.echo(
                "      as you work - it makes debugging and collaboration much easier!", err=True
            )
            return

        # Debug: Check if we got a valid subject
        if not subject or not subject.strip():
            typer.echo("Error: No commit subject generated", err=True)
            raise typer.Exit(1)

        # Check if this is a very large diff with a poor commit message
        very_large_threshold = 8000  # tokens
        is_very_large = estimated_tokens > very_large_threshold
        poor_message_indicators = ["add .env", "update files", "modify", "add", "update", "change"]
        has_poor_message = any(
            indicator in subject.lower() for indicator in poor_message_indicators
        )

        # Prevent writing poor commit messages for very large diffs
        if is_very_large and has_poor_message and write and not force_write:
            typer.echo(
                typer.style("[WARNING]", fg=typer.colors.RED, bold=True)
                + f" Refusing to write commit for very large diff ({estimated_tokens} tokens).",
                err=True,
            )
            typer.echo("", err=True)
            typer.echo(
                f"The generated message '{subject}' is too generic for such a large change.",
                err=True,
            )
            typer.echo("", err=True)
            typer.echo(
                typer.style("[HELP]", fg=typer.colors.GREEN, bold=True) + " Recommended actions:",
                err=True,
            )
            typer.echo("  1. Use --suggest-groups to split into focused commits", err=True)
            typer.echo("  2. Use --explain to see what's happening", err=True)
            typer.echo("  3. Use --force-write if you really want this message", err=True)
            typer.echo("", err=True)
            raise typer.Exit(1)

        # Handle amend mode - edit cached commit message
        if amend:
            try:
                # Check if we have a cached response for the current diff
                from .llm import Cache

                cache = Cache()

                # Build the same prompt that was used to generate the message
                prompt = build_prompt(ctx, style=style, want_pr=pr)
                cached = cache.get(prompt)

                if not cached:
                    typer.echo(
                        "Error: No cached commit message found. Run commit-gpt first to generate a message.",
                        err=True,
                    )
                    raise typer.Exit(1)

                # Get the cached response and parse it
                response_text, cost = cached
                response = parse_llm_response(response_text, ctx)

                # Create the commit message content from cached response
                msg = response.subject
                if response.body:
                    msg += f"\n\n{response.body}"

                # Write to temporary file
                import os
                import tempfile

                with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
                    f.write(msg)
                    temp_file = f.name

                # Open in editor with better detection
                editor = os.getenv("EDITOR")

                # Try common editors if EDITOR is not set
                if not editor:
                    # Check for common editors
                    for common_editor in ["code", "vim", "nano", "emacs"]:
                        try:
                            subprocess.run(
                                ["which", common_editor], check=True, capture_output=True
                            )
                            editor = common_editor
                            break
                        except subprocess.CalledProcessError:
                            continue

                    # Fallback to nano if nothing found
                    if not editor:
                        editor = "nano"

                # Handle VS Code and other editors that need special handling
                if "code" in editor:
                    # If editor already has flags, use it as is
                    if "--wait" in editor:
                        subprocess.run(editor.split() + [temp_file], check=True)
                    else:
                        # VS Code needs --wait flag to wait for file to close
                        subprocess.run([editor, "--wait", temp_file], check=True)
                else:
                    subprocess.run([editor, temp_file], check=True)

                # Read back the edited message
                with open(temp_file, "r") as f:
                    edited_msg = f.read().strip()

                # Clean up temp file
                os.unlink(temp_file)

                # Parse the edited message to extract subject and body
                lines = edited_msg.strip().split("\n")
                edited_subject = lines[0].strip()
                edited_body = "\n".join(lines[1:]).strip() if len(lines) > 1 else None

                # Update the cached response with the edited message
                # We need to reconstruct the LLM response format
                updated_response = f"SUBJECT: {edited_subject}"
                if edited_body:
                    updated_response += f"\nBODY:\n{edited_body}"

                # Update the cache with the edited response
                cache.set(prompt, updated_response, cost)

                if explain:
                    typer.echo("[explain] Updated cached commit message", err=True)

                # Output the edited message
                typer.echo(edited_subject)
                if edited_body:
                    typer.echo(f"\n{edited_body}")

                return

            except Exception as e:
                typer.echo(f"Error during amend: {e}", err=True)
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
