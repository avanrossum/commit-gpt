"""Additional tests for redaction utilities."""

from commit_gpt.redact import get_redaction_summary, truncate_for_tokens


def test_truncate_for_tokens():
    text = "a" * 100
    truncated = truncate_for_tokens(text, max_tokens=5)
    assert truncated.endswith("... (truncated)")
    assert len(truncated) < len(text)


def test_get_redaction_summary():
    original = "secret=123\nsafe=ok"
    scrubbed = "***REDACTED***\nsafe=ok"
    summary = get_redaction_summary(original, scrubbed)
    assert summary["original_lines"] == 2
    assert summary["scrubbed_lines"] == 2
    assert summary["redacted_lines"] == 1
