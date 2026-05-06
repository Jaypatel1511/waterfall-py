# Contributing

Thank you for your interest in contributing! Here's how to get started.

## Getting Started

1. Fork the repository
2. Clone your fork locally
3. Install dependencies:

    pip install -e .
    pip install pytest

4. Run the tests to confirm everything works:

    PYTHONPATH=. pytest tests/ -v

## Making Changes

1. Create a new branch:

    git checkout -b fix/your-fix-name

2. Make your changes
3. Add or update tests to cover your changes
4. Run the full test suite — all tests must pass
5. Commit with a clear message:

    git commit -m "fix: description of what you fixed"

6. Push and open a Pull Request against main

## Pull Request Guidelines

- Keep PRs focused — one fix or feature per PR
- All tests must pass before merging
- Add tests for any new functionality
- Update the README if you add new features or change the API
- Use clear, descriptive commit messages

## Reporting Issues

Please open a GitHub Issue with:
- A clear description of the problem
- Steps to reproduce it
- Expected vs actual behavior
- Your Python version and OS

## Code Style

- Follow existing code style in the repo
- Use type hints where possible
- Add docstrings to public functions and classes
- Keep functions focused and single-purpose

## License

By contributing, you agree that your contributions will be licensed
under the MIT License.
