"""Risk assessment for commit analysis."""

import re
from dataclasses import dataclass
from typing import List


@dataclass
class RiskReport:
    """Risk assessment report."""

    score: float  # 0.0 to 1.0
    report: str
    findings: List[str]
    checklist: List[str]


# Risk patterns
SECRET_PATTERNS = [
    r"AKIA[0-9A-Z]{16}",  # AWS access keys
    r"aws_access_key_id\s*=\s*[^\s]+",
    r"aws_secret_access_key\s*=\s*[^\s]+",
    r'api_key\s*[:=]\s*["\']?[a-zA-Z0-9]{32,}["\']?',
    r"eyJ[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*",  # JWT
    r"-----BEGIN\s+(RSA\s+)?PRIVATE\s+KEY-----",
]

DESTRUCTIVE_PATTERNS = [
    r"DROP\s+TABLE",
    r"DELETE\s+FROM",
    r"TRUNCATE\s+TABLE",
    r"rm\s+-rf",
    r"rmdir\s+/",
]

PROD_TOUCHING_PATTERNS = [
    r"env/prod/",
    r"production/",
    r"prod\.",
    r"live\.",
    r"k8s/prod/",
    r"terraform/prod/",
]

BREAKING_PATTERNS = [
    r"BREAKING\s+CHANGE",
    r"breaking\s+change",
    r"version\s+[0-9]+\.[0-9]+\.0",  # Major version bump
    r"api/v[0-9]+/",
]


def assess(diff: str) -> RiskReport:
    """Assess risk level of a git diff."""
    findings = []
    checklist = []
    score = 0.0

    # Check for secrets
    secret_count = 0
    for pattern in SECRET_PATTERNS:
        matches = re.findall(pattern, diff, re.IGNORECASE)
        secret_count += len(matches)

    if secret_count > 0:
        findings.append(f"Found {secret_count} potential secrets")
        score += 0.4
        checklist.append("🔒 Review for exposed secrets")

    # Check for destructive changes
    destructive_count = 0
    for pattern in DESTRUCTIVE_PATTERNS:
        matches = re.findall(pattern, diff, re.IGNORECASE)
        destructive_count += len(matches)

    if destructive_count > 0:
        findings.append(f"Found {destructive_count} destructive operations")
        score += 0.3
        checklist.append("[WARNING] Review destructive operations")

    # Check for production-touching files
    prod_files = []
    for pattern in PROD_TOUCHING_PATTERNS:
        matches = re.findall(pattern, diff, re.IGNORECASE)
        prod_files.extend(matches)

    if prod_files:
        findings.append(f"Touches production files: {', '.join(set(prod_files))}")
        score += 0.2
        checklist.append("🚨 Review production changes")

    # Check for breaking changes
    breaking_count = 0
    for pattern in BREAKING_PATTERNS:
        matches = re.findall(pattern, diff, re.IGNORECASE)
        breaking_count += len(matches)

    if breaking_count > 0:
        findings.append(f"Found {breaking_count} potential breaking changes")
        score += 0.2
        checklist.append("💥 Review for breaking changes")

    # Check for large deletions
    deletion_lines = len(
        [line for line in diff.split("\n") if line.startswith("-") and not line.startswith("---")]
    )
    if deletion_lines > 100:
        findings.append(f"Large deletion: {deletion_lines} lines removed")
        score += 0.1
        checklist.append("[WARNING] Review large deletions")

    # Check for test file removals
    test_removals = re.findall(r"--- a/.*test.*\.py", diff, re.IGNORECASE)
    if test_removals:
        findings.append(f"Removing test files: {len(test_removals)} files")
        score += 0.1
        checklist.append("[WARNING] Review test file removals")

    # Check for migration files
    migration_files = re.findall(r"[+-].*migration.*\.py", diff, re.IGNORECASE)
    if migration_files:
        findings.append("Database migration detected")
        score += 0.1
        checklist.append("[INFO] Review database migrations")

    # Cap score at 1.0
    score = min(score, 1.0)

    # Generate report
    if findings:
        report = f"Risk Score: {score:.1f}/1.0 - {'; '.join(findings)}"
    else:
        report = "Risk Score: 0.0/1.0 - No significant risks detected"
        checklist.append("[OK] All clear")

    return RiskReport(score=score, report=report, findings=findings, checklist=checklist)


def get_risk_level(score: float) -> str:
    """Get risk level description."""
    if score >= 0.7:
        return "HIGH"
    elif score >= 0.4:
        return "MEDIUM"
    elif score >= 0.1:
        return "LOW"
    else:
        return "NONE"


def format_risk_report(risk: RiskReport) -> str:
    """Format risk report for display."""
    level = get_risk_level(risk.score)

    report = f"Risk Assessment: {level} ({risk.score:.1f}/1.0)\n"
    report += f"{risk.report}\n\n"

    if risk.checklist:
        report += "Checklist:\n"
        for item in risk.checklist:
            report += f"  {item}\n"

    return report
