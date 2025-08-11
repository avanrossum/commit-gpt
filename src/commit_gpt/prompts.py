"""Prompt templates for LLM interactions."""

from typing import Dict


def get_system_prompt() -> str:
    """Get the system prompt for commit message generation."""
    return """You are an expert at analyzing git diffs and generating precise, meaningful commit messages.

Your task is to:
1. Analyze the provided git diff as a SINGLE commit
2. Generate ONE commit subject (max 72 characters) that summarizes the entire change
3. Optionally generate a commit body with bullet points covering all changes

IMPORTANT: Treat the entire diff as a single, cohesive commit. Do not generate separate commit messages for individual files unless the changes are completely unrelated. Group related changes together under one commit message.

CRITICAL: If the user provides a purpose/intent for their changes, use that context to generate a more meaningful and accurate commit message. The user's purpose should guide your understanding of why these changes were made.

Guidelines:
- Prefer Conventional Commits format unless told otherwise
- Never invent changes that aren't in the diff
- Keep subjects concise and descriptive
- Avoid trailing periods in subjects
- Cite file paths sparingly in the body
- Focus on the "what" and "why" of changes
- Use present tense for subjects
- Be specific but concise
- Group related file changes under one commit message
- When user provides purpose, incorporate that context into the commit message

Conventional Commit types:
- feat: new features
- fix: bug fixes
- docs: documentation changes
- style: formatting, missing semicolons, etc.
- refactor: code refactoring
- perf: performance improvements
- test: adding or updating tests
- build: build system changes
- ci: CI/CD changes
- chore: maintenance tasks
- revert: reverting changes"""


def get_user_prompt_template() -> str:
    """Get the user prompt template."""
    return """TASK: Generate ONE SINGLE commit message for the entire diff. Do not create separate commits for individual files.

STYLE: {style}

CONTEXT:
- Repo name: {repo}
- Branch: {branch}
- Recent subjects (last 5): {subjects}
{purpose_section}

DIFF:
{diff}

IMPORTANT: Generate exactly ONE commit message that covers all changes in the diff. Do not create multiple SUBJECT lines.

Assistant format (strict):
SUBJECT: <single line <= 72 chars covering all changes>
BODY:
- <bullet 1>
- <bullet 2>"""


def format_user_prompt(ctx: Dict, style: str = "conventional") -> str:
    """Format the user prompt with context."""
    template = get_user_prompt_template()

    # Format recent subjects
    subjects = ctx.get("subjects", [])
    subjects_str = ", ".join(subjects) if subjects else "none"

    # Format purpose section
    purpose = ctx.get("purpose")
    if purpose:
        purpose_section = f"- User purpose: {purpose}"
    else:
        purpose_section = ""

    return template.format(
        style=style,
        repo=ctx.get("repo", "unknown"),
        branch=ctx.get("branch", "unknown"),
        subjects=subjects_str,
        purpose_section=purpose_section,
        diff=ctx.get("diff", ""),
    )


def get_explanation_prompt(diff: str, generated_message: str) -> str:
    """Get prompt for explaining the generated message."""
    return f"""Explain why this commit message was generated for the following diff:

DIFF:
{diff}

GENERATED MESSAGE:
{generated_message}

Please provide a brief explanation of:
1. Why this commit type was chosen
2. What the main changes are
3. Any important context or considerations

Keep the explanation concise and focused on the reasoning behind the message generation."""


def get_risk_analysis_prompt(diff: str) -> str:
    """Get prompt for risk analysis."""
    return f"""Analyze the following git diff for potential risks:

DIFF:
{diff}

Please identify:
1. Any exposed secrets or sensitive data
2. Destructive operations (deletions, drops, etc.)
3. Production-touching changes
4. Breaking changes
5. Large-scale modifications
6. Test file removals
7. Database migrations

For each risk found, provide:
- Risk level (LOW/MEDIUM/HIGH)
- Description of the risk
- Recommended action

If no significant risks are found, indicate that the changes appear safe."""
