# SERP Execution Tests

Comprehensive test suite for the SERP execution module in Thesis Grey.

## Test Structure

The test suite is organized into the following modules:

### 1. **test_models.py**
Tests for all model classes and their methods:
- `SearchExecution` model lifecycle and status management
- `RawSearchResult` data storage and processing
- `ExecutionMetrics` aggregation and calculations
- Model relationships and cascade behaviors
- Field validations and constraints

### 2. **test_services.py**
Tests for service layer components:
- `SerperClient` - API integration and error handling
- `CacheManager` - Result caching and invalidation
- `UsageTracker` - Credit and usage monitoring
- `QueryBuilder` - Search query optimization
- `ResultProcessor` - Result normalization and storage

### 3. **test_views.py**
Tests for all view classes and AJAX endpoints:
- `ExecuteSearchView` - Search initiation workflow
- `SearchExecutionStatusView` - Real-time monitoring
- `ErrorRecoveryView` - Failure recovery interface
- AJAX API endpoints for status updates
- Permission and authentication checks

### 4. **test_tasks.py**
Tests for Celery asynchronous tasks:
- `initiate_search_session_execution_task`
- `perform_serp_query_task`
- `monitor_session_completion_task`
- `retry_failed_execution_task`
- Task retry logic and error handling

### 5. **test_forms.py**
Tests for Django forms:
- `ExecutionConfirmationForm` validation
- `ErrorRecoveryForm` logic
- Field validations and error messages

### 6. **test_integration.py**
End-to-end integration tests:
- Complete search workflow from initiation to completion
- Caching integration across components
- Error recovery workflows
- Concurrent execution scenarios
- Metrics aggregation

## Running Tests

### Run All Tests
```bash
python manage.py test apps.serp_execution
```

### Run Specific Test Module
```bash
# Model tests only
python manage.py test apps.serp_execution.tests.test_models

# Service tests only
python manage.py test apps.serp_execution.tests.test_services

# View tests only
python manage.py test apps.serp_execution.tests.test_views

# Task tests only
python manage.py test apps.serp_execution.tests.test_tasks

# Form tests only
python manage.py test apps.serp_execution.tests.test_forms

# Integration tests only
python manage.py test apps.serp_execution.tests.test_integration
```

### Run Specific Test Class
```bash
python manage.py test apps.serp_execution.tests.test_services.TestSerperClient
```

### Run Specific Test Method
```bash
python manage.py test apps.serp_execution.tests.test_models.SearchExecutionModelTests.test_can_retry_logic
```

### Using the Test Runner Script
```bash
cd apps/serp_execution/tests

# Run all tests
python run_tests.py

# Run specific test type
python run_tests.py models
python run_tests.py services
python run_tests.py views
python run_tests.py tasks
python run_tests.py integration
python run_tests.py forms

# Run with coverage
python run_tests.py coverage

# Run with options
python run_tests.py all --verbosity=3 --failfast
```

## Test Coverage

The test suite aims for >90% code coverage. To generate a coverage report:

```bash
# Using coverage.py
coverage run --source='apps/serp_execution' manage.py test apps.serp_execution
coverage report
coverage html  # Generates htmlcov/index.html

# Using the test runner script
python apps/serp_execution/tests/run_tests.py coverage
```

## Test Data and Fixtures

Tests use Django's TestCase classes which provide:
- Automatic database transaction rollback
- Test isolation
- Factory methods for creating test data

Common test data patterns:
```python
# User creation
user = User.objects.create_user(
    email='test@example.com',
    password='testpass123'
)

# Session with queries
session = SearchSession.objects.create(
    title='Test Session',
    owner=user,
    status='ready_to_execute'
)

query = SearchQuery.objects.create(
    session=session,
    population='developers',
    interest='testing',
    context='python',
    search_engines=['google']
)
```

## Mocking External Services

External API calls are mocked to ensure:
- Tests run without internet connection
- Predictable test results
- No API credit consumption
- Fast test execution

Example mock pattern:
```python
@patch('apps.serp_execution.services.serper_client.requests.Session.post')
def test_search_execution(self, mock_post):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {'organic': [...]}
    mock_post.return_value = mock_response
```

## Testing Best Practices

1. **Test Isolation**: Each test should be independent
2. **Clear Test Names**: Use descriptive test method names
3. **Arrange-Act-Assert**: Follow AAA pattern in tests
4. **Mock External Dependencies**: Don't make real API calls
5. **Test Edge Cases**: Include error scenarios and boundary conditions
6. **Use Factories**: Create reusable test data factories
7. **Transaction Tests**: Use TransactionTestCase for tests requiring transactions

## Common Test Scenarios

### Testing API Integration
- Successful API calls
- Rate limiting
- Authentication errors
- Network failures
- Retry logic

### Testing Async Tasks
- Task execution
- Retry on failure
- Task chaining
- Progress monitoring

### Testing User Workflows
- Search initiation
- Error recovery
- Result viewing
- Permission checks

### Testing Data Processing
- Result normalization
- Duplicate detection
- Metadata extraction
- Batch processing

## Debugging Failed Tests

1. **Increase Verbosity**: `python manage.py test --verbosity=3`
2. **Run Single Test**: Isolate the failing test
3. **Check Test Database**: Use `--keepdb` to inspect test data
4. **Add Debug Prints**: Use `print()` or `pdb` for debugging
5. **Check Mocks**: Ensure mocks match actual implementation

## Contributing

When adding new features:
1. Write tests first (TDD approach)
2. Ensure all tests pass
3. Maintain >90% coverage
4. Update this README if adding new test patterns