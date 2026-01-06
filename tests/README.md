# Georgian Voiceover App - Tests

Comprehensive test suite for the Georgian Voiceover App using pytest.

## Test Structure

```
tests/
├── conftest.py              # Shared fixtures and configuration
├── unit/                    # Unit tests (fast, isolated)
│   ├── test_validators.py   # Input validation tests
│   ├── test_config.py       # Configuration tests
│   └── ...
├── integration/             # Integration tests (slower)
│   ├── test_api_endpoints.py  # API endpoint tests
│   └── ...
└── fixtures/                # Test data and fixtures
```

## Running Tests

### Install Testing Dependencies

```bash
pip install -r requirements-dev.txt
```

### Run All Tests

```bash
pytest
```

### Run Specific Test Categories

```bash
# Run only unit tests
pytest -m unit

# Run only integration tests
pytest -m integration

# Run only API tests
pytest -m api

# Run tests that don't require external services
pytest -m "not external_api"

# Skip slow tests
pytest -m "not slow"
```

### Run Specific Test Files

```bash
# Test validators only
pytest tests/unit/test_validators.py

# Test config only
pytest tests/unit/test_config.py

# Test API endpoints
pytest tests/integration/test_api_endpoints.py
```

### Run with Coverage Report

```bash
# Generate HTML coverage report
pytest --cov=src --cov=app --cov-report=html

# View coverage in browser
open htmlcov/index.html  # macOS
start htmlcov/index.html  # Windows
```

### Run Tests in Parallel

```bash
# Use all CPU cores
pytest -n auto

# Use specific number of workers
pytest -n 4
```

### Verbose Output

```bash
# Show detailed test output
pytest -v

# Show even more details
pytest -vv

# Show print statements
pytest -s
```

## Test Markers

Tests are organized using pytest markers:

- `@pytest.mark.unit` - Fast, isolated unit tests
- `@pytest.mark.integration` - Integration tests with multiple components
- `@pytest.mark.api` - API endpoint tests
- `@pytest.mark.database` - Tests requiring database
- `@pytest.mark.redis` - Tests requiring Redis
- `@pytest.mark.external_api` - Tests calling external APIs
- `@pytest.mark.slow` - Slow tests (skip with `-m "not slow"`)
- `@pytest.mark.smoke` - Critical smoke tests

## Code Coverage

Minimum coverage threshold: **80%**

View current coverage:
```bash
pytest --cov=src --cov-report=term-missing
```

## Writing New Tests

### Unit Test Example

```python
import pytest
from src.module import function_to_test

class TestMyFunction:
    @pytest.mark.unit
    def test_returns_correct_value(self):
        result = function_to_test(input_data)
        assert result == expected_value

    @pytest.mark.unit
    def test_raises_error_on_invalid_input(self):
        with pytest.raises(ValueError):
            function_to_test(invalid_data)
```

### Integration Test Example

```python
import pytest

class TestAPIEndpoint:
    @pytest.mark.integration
    @pytest.mark.api
    def test_endpoint_returns_200(self, client):
        response = client.get('/endpoint')
        assert response.status_code == 200

    @pytest.mark.integration
    @pytest.mark.database
    def test_creates_database_record(self, client, db_session):
        response = client.post('/create', json={'data': 'test'})
        assert response.status_code == 201
```

### Using Fixtures

```python
@pytest.mark.unit
def test_with_temp_file(temp_dir, temp_video_file):
    # temp_dir and temp_video_file are fixtures from conftest.py
    assert temp_video_file.exists()
    assert temp_video_file.parent == temp_dir
```

## Continuous Integration

Tests run automatically on:
- Every commit (via pre-commit hooks)
- Pull requests (via GitHub Actions)
- Before deployment (via CI/CD pipeline)

## Troubleshooting

### Tests Fail Due to Missing Dependencies

```bash
pip install -r requirements-dev.txt
```

### Database Tests Fail

Tests use in-memory SQLite. No external database needed.

### Redis Tests Fail

Mock Redis or skip with:
```bash
pytest -m "not redis"
```

### Import Errors

Ensure project root is in PYTHONPATH:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
pytest
```

## Best Practices

1. **Write tests first** (TDD) when adding new features
2. **Keep tests isolated** - each test should be independent
3. **Use fixtures** - reuse common setup code
4. **Mock external services** - don't call real APIs in tests
5. **Test edge cases** - not just happy paths
6. **Keep tests fast** - unit tests should run in milliseconds
7. **Clear test names** - describe what is being tested
8. **One assertion per test** (when possible) - easier debugging

## Test Coverage Goals

| Module | Target Coverage |
|--------|----------------|
| validators.py | 100% |
| config.py | 95% |
| database.py | 90% |
| API endpoints | 85% |
| Processing modules | 80% |

## Contributing

When adding new code:
1. Write tests covering the new functionality
2. Ensure all tests pass: `pytest`
3. Check coverage: `pytest --cov=src --cov-report=term-missing`
4. Aim for >80% coverage on new code

## Further Reading

- [pytest Documentation](https://docs.pytest.org/)
- [pytest-cov Documentation](https://pytest-cov.readthedocs.io/)
- [Testing Best Practices](https://docs.python-guide.org/writing/tests/)
