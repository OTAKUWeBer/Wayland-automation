# Contributing to Wayland Automation

Thank you for considering contributing to Wayland Automation! We welcome all contributions that improve the library.

## Getting Started

1. Fork the repository.
2. Clone your fork locally.
3. Install development dependencies:
   ```bash
   pip install -e .
   ```

## Development Standards

- **Code Style**: We follow [PEP 8](https://peps.python.org/pep-0008/).
- **Documentation**: All new features should include docstrings and be updated in the README if necessary.
- **Error Handling**: Use the existing reconnection patterns for socket-based controllers.

## Pull Request Process

1. Create a new branch for your feature or bugfix.
2. Ensure your code doesn't break existing functionality.
3. Submit a PR with a clear description of the changes and the problem they solve.

## Reporting Issues

Use the GitHub issue tracker to report bugs. Please include:
- Your compositor (e.g., Hyprland, Sway).
- Steps to reproduce the issue.
- Any relevant error logs (especially `BrokenPipeError`).
