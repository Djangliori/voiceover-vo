# Contributing to Georgian Voiceover App

მადლობა, რომ გსურთ პროექტში წვლილის შეტანა! 🎉

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [Making Changes](#making-changes)
- [Testing](#testing)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Commit Messages](#commit-messages)

---

## Code of Conduct

ეს პროექტი და მისი ყველა მონაწილე იცავს პატივისცემის, ინკლუზიურობისა და პროფესიონალიზმის პრინციპებს.

### Our Standards

- ✅ Be respectful and inclusive
- ✅ Welcome newcomers and help them learn
- ✅ Give and receive constructive feedback
- ✅ Focus on what's best for the project
- ❌ No harassment, trolling, or personal attacks
- ❌ No spam or off-topic content

---

## Getting Started

### Prerequisites

- Python 3.9 or higher
- Git
- ffmpeg
- GitHub account

### Fork and Clone

```bash
# Fork the repository on GitHub
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/georgian-voiceover-app.git
cd georgian-voiceover-app

# Add upstream remote
git remote add upstream https://github.com/speudoname/georgian-voiceover-app.git
```

---

## Development Setup

### 1. Create Virtual Environment

```bash
python -m venv venv

# Activate (Linux/Mac)
source venv/bin/activate

# Activate (Windows)
.\venv\Scripts\activate
```

### 2. Install Dependencies

```bash
# Production dependencies
pip install -r requirements.txt

# Development dependencies (includes testing, linting, etc.)
pip install -r requirements-dev.txt
```

### 3. Setup Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your API keys
# VOICEGAIN_API_KEY=your_key_here
# OPENAI_API_KEY=your_key_here
# etc.
```

### 4. Verify Setup

```bash
# Run tests to verify everything works
make test

# Or manually
pytest
```

---

## Making Changes

### 1. Create a Branch

Use conventional branch names:

```bash
# Features
git checkout -b feat/add-user-authentication
git checkout -b feat/improve-video-quality

# Bug fixes
git checkout -b fix/resolve-encoding-error
git checkout -b fix/memory-leak-in-processing

# Documentation
git checkout -b docs/update-installation-guide

# Refactoring
git checkout -b refactor/improve-code-structure
```

### 2. Make Your Changes

- Write clean, readable code
- Follow the [coding standards](#coding-standards)
- Add tests for new features
- Update documentation if needed

### 3. Test Your Changes

```bash
# Run all tests
make test

# Run specific test types
make test-unit         # Fast unit tests
make test-integration  # Integration tests
make test-cov          # With coverage report

# Run linting
make lint

# Format code
make format
```

### 4. Commit Your Changes

Follow [conventional commits](#commit-messages):

```bash
git add .
git commit -m "feat: Add user authentication system"
```

---

## Testing

### Writing Tests

**All new features MUST include tests!**

#### Unit Test Example

```python
# tests/unit/test_my_feature.py
import pytest
from src.my_module import my_function

class TestMyFeature:
    @pytest.mark.unit
    def test_returns_expected_value(self):
        """Test that function returns correct value"""
        result = my_function(input_data)
        assert result == expected_value

    @pytest.mark.unit
    def test_raises_error_on_invalid_input(self):
        """Test that function raises error for invalid input"""
        with pytest.raises(ValueError):
            my_function(invalid_data)
```

#### Integration Test Example

```python
# tests/integration/test_my_endpoint.py
import pytest

class TestMyEndpoint:
    @pytest.mark.integration
    @pytest.mark.api
    def test_endpoint_returns_200(self, client):
        """Test that endpoint returns 200 OK"""
        response = client.get('/my-endpoint')
        assert response.status_code == 200
```

### Test Requirements

- ✅ All new features need tests
- ✅ Bug fixes should include regression tests
- ✅ Aim for >80% code coverage
- ✅ Tests should be fast (unit tests < 100ms)
- ✅ Use fixtures for shared test data
- ✅ Mock external services (APIs, databases)

### Running Tests

```bash
# All tests
pytest

# Specific file
pytest tests/unit/test_validators.py

# Specific test
pytest tests/unit/test_validators.py::TestValidateYouTubeURL::test_standard_youtube_url

# With coverage
pytest --cov=src --cov-report=html

# Watch mode (re-run on file change)
pytest-watch
```

---

## Pull Request Process

### 1. Before Creating PR

**Checklist:**
- [ ] Code follows [coding standards](#coding-standards)
- [ ] All tests pass: `make test`
- [ ] Code is formatted: `make format`
- [ ] Linting passes: `make lint`
- [ ] Coverage maintained/improved: `make test-cov`
- [ ] Documentation updated if needed
- [ ] Commits follow [conventional commits](#commit-messages)

### 2. Create Pull Request

```bash
# Push your branch
git push origin feat/my-feature

# Go to GitHub and create PR
# Use the PR template
```

### 3. PR Title Format

Follow **Conventional Commits**:

```
feat: Add user authentication system
fix: Resolve video encoding timeout issue
docs: Update API documentation
test: Add unit tests for validators
refactor: Improve code structure in processor
perf: Optimize video encoding performance
ci: Update GitHub Actions workflow
```

### 4. PR Description Template

```markdown
## Description
Brief description of changes

## Type of Change
- [ ] Bug fix
- [ ] New feature
- [ ] Breaking change
- [ ] Documentation update

## How Has This Been Tested?
- [ ] Unit tests
- [ ] Integration tests
- [ ] Manual testing

## Checklist
- [ ] Tests pass locally
- [ ] Code follows style guidelines
- [ ] Documentation updated
- [ ] No new warnings
```

### 5. PR Review Process

1. **Automated Checks** will run:
   - CI tests
   - Linting
   - Security scans
   - Coverage comparison

2. **Code Review** by maintainers:
   - Code quality
   - Test coverage
   - Documentation
   - Performance impact

3. **Address Feedback**:
   - Make requested changes
   - Push new commits
   - Re-request review

4. **Merge**:
   - Maintainer will merge when approved
   - PR branch will be deleted

---

## Coding Standards

### Python Style

We follow **PEP 8** with some modifications:

```python
# Good: Clear, descriptive names
def process_video_with_georgian_voiceover(video_id: str) -> dict:
    """
    Process video and add Georgian voiceover.

    Args:
        video_id: YouTube video ID

    Returns:
        dict: Processing result with status and URL
    """
    pass

# Bad: Unclear names, no types, no docstring
def pv(v):
    pass
```

### Code Formatting

- **Line length**: 120 characters max
- **Indentation**: 4 spaces (no tabs)
- **Imports**: Sorted with isort
- **Strings**: Double quotes for strings, single for dict keys

### Auto-formatting

```bash
# Format all code
make format

# This runs:
# - black (code formatter)
# - isort (import sorter)
```

### Type Hints

Use type hints for function signatures:

```python
from typing import List, Optional, Dict

def translate_text(text: str, target_lang: str = 'ka') -> str:
    """Translate text to target language"""
    pass

def get_video_info(video_id: str) -> Optional[Dict[str, any]]:
    """Get video information"""
    pass
```

### Docstrings

Use Google-style docstrings:

```python
def process_video(video_id: str, quality: str = 'high') -> dict:
    """
    Process video with Georgian voiceover.

    Args:
        video_id: YouTube video ID (11 characters)
        quality: Video quality ('low', 'medium', 'high')

    Returns:
        dict: Processing result containing:
            - status: 'completed' or 'failed'
            - url: URL to processed video
            - duration: Processing duration in seconds

    Raises:
        ValidationError: If video_id is invalid
        ProcessingError: If video processing fails

    Example:
        >>> result = process_video('dQw4w9WgXcQ', quality='high')
        >>> print(result['status'])
        'completed'
    """
    pass
```

---

## Commit Messages

### Conventional Commits Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `perf`: Performance improvements
- `test`: Adding or updating tests
- `build`: Build system changes
- `ci`: CI/CD changes
- `chore`: Other changes (dependencies, etc.)

### Examples

```bash
# Simple feature
git commit -m "feat: Add user authentication"

# With scope
git commit -m "feat(api): Add video upload endpoint"

# With body
git commit -m "fix: Resolve video encoding timeout

Video encoding was timing out for videos longer than 30 minutes.
Increased timeout from 10 to 60 minutes and added progress tracking."

# Breaking change
git commit -m "feat!: Change API response format

BREAKING CHANGE: API now returns {data: {}, error: null} format
instead of direct response. Update clients accordingly."
```

### Commit Message Rules

- ✅ Use imperative mood ("Add feature" not "Added feature")
- ✅ Start with lowercase (except proper nouns)
- ✅ No period at the end of subject
- ✅ Keep subject under 72 characters
- ✅ Separate subject and body with blank line
- ✅ Wrap body at 72 characters

---

## Areas for Contribution

### 🐛 Bug Fixes

Check [Issues](https://github.com/speudoname/georgian-voiceover-app/issues) labeled `bug`

### ✨ New Features

Check [Issues](https://github.com/speudoname/georgian-voiceover-app/issues) labeled `enhancement`

### 📚 Documentation

- Improve existing documentation
- Add code examples
- Fix typos
- Translate docs to Georgian

### 🧪 Testing

- Increase test coverage
- Add integration tests
- Improve test quality

### 🎨 UI/UX

- Improve web interface
- Add new themes
- Enhance user experience

### ⚡ Performance

- Optimize video processing
- Reduce memory usage
- Improve response times

---

## Questions?

- 💬 **Discussions**: [GitHub Discussions](https://github.com/speudoname/georgian-voiceover-app/discussions)
- 🐛 **Bug Reports**: [GitHub Issues](https://github.com/speudoname/georgian-voiceover-app/issues)
- 📧 **Email**: Contact maintainers

---

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

**მადლობა თქვენი წვლილისთვის! 🙏**

ყველა contribution აფასებულია, დიდიდან პატარამდე!
