# Commit-GPT

[![PyPI](https://img.shields.io/pypi/v/commit-gpt)](https://pypi.org/project/commit-gpt/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

AI-powered git commit message generator that turns your staged changes into meaningful commit messages.

⚠️ **Security Notice**: This tool sends git diffs to external AI services. Use `--no-llm` for sensitive code or review [Privacy & Security](#privacy--security) section.

## Features

- 🤖 **AI-Powered**: Uses OpenAI GPT or Anthropic Claude to generate intelligent commit messages
- 🔒 **Secure**: Automatically redacts secrets and sensitive data before sending to AI
- ⚡ **Fast**: Caches responses locally to avoid repeated API calls
- 🛡️ **Risk Assessment**: Detects potential issues like secrets, destructive changes, and breaking changes
- 📝 **Flexible**: Supports both conventional commits and casual styles
- 💰 **Cost Control**: Built-in cost limits and token estimation
- 🔄 **Offline Fallback**: Heuristic-based generation when no API key is available
- 🎯 **Smart Orchestration**: Suggests how to split large diffs into multiple focused commits

## Quick Start

### Installation

```bash
pip install commit-gpt
```

### Setup

Set your API key using a `.env` file (recommended for security):

```bash
# Copy the example file and edit it
cp .env.example .env

# Edit .env with your actual API key
# OPENAI_API_KEY=your-actual-openai-api-key
```

**That's it!** Commit-GPT will automatically load the `.env` file when you run it. No need to manually source the file or set environment variables.

**Note**: The `.env` file is already in `.gitignore` to prevent accidental commits of your API key.

### Model Configuration

Commit-GPT supports various GPT-4 series models. Configure via environment variable:

```bash
# In your .env file
COMMIT_GPT_OPENAI_MODEL=gpt-4o  # Default - best balance of quality and cost
COMMIT_GPT_OPENAI_MODEL=gpt-4o-mini  # Fastest and cheapest
COMMIT_GPT_OPENAI_MODEL=gpt-4.1  # Latest model with large context
COMMIT_GPT_OPENAI_MODEL=gpt-4.1-mini  # Good balance for smaller diffs
```

⚠️ **Model Compatibility**: Using models other than GPT-4 series may result in unexpected behavior due to token limits and context window differences. Recommended models: `gpt-4o`, `gpt-4o-mini`, `gpt-4.1`, `gpt-4.1-mini`.

### Basic Usage

```bash
# Stage your changes
git add .

# Generate commit message
commit-gpt

# Write commit directly
commit-gpt --write
```

## Examples

### Conventional Commits (default)

```bash
$ commit-gpt
feat(auth): add refresh token rotation and revoke on logout

- introduce refresh token rotation in oauth2.py
- add revoke endpoint; update session store
- adjust tests for new token expiry behavior
```

### Casual Style

```bash
$ commit-gpt --style casual
Fix flaky cache warmup and improve error handling

- add retry logic for cache initialization
- improve error messages for debugging
- update tests to handle edge cases
```

### With Explanation

```bash
$ commit-gpt --explain
feat(api): add user authentication endpoints

- implement login and logout routes
- add JWT token generation and validation
- include comprehensive test coverage

[explain] $0.0023 :: Generated conventional commit for new authentication feature with proper scope and descriptive body
```

### Risk Assessment

```bash
$ commit-gpt --risk-check
Risk Score: 0.4/1.0 - Found 2 potential secrets; Touches production files: env/prod/

Checklist:
  🔒 Review for exposed secrets
  🚨 Review production changes
```

## Advanced Usage

### Generate PR Summary

```bash
$ commit-gpt --pr
feat(dashboard): add real-time metrics and alerting

- implement WebSocket connection for live updates
- add alert configuration UI
- integrate with monitoring services

PR_TITLE: Add Real-time Dashboard with Alerting System
PR_SUMMARY:
- Live metrics display with WebSocket updates
- Configurable alert thresholds and notifications
- Integration with existing monitoring infrastructure
```

### Analyze Specific Range

```bash
$ commit-gpt --range HEAD~3..HEAD
refactor(core): consolidate database connection handling

- extract connection pool logic into separate module
- add connection retry and timeout configuration
- update all database access to use new interface
```

### Offline Mode

```bash
$ commit-gpt --no-llm
feat(auth): add user authentication module

- modify 3 file(s)
- add 45 line(s)
- remove 12 line(s)
```

### Cost Control

```bash
$ commit-gpt --max-$ 0.01
# Will fail if estimated cost exceeds $0.01
```

### Large Diff Orchestration

```bash
$ commit-gpt --suggest-groups
# Suggests how to split large changes into multiple focused commits
```

### Large Diff Orchestration

For large changes, commit-gpt can suggest how to split them into multiple focused commits:

```bash
$ commit-gpt --suggest-groups
📋 Large diff detected (52837 chars). Suggested commit groups:

Group 1 (662 chars):
  Files: .env.example
  Suggested: chore: Add .env.example with API key placeholders

Group 2 (3259 chars):
  Files: ci.yml
  Suggested: feat: add CI workflow for testing and coverage

💡 To commit each group separately:
  1. git reset HEAD~  # Unstage all changes
  2. Stage files for each group: git add <files>
  3. Run commit-gpt for each group
```

This creates a cleaner commit history with atomic, focused commits instead of one massive change.

## Configuration

### Environment Variables

- `OPENAI_API_KEY`: Your OpenAI API key
- `ANTHROPIC_API_KEY`: Your Anthropic API key
- `COMMIT_GPT_CACHE_DIR`: Custom cache directory (default: `~/.commit-gpt/`)

### Git Hooks

#### Prepare Commit Message Hook

```bash
# .git/hooks/prepare-commit-msg
#!/bin/sh
commit-gpt > "$1"
```

#### Commit Message Validation

```bash
# .git/hooks/commit-msg
#!/bin/sh
commit-gpt --validate < "$1" || exit 1
```

## Risk Assessment

Commit-GPT automatically detects potential issues:

- 🔒 **Secrets**: API keys, passwords, private keys
- ⚠️ **Destructive Changes**: DROP statements, file deletions
- 🚨 **Production Touches**: Changes to prod configs
- 💥 **Breaking Changes**: API version bumps, breaking change indicators
- 🗑️ **Large Deletions**: Bulk file or code removals
- 🧪 **Test Removals**: Deletion of test files
- 🗄️ **Migrations**: Database schema changes

## Privacy & Security

⚠️ **Important Security Notice**: This tool sends your git diffs to external AI services (OpenAI/Anthropic). While we implement redaction to remove common secrets, you should:

- **Review your diffs** before using this tool
- **Never use on highly sensitive code** without thorough review
- **Consider using `--no-llm` mode** for sensitive repositories
- **Understand that redaction is not perfect** - some sensitive data might still be sent

### Security Features

- **Local Processing**: Diffs are processed locally before sending to AI
- **Automatic Redaction**: Secrets and sensitive data are automatically redacted
- **Local Cache**: Responses are cached locally in SQLite
- **No Data Retention**: No data is stored on external servers beyond the API call
- **Offline Mode**: Use `--no-llm` for heuristic-based generation without AI

### Redaction Patterns

The tool automatically redacts:
- AWS access keys and secrets
- API keys and tokens
- JWT tokens
- Private keys (RSA, SSH, etc.)
- Database connection strings
- OAuth tokens
- Environment files (.env, etc.)

## Development

### Installation

```bash
git clone https://github.com/your-org/commit-gpt.git
cd commit-gpt
pip install -e .
```

### Running Tests

```bash
pytest tests/
```

### Code Quality

```bash
black src/
isort src/
mypy src/
ruff check src/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see [LICENSE](LICENSE) for details.

## Support

- 📖 [Documentation](https://github.com/your-org/commit-gpt/wiki)
- 🐛 [Issues](https://github.com/your-org/commit-gpt/issues)
- 💬 [Discussions](https://github.com/your-org/commit-gpt/discussions)

---

**Note**: This tool is designed to assist with commit message generation. Always review generated messages before committing, especially for important changes.
