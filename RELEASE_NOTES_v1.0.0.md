# Initial Release - v1.0.0

**Commit-GPT** is an AI-powered git commit message generator that transforms your staged changes into meaningful, professional commit messages using OpenAI GPT or Anthropic Claude.

## Key Features

- **AI-Powered Generation**: Uses GPT-4 series models to create intelligent, context-aware commit messages
- **Security First**: Automatically redacts secrets, API keys, and sensitive data before sending to AI services
- **Smart Caching**: Local SQLite cache prevents repeated API calls for identical changes
- **Risk Assessment**: Detects potential issues like secrets, destructive changes, and breaking changes
- **Flexible Styling**: Supports both conventional commits and casual styles
- **Cost Control**: Built-in cost limits and token estimation to manage API usage
- **Offline Fallback**: Heuristic-based generation when no API key is available
- **Smart Orchestration**: Suggests how to split large diffs into multiple focused commits

## Getting Started

```bash
# Install
pip install smart-commit-gpt

# Setup API key
cp .env.example .env
# Edit .env with your OPENAI_API_KEY

# Use
git add .
commit-gpt
```

## Advanced Features

- **Model Configuration**: Support for `gpt-4o`, `gpt-4o-mini`, `gpt-4.1`, and `gpt-4.1-mini`
- **Commit Message Editing**: Use `--amend` to edit cached messages in your preferred editor
- **PR Summaries**: Generate pull request titles and summaries with `--pr`
- **Risk Analysis**: Get detailed risk assessments with `--risk-check`
- **Large Diff Handling**: Automatic suggestions for splitting large changes into focused commits

## Development

- Comprehensive test suite with pytest
- Code quality checks with black, isort, and ruff
- Security scanning with bandit and safety
- Automated CI/CD pipeline

## Documentation

Extensive documentation including:
- Quick start guide
- Usage examples and workflows
- Security considerations
- Advanced configuration options
- Development setup instructions

---

**Ready to revolutionize your commit workflow?** Install Commit-GPT today and experience AI-powered commit message generation that's both intelligent and secure.
