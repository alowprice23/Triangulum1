# Contributing to Triangulum LX

Thank you for considering contributing to Triangulum LX! This document outlines the process for contributing to the project.

## Code of Conduct

By participating in this project, you agree to abide by our code of conduct:

* Be respectful and inclusive
* Value different viewpoints and experiences
* Accept constructive criticism gracefully
* Focus on what is best for the community
* Show empathy towards community members

## How to Contribute

### Reporting Bugs

1. Check if the bug has already been reported in the [Issues](https://github.com/triangulum/triangulum-lx/issues)
2. If not, create a new issue using the bug report template
3. Include detailed steps to reproduce the bug
4. Include system information and relevant logs

### Suggesting Enhancements

1. Check if the enhancement has already been suggested in the [Issues](https://github.com/triangulum/triangulum-lx/issues)
2. If not, create a new issue using the feature request template
3. Describe the enhancement in detail and explain its benefits

### Pull Requests

1. Fork the repository
2. Create a new branch for your feature or bugfix
3. Make your changes
4. Add or update tests as necessary
5. Update documentation if relevant
6. Ensure all tests pass
7. Submit a pull request

## Development Setup

To set up the development environment:

```bash
# Clone your fork
git clone https://github.com/YOUR_USERNAME/triangulum-lx.git
cd triangulum-lx

# Create a virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e ".[dev]"
```

## Testing

Run the test suite with:

```bash
pytest
```

## Coding Standards

* Follow PEP 8 style guidelines
* Write docstrings for all functions, classes, and modules
* Add type hints where appropriate
* Keep functions small and focused
* Write tests for new functionality

## Git Workflow

1. Create a branch for your work
   ```bash
   git checkout -b feature/your-feature
   ```

2. Make commits with clear messages
   ```bash
   git commit -m "Add feature X that does Y"
   ```

3. Push your branch to your fork
   ```bash
   git push origin feature/your-feature
   ```

4. Create a pull request to the main repository

## License

By contributing to Triangulum LX, you agree that your contributions will be licensed under the project's MIT license.
