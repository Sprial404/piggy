# Contributing to Piggy

Thank you for your interest in contributing to Piggy! This document provides guidelines and instructions for contributing to the project.

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [How to Contribute](#how-to-contribute)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Submitting Changes](#submitting-changes)
- [Reporting Bugs](#reporting-bugs)
- [Suggesting Features](#suggesting-features)

## Code of Conduct

This project adheres to a Code of Conduct that all contributors are expected to follow. Please read [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) before contributing.

## Getting Started

### Prerequisites

- Python 3.13 or higher
- Git
- pip (Python package installer)

### Development Setup

1. **Fork and clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/piggy.git
   cd piggy
   ```

2. **Create a virtual environment:**
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate  # On Windows: .venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   pip install -r requirements-dev.txt
   ```

4. **Install pre-commit hooks:**
   ```bash
   pre-commit install
   ```

5. **Verify setup:**
   ```bash
   # Run tests
   python -m unittest tests/test_serialization.py

   # Run the application
   python -m piggy.interactive
   ```

## How to Contribute

### Types of Contributions

We welcome various types of contributions:

- **Bug fixes** - Fix issues in the codebase
- **New features** - Implement new functionality
- **Documentation** - Improve or add documentation
- **Tests** - Add or improve test coverage
- **Refactoring** - Improve code quality or performance
- **Bug reports** - Report issues with detailed information
- **Feature requests** - Suggest new features or improvements

### Finding Something to Work On

- Check the [Issues](https://github.com/Sprial404/piggy/issues) page for open issues
- Look for issues labeled `good first issue` for beginner-friendly tasks
- Suggest your own improvements

## Development Workflow

### 1. Create a Branch

Create a feature branch for your work:

```bash
git checkout -b feature/your-feature-name
# or
git checkout -b fix/issue-description
```

### 2. Make Changes

- Write clean, well-documented code
- Follow the [coding standards](#coding-standards)
- Add tests for new functionality
- Update documentation as needed

### 3. Run Quality Checks

Before committing, ensure your code passes all checks:

```bash
# Format code
black piggy/ tests/

# Lint code
ruff check --fix piggy/ tests/

# Run tests
python -m unittest tests/test_serialization.py
```

### 4. Commit Changes

Write clear, descriptive commit messages:

```bash
git add .
git commit -m "Add brief description of changes

More detailed explanation if needed. Explain why the change
was made and what problem it solves."
```

### 5. Push and Create Pull Request

```bash
git push origin feature/your-feature-name
```

Then create a pull request on GitHub with:
- Clear description of changes
- Reference to related issues
- Any special testing instructions

## Coding Standards

### Style Guide

Please read and follow [STYLE_GUIDE.md](STYLE_GUIDE.md) for detailed code style guidelines.

### Key Points

- **Type hints:** Always use type annotations with modern Python 3.13+ syntax
- **Line length:** Maximum 120 characters (enforced by Black)
- **Docstrings:** Use `:param` and `:return` tags for all public functions
- **Comments:** Only add comments for complex or non-obvious logic
- **Naming:** Use `snake_case` for functions/variables, `PascalCase` for classes

### Code Quality Tools

- **Black** - Code formatter (automatic)
- **Ruff** - Fast linter (catches common issues)
- **Pre-commit** - Runs checks before each commit

Run formatting and linting:

```bash
# Format
black piggy/ tests/

# Lint with auto-fix
ruff check --fix piggy/ tests/

# Check without fixing
ruff check piggy/ tests/
```

## Testing

### Running Tests

```bash
# Run all tests
python -m unittest tests/test_serialization.py

# Run specific test
python -m unittest tests.test_serialization.TestInstallmentPlanSerialization.test_json_serialization_to_string
```

### Writing Tests

- Add tests for new features in appropriate test files
- Test both success and failure cases
- Use descriptive test names: `test_<what>_<condition>_<expected_result>`
- Include docstrings explaining what the test validates

Example:

```python
def test_remaining_balance_after_payment(self):
    """Test remaining_balance updates correctly after marking payment as paid."""
    plan = create_test_plan()
    plan.mark_installment_paid(1, date.today())

    expected = Decimal("750.00")
    self.assertEqual(plan.remaining_balance, expected)
```

## Submitting Changes

### Pull Request Process

1. **Update documentation** - Update README.md, docstrings, or other docs as needed
2. **Update tests** - Ensure all tests pass and add new ones for your changes
4. **Run all checks** - Format, lint, and test your code
5. **Create PR** - Submit pull request with clear description
6. **Respond to feedback** - Address any review comments

### Pull Request Guidelines

- **One feature per PR** - Keep pull requests focused on a single change
- **Clear title** - Use descriptive titles like "Add partial payment support" or "Fix overflow in installment display"
- **Description** - Explain what changed and why
- **Link issues** - Reference related issues with `Fixes #123` or `Relates to #456`
- **Tests pass** - Ensure all tests pass before submitting
- **Clean commits** - Squash or rebase commits if necessary

## Reporting Bugs

### Before Submitting a Bug Report

- Check if the bug has already been reported in [Issues](https://github.com/Sprial404/piggy/issues)
- Try to reproduce the bug with the latest version
- Gather relevant information about your environment

### How to Submit a Bug Report

Create an issue with the following information:

**Title:** Clear, concise description of the problem

**Description:**
- **Expected behavior** - What you expected to happen
- **Actual behavior** - What actually happened
- **Steps to reproduce** - Detailed steps to recreate the issue
- **Environment:**
  - Python version: `python --version`
  - Operating system
  - Piggy version/commit
- **Error messages** - Include full error messages and stack traces
- **Screenshots** - If applicable

**Example:**

```
Title: Application crashes when marking payment with invalid date

Description:
Expected: Error message displayed when entering invalid date
Actual: Application crashes with traceback

Steps to reproduce:
1. Run `python -m piggy.interactive`
2. Select "Mark Payment"
3. Choose a plan
4. Select an installment
5. Enter invalid date "not-a-date"

Environment:
- Python 3.13.0
- macOS 14.5
- Commit: abc123

Error:
[paste full error message]
```

## Suggesting Features

### Before Suggesting a Feature

- Check [Issues](https://github.com/Sprial404/piggy/issues) to see if it's been suggested
- Consider if it fits the project's goals and scope

### How to Suggest a Feature

Create an issue with the following information:

**Title:** Clear feature description

**Description:**
- **Problem statement** - What problem does this solve?
- **Proposed solution** - How should it work?
- **Alternatives** - Other approaches you've considered
- **Use cases** - Real-world scenarios where this would be useful
- **Additional context** - Mockups, examples, or references

## Questions?

If you have questions about contributing, feel free to:
- Open a [Discussion](https://github.com/Sprial404/piggy/discussions) on GitHub
- Check existing documentation
- Reach out to maintainers

## Recognition

All contributors will be recognized in [CONTRIBUTORS.md](CONTRIBUTORS.md). Thank you for helping make Piggy better!
