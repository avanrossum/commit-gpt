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

### Edit Cached Commit Messages

```bash
# Generate a commit message (cached automatically)
$ commit-gpt "add user authentication"
feat: add user authentication system

- implement login and logout functionality
- add JWT token handling
- include user session management

# Edit the cached message in your system editor
$ commit-gpt --amend
# [Opens your editor with the message above]

# Show the edited message (from cache)
$ commit-gpt
feat: add comprehensive user authentication system

- implement secure login and logout functionality
- add JWT token generation and validation
- include user session management with Redis
- add comprehensive error handling and logging

# Write the edited message to git
$ commit-gpt -w
# [Commits with your edited message]
```

### Complete Workflow Examples

#### **Feature Development Workflow**

```bash
# 1. Start working on a feature
git add src/auth.py src/models.py

# 2. Generate initial commit message
commit-gpt "implement user authentication"
feat: implement user authentication system

- add user model with secure password hashing
- implement login and registration endpoints
- add JWT token generation and validation

# 3. Realize you want to add more details
commit-gpt --amend
# [Edit in VS Code: add more context about security features]

# 4. Review the updated message
commit-gpt
feat: implement secure user authentication system

- add user model with bcrypt password hashing
- implement login and registration endpoints with rate limiting
- add JWT token generation and validation with refresh tokens
- include comprehensive input validation and error handling
- add audit logging for security events

# 5. Commit when satisfied
commit-gpt -w
```

#### **Bug Fix Workflow**

```bash
# 1. Fix a bug
git add src/bugfix.py

# 2. Generate fix message
commit-gpt "fix authentication bug"
fix: resolve token refresh race condition

- prevent multiple simultaneous token refresh requests
- add request deduplication using Redis locks
- improve error handling for concurrent requests

# 3. Add more technical details
commit-gpt --amend
# [Add specific details about the race condition]

# 4. Final review and commit
commit-gpt -w
```

#### **Large Change Workflow**

```bash
# 1. Make significant changes
git add .

# 2. Generate comprehensive message
commit-gpt "refactor entire authentication system"
feat: refactor authentication system for better security

- migrate from JWT to session-based authentication
- implement CSRF protection and rate limiting
- add comprehensive audit logging
- update all authentication endpoints
- include new security middleware

# 3. Split into smaller commits (if needed)
commit-gpt --suggest-groups
[INFO] Large diff detected (15,000 tokens). Suggested commit groups:

Group 1 (3,200 tokens):
  Files: src/auth/models.py, src/auth/schemas.py

Group 2 (4,100 tokens):
  Files: src/auth/endpoints.py, src/auth/middleware.py

Group 3 (2,800 tokens):
  Files: tests/auth/test_models.py, tests/auth/test_endpoints.py

# 4. Commit each group separately
git reset HEAD~  # Unstage all changes
git add src/auth/models.py src/auth/schemas.py
commit-gpt "add new auth models" -w

git add src/auth/endpoints.py src/auth/middleware.py
commit-gpt "implement auth endpoints" -w

git add tests/auth/
commit-gpt "add auth tests" -w
```

## How It Works

### Caching System

Commit-GPT uses intelligent caching to avoid repeated API calls:

- **Cache Location**: `~/.commit-gpt/cache.db` (SQLite)
- **Cache Key**: Hash of the entire prompt (diff + context + style)
- **Cache Hit**: Same staged changes → No API call, instant response
- **Cache Miss**: Different changes → New API call, cached for next time

### Typical Workflow

```bash
# First run - API call, cached
commit-gpt "add feature"
# [explain] $0.1491 :: Generated with AI
# feat: add new feature

# Same staged changes - CACHE HIT! No API call
commit-gpt "add feature"  
# [explain] $0.0000 :: Using cached response
# feat: add new feature

# Edit the cached message
commit-gpt --amend
# [Opens editor, edit message]

# Show edited message - Still cache hit!
commit-gpt
# feat: add comprehensive new feature with tests

# Write to git - Still cache hit!
commit-gpt -w
# [Commits with edited message]
```

### Editor Integration

The `--amend` feature opens your system editor:

- **VS Code**: `code --wait --new-window`
- **Vim**: `vim`
- **Nano**: `nano`
- **Custom**: Set `$EDITOR` environment variable

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
