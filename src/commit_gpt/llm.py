"""LLM integration for commit message generation."""

import hashlib
import json
import os
import sqlite3
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

from .redact import estimate_tokens, truncate_for_tokens


@dataclass
class LLMResponse:
    """LLM response with metadata."""

    subject: str
    body: Optional[str] = None
    pr_title: Optional[str] = None
    pr_summary: Optional[str] = None
    rationale: str = ""
    cost: float = 0.0


class LLMProvider:
    """Base class for LLM providers."""

    def __init__(self, api_key: str):
        self.api_key = api_key

    def generate(self, prompt: str, max_tokens: int = 500) -> Tuple[str, float]:
        """Generate response and return cost estimate."""
        raise NotImplementedError


class OpenAIProvider(LLMProvider):
    """OpenAI GPT provider."""

    def __init__(self, api_key: str):
        super().__init__(api_key)
        try:
            import openai

            self.client = openai.OpenAI(api_key=api_key)
        except ImportError:
            raise ImportError("OpenAI package not installed. Run: pip install openai")

    def generate(self, prompt: str, max_tokens: int = 500) -> Tuple[str, float]:
        """Generate response using OpenAI model."""
        try:
            # Get model from environment variable, default to gpt-4o
            model = os.getenv("COMMIT_GPT_OPENAI_MODEL", "gpt-4o")

            response = self.client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": self._get_system_prompt()},
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tokens,
                temperature=0.3,
            )

            content = response.choices[0].message.content
            cost = self._calculate_cost(response.usage.total_tokens)

            return content, cost

        except Exception as e:
            raise Exception(f"OpenAI API error: {e}")

    def _get_system_prompt(self) -> str:
        """Get system prompt for commit message generation."""
        return """You generate precise git commit subjects and optional bodies from diffs. 

You are to treat ALL included diffs as a single commit, with all changes being part of the same commit. Your goal is to create a comprehensive commit message that covers all of the changes in each diff into one comprehensive commit message. If you are provided with a "purpose" from the user, you should use that as context for why the changes were made and what the motivation was behind the changes.

Prefer Conventional Commits unless told otherwise. Max 72 chars for subjects. 
Never invent changes. Cite file paths sparingly. Avoid trailing periods in subjects.
Respond in the exact format specified by the user."""

    def _calculate_cost(self, tokens: int) -> float:
        """Calculate cost for OpenAI model."""
        # Get model from environment variable, default to gpt-4o
        model = os.getenv("COMMIT_GPT_OPENAI_MODEL", "gpt-4o")

        # Pricing per 1M tokens (input, output) - converted to per 1K tokens
        pricing = {
            "gpt-4o": (0.0025, 0.01),  # GPT-4o: $2.50/$10 per 1M tokens
            "gpt-4o-mini": (0.00015, 0.0006),  # GPT-4o-mini: $0.15/$0.60 per 1M tokens
            "gpt-4-turbo": (0.01, 0.03),  # GPT-4-turbo: $10/$30 per 1M tokens
            "gpt-4": (0.03, 0.06),  # GPT-4: $30/$60 per 1M tokens
            "gpt-4.1": (0.002, 0.008),  # GPT-4.1: $2.00/$8.00 per 1M tokens
            "gpt-4.1-mini": (0.0004, 0.0016),  # GPT-4.1-mini: $0.40/$1.60 per 1M tokens
            "gpt-4.1-nano": (0.0001, 0.0004),  # GPT-4.1-nano: $0.10/$0.40 per 1M tokens
            "gpt-4.5": (0.075, 0.15),  # GPT-4.5: $75/$150 per 1M tokens
        }

        # Default to GPT-4o pricing if model not found
        input_rate, output_rate = pricing.get(model, pricing["gpt-4o"])

        # Rough estimate: assume 2:1 input/output ratio
        input_cost = (tokens * 0.6) / 1000 * input_rate
        output_cost = (tokens * 0.4) / 1000 * output_rate
        return input_cost + output_cost


class AnthropicProvider(LLMProvider):
    """Anthropic Claude provider."""

    def __init__(self, api_key: str):
        super().__init__(api_key)
        try:
            import anthropic

            self.client = anthropic.Anthropic(api_key=api_key)
        except ImportError:
            raise ImportError("Anthropic package not installed. Run: pip install anthropic")

    def generate(self, prompt: str, max_tokens: int = 500) -> Tuple[str, float]:
        """Generate response using Anthropic Claude."""
        try:
            response = self.client.messages.create(
                model="claude-3-sonnet-20240229",
                max_tokens=max_tokens,
                temperature=0.3,
                system=self._get_system_prompt(),
                messages=[{"role": "user", "content": prompt}],
            )

            content = response.content[0].text
            cost = self._calculate_cost(response.usage.input_tokens, response.usage.output_tokens)

            return content, cost

        except Exception as e:
            raise Exception(f"Anthropic API error: {e}")

    def _get_system_prompt(self) -> str:
        """Get system prompt for commit message generation."""
        return """You generate precise git commit subjects and optional bodies from diffs. 

        You are to treat ALL included diffs as a single commit, with all changes being part of the same commit. Your goal is to create a comprehensive commit message that covers all of the changes in each diff into one comprehensive commit message.  If you are provided with a "purpose" from the user, you should use that as context for why the cahnges were made and what 6the motivation was behind the changes.

Prefer Conventional Commits unless told otherwise. Max 72 chars for subjects. 
Never invent changes. Cite file paths sparingly. Avoid trailing periods in subjects.
Respond in the exact format specified by the user."""

    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for Claude-3-sonnet."""
        # Claude-3-sonnet pricing: $3 per 1M input tokens, $15 per 1M output tokens
        input_cost = (input_tokens / 1_000_000) * 3
        output_cost = (output_tokens / 1_000_000) * 15
        return input_cost + output_cost


class Cache:
    """SQLite cache for LLM responses."""

    def __init__(self, db_path: str = "~/.commit-gpt/cache.db"):
        self.db_path = os.path.expanduser(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        """Initialize database."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    prompt_hash TEXT PRIMARY KEY,
                    response TEXT,
                    cost REAL,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

    def get(self, prompt: str) -> Optional[Tuple[str, float]]:
        """Get cached response."""
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT response, cost FROM cache WHERE prompt_hash = ?", (prompt_hash,)
            )
            result = cursor.fetchone()

            if result:
                return json.loads(result[0]), result[1]
            return None

    def set(self, prompt: str, response: str, cost: float):
        """Cache response."""
        prompt_hash = hashlib.md5(prompt.encode()).hexdigest()

        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT OR REPLACE INTO cache (prompt_hash, response, cost) VALUES (?, ?, ?)",
                (prompt_hash, json.dumps(response), cost),
            )


def have_llm() -> bool:
    """Check if LLM API key is available."""
    return bool(os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))


def get_provider() -> Optional[LLMProvider]:
    """Get configured LLM provider."""
    if os.getenv("OPENAI_API_KEY"):
        return OpenAIProvider(os.getenv("OPENAI_API_KEY"))
    elif os.getenv("ANTHROPIC_API_KEY"):
        return AnthropicProvider(os.getenv("ANTHROPIC_API_KEY"))
    return None


def is_diff_too_large(diff: str, max_tokens: int = 30000) -> bool:
    """Check if a diff is too large for safe AI processing."""
    # Estimate tokens for the diff plus some overhead for prompt
    estimated_tokens = estimate_tokens(diff) + 500  # Add 500 tokens for prompt overhead
    return estimated_tokens > max_tokens


def build_prompt(ctx: Dict, style: str = "conventional", want_pr: bool = False) -> str:
    """Build prompt for LLM."""
    from .prompts import format_user_prompt

    return format_user_prompt(ctx, style, want_pr)


def parse_llm_response(response: str, ctx: Optional[Dict] = None) -> LLMResponse:
    """Parse LLM response into structured format."""
    lines = response.strip().split("\n")

    subject = ""
    body_lines = []
    pr_title = ""
    pr_summary_lines = []

    in_body = False
    in_pr_summary = False

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # Handle standard format
        if line.startswith("SUBJECT:"):
            subject = line[8:].strip()
        elif line.startswith("BODY:"):
            in_body = True
            in_pr_summary = False
        elif line.startswith("PR_TITLE:"):
            pr_title = line[10:].strip()
            in_body = False
        elif line.startswith("PR_SUMMARY:"):
            in_pr_summary = True
            in_body = False
        # Handle markdown format (fallback)
        elif (
            line.startswith("- **Commit**:")
            or line.startswith("- **Subject**:")
            or line.startswith("- **Commit Subject:**")
        ):
            subject = line.split(":", 1)[1].strip()
        elif line.startswith("- **Body**:") or line.startswith("- **Commit Body:**"):
            in_body = True
            in_pr_summary = False
        elif line.startswith("- **PR Title**:"):
            pr_title = line.split(":", 1)[1].strip()
            in_body = False
        elif line.startswith("- **PR Summary**:"):
            in_pr_summary = True
            in_body = False
        elif in_body and line.startswith("-"):
            body_lines.append(line)
        elif in_pr_summary and line.startswith("-"):
            pr_summary_lines.append(line)

    # If no subject found but we have a PR title, use it as subject
    if not subject and pr_title:
        subject = pr_title
        pr_title = None  # Don't duplicate

    # Fallback: if no subject found, use the first non-empty line
    if not subject:
        for line in lines:
            line = line.strip()
            if (
                line
                and not line.startswith("-")
                and not line.startswith("#")
                and not line.startswith("PR")
            ):
                # Clean up the line and use as subject
                clean_line = line.replace("PR Title:", "").replace("PR Summary:", "").strip()
                if clean_line:
                    subject = clean_line[:72]  # Truncate to 72 chars
                    break

    return LLMResponse(
        subject=subject or "Update files",
        body="\n".join(body_lines) if body_lines else None,
        pr_title=pr_title if pr_title else None,
        pr_summary="\n".join(pr_summary_lines) if pr_summary_lines else None,
    )


def summarize_diff(
    ctx: Dict, style: str = "conventional", want_pr: bool = False, max_cost: float = 0.02
) -> Tuple[LLMResponse, str, float]:
    """Generate commit message using LLM."""
    provider = get_provider()
    if not provider:
        raise Exception("No LLM provider configured")

    # Build prompt
    prompt = build_prompt(ctx, style, want_pr)

    # Check cache
    cache = Cache()
    cached = cache.get(prompt)
    if cached:
        response_text, cost = cached
        response = parse_llm_response(response_text, ctx)
        return response, "Using cached response", cost

    # Truncate if needed
    prompt = truncate_for_tokens(prompt, 15000)

    # Generate response
    response_text, cost = provider.generate(prompt)

    # Check cost limit
    if cost > max_cost:
        raise Exception(f"Cost ${cost:.4f} exceeds limit ${max_cost:.4f}")

    # Parse response
    response = parse_llm_response(response_text, ctx)

    # Cache response
    cache.set(prompt, response_text, cost)

    return response, "Generated with AI", cost
