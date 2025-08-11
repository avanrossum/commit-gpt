"""Basic tests for commit-gpt."""

from unittest.mock import patch

from commit_gpt.formatters import CasualFormatter, ConventionalFormatter, enforce_limits
from commit_gpt.redact import estimate_tokens, scrub
from commit_gpt.risk import RiskReport, assess


class TestConventionalFormatter:
    """Test conventional commit formatter."""

    def setup_method(self):
        self.formatter = ConventionalFormatter()

    def test_validate_valid_conventional(self):
        """Test validation of valid conventional commits."""
        valid_commits = [
            "feat: add user authentication",
            "fix(auth): resolve token refresh issue",
            "docs: update API documentation",
            "test: add unit tests for auth module",
            "refactor(core): simplify database connection",
        ]

        for commit in valid_commits:
            assert self.formatter.validate(commit), f"Should validate: {commit}"

    def test_validate_invalid_conventional(self):
        """Test validation of invalid conventional commits."""
        invalid_commits = [
            "add user authentication",
            "fix auth: resolve token refresh issue",
            "docs update API documentation",
            "test add unit tests",
        ]

        for commit in invalid_commits:
            assert not self.formatter.validate(commit), f"Should not validate: {commit}"

    def test_offline_generation(self):
        """Test offline commit message generation."""
        ctx = {
            "diff": """diff --git a/src/auth.py b/src/auth.py
+++ b/src/auth.py
@@ -0,0 +1,10 @@
+def login(username, password):
+    # authentication logic
+    pass
+
+def logout():
+    # logout logic
+    pass
+""",
            "repo": "test-repo",
        }

        subject, body = self.formatter.offline(ctx)

        assert subject.startswith("feat")
        assert "auth" in subject.lower()
        assert body is not None


class TestCasualFormatter:
    """Test casual commit formatter."""

    def setup_method(self):
        self.formatter = CasualFormatter()

    def test_offline_generation(self):
        """Test offline casual commit message generation."""
        ctx = {
            "diff": """diff --git a/src/auth.py b/src/auth.py
+++ b/src/auth.py
@@ -0,0 +1,5 @@
+def login(username, password):
+    pass
+"""
        }

        subject, body = self.formatter.offline(ctx)

        assert "auth" in subject.lower()
        assert body is not None


class TestEnforceLimits:
    """Test commit message limit enforcement."""

    def test_subject_length_limit(self):
        """Test 72 character limit on subject."""
        long_subject = "a" * 80
        short_body = "Short body"

        result_subject, result_body = enforce_limits((long_subject, short_body))

        assert len(result_subject) <= 72
        assert result_subject.endswith("...")

    def test_remove_trailing_period(self):
        """Test removal of trailing period from subject."""
        subject_with_period = "feat: add authentication."
        body = "Test body"

        result_subject, result_body = enforce_limits((subject_with_period, body))

        assert not result_subject.endswith(".")

    def test_body_line_length_limit(self):
        """Test 100 character limit on body lines."""
        subject = "feat: test"
        long_body = "a" * 120

        result_subject, result_body = enforce_limits((subject, long_body))

        for line in result_body.split("\n"):
            assert len(line) <= 100


class TestRiskAssessment:
    """Test risk assessment functionality."""

    def test_no_risk(self):
        """Test assessment with no risks."""
        diff = """diff --git a/src/utils.py b/src/utils.py
+++ b/src/utils.py
@@ -0,0 +1,5 @@
+def helper_function():
+    return True
+"""

        risk = assess(diff)

        assert isinstance(risk, RiskReport)
        assert risk.score == 0.0
        assert "No significant risks" in risk.report

    def test_secret_detection(self):
        """Test detection of secrets in diff."""
        diff = """diff --git a/config.py b/config.py
+++ b/config.py
@@ -0,0 +1,3 @@
+api_key = "sk-1234567890abcdef"
+aws_access_key_id = "AKIA1234567890ABCDEF"
+password = "secret123"
+"""

        risk = assess(diff)

        assert risk.score > 0.0
        assert "secrets" in risk.report.lower()
        assert "🔒" in str(risk.checklist)

    def test_destructive_changes(self):
        """Test detection of destructive changes."""
        diff = """diff --git a/script.sql b/script.sql
+++ b/script.sql
@@ -0,0 +1,2 @@
+DROP TABLE users;
+DELETE FROM sessions;
+"""

        risk = assess(diff)

        assert risk.score > 0.0
        assert "destructive" in risk.report.lower()
        assert "[WARNING]" in str(risk.checklist)


class TestRedaction:
    """Test redaction functionality."""

    def test_basic_redaction(self):
        """Test basic secret redaction."""
        diff = """diff --git a/config.py b/config.py
+++ b/config.py
@@ -0,0 +1,3 @@
+api_key = "sk-1234567890abcdef"
+password = "secret123"
+normal_var = "safe_value"
+"""

        scrubbed = scrub(diff)

        assert "***REDACTED***" in scrubbed
        assert "normal_var" in scrubbed
        assert "safe_value" in scrubbed

    def test_file_exclusion(self):
        """Test exclusion of sensitive files."""
        diff = """diff --git a/.env b/.env
+++ b/.env
@@ -0,0 +1,2 @@
+API_KEY=secret
+PASSWORD=secret
+"""

        scrubbed = scrub(diff)

        # Should be completely excluded
        assert ".env" not in scrubbed
        assert "API_KEY" not in scrubbed

    def test_token_estimation(self):
        """Test token estimation."""
        text = "This is a test string with some content."
        tokens = estimate_tokens(text)

        assert isinstance(tokens, int)
        assert tokens > 0


class TestIntegration:
    """Test integration scenarios."""

    @patch("commit_gpt.gitio.staged_diff")
    def test_basic_workflow(self, mock_staged_diff):
        """Test basic workflow with mocked git operations."""
        mock_staged_diff.return_value = """diff --git a/src/test.py b/src/test.py
+++ b/src/test.py
@@ -0,0 +1,5 @@
+def test_function():
+    return True
+"""

        # This would test the full workflow if we had the CLI module imported
        # For now, just verify the mock works
        assert "test_function" in mock_staged_diff.return_value
