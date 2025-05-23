# Contributing to Friday Voice RAG

Thank you for considering contributing to this project! We welcome contributions from everyone.

## Getting Started

1. Fork the repository
2. Clone your fork: `git clone https://github.com/shibyan-ai-engineer/voice-rag.git`
3. Set up your development environment as described in the README.md
4. Create a new branch: `git checkout -b feature/your-feature-name`

## Development Guidelines

### Code Style

- Follow PEP 8 guidelines for Python code
- Use meaningful variable and function names
- Include docstrings for all functions and classes
- Keep functions focused on a single task

### Commit Messages

- Use clear and descriptive commit messages
- Start with a short summary (50 chars or less)
- Use the imperative mood ("Add feature" not "Added feature")

### Pull Requests

1. Make sure your code passes all tests
2. Update the README.md if necessary
3. Create a pull request with a descriptive title
4. Link any relevant issues

## Project Structure

- `/app`: Contains the FastAPI application code
  - `/api`: API endpoints
  - `/core`: Configuration and core functionality
  - `/services`: Business logic for various components
- `/static`: Frontend files
- `/data`: Directory for data storage

## Testing

Before submitting a pull request:

1. Run `python verify.py` to ensure your changes don't break existing functionality
2. Test the application manually to ensure end-to-end functionality works
3. Add appropriate tests for new features

## License

By contributing to this project, you agree that your contributions will be licensed under the project's MIT License.
