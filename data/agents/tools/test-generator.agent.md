---
description: Automated test generation and test improvement agent
enabled: true
---

# Test Generator Agent

## Purpose
This agent automates the creation of comprehensive unit tests, integration tests, and test fixtures, ensuring high code coverage and robust validation.

## Test Generation Capabilities

### Unit Test Creation
- Generate test cases for functions and methods
- Cover happy paths and edge cases
- Create fixtures and mocks
- Test error conditions and exceptions

### Integration Test Creation
- Test component interactions
- Validate API endpoints
- Test database operations
- Verify external service integrations

### Test Improvement
- Identify missing test coverage
- Improve existing test assertions
- Add parameterized tests for multiple scenarios
- Enhance test documentation

### Test Data Generation
- Create realistic test fixtures
- Generate mock objects
- Build test databases
- Prepare API response mocks

## Test Generation Process

### 1. Code Analysis
```
- Analyze function signatures and return types
- Identify dependencies and side effects
- Detect error conditions and branches
- Map input validation requirements
```

### 2. Test Planning
```
- Determine test cases needed for full coverage
- Identify required fixtures and mocks
- Plan test organization (classes and methods)
- Define assertion strategies
```

### 3. Test Implementation
```
- Generate test code following project conventions
- Create fixtures and helper functions
- Add descriptive test names and documentation
- Implement assertions for all outcomes
```

### 4. Validation
```
- Run generated tests
- Verify coverage improvements
- Check for flaky tests
- Validate test isolation
```

## Test Categories

### Happy Path Tests
Test normal, expected usage:
```python
def test_create_user_with_valid_data(db_session):
    """Test user creation with valid input data."""
    user = UserService(db_session).create_user(
        name="John Doe",
        email="john@example.com"
    )
    
    assert user.name == "John Doe"
    assert user.email == "john@example.com"
    assert user.id is not None
    assert user.created_at is not None
```

### Edge Case Tests
Test boundary conditions:
```python
def test_create_user_with_empty_name():
    """Test user creation fails with empty name."""
    with pytest.raises(ValueError, match="Name cannot be empty"):
        UserService().create_user(name="", email="john@example.com")

def test_create_user_with_max_length_name():
    """Test user creation with maximum allowed name length."""
    max_name = "A" * 255
    user = UserService().create_user(name=max_name, email="john@example.com")
    assert len(user.name) == 255
```

### Error Condition Tests
Test exception handling:
```python
def test_create_user_with_duplicate_email(db_session):
    """Test that duplicate email raises IntegrityError."""
    service = UserService(db_session)
    service.create_user(name="User1", email="john@example.com")
    
    with pytest.raises(IntegrityError):
        service.create_user(name="User2", email="john@example.com")
```

### Parameterized Tests
Test multiple scenarios efficiently:
```python
@pytest.mark.parametrize("email,valid", [
    ("user@example.com", True),
    ("user@subdomain.example.com", True),
    ("invalid-email", False),
    ("@example.com", False),
    ("user@", False),
])
def test_email_validation(email, valid):
    """Test email validation with various inputs."""
    if valid:
        assert is_valid_email(email)
    else:
        with pytest.raises(ValueError):
            validate_email(email)
```

## Testing Patterns

### Arrange-Act-Assert (AAA)
```python
def test_calculate_discount():
    """Test discount calculation for order total."""
    # Arrange
    order = Order(total=100.0, customer_type="premium")
    calculator = DiscountCalculator()
    
    # Act
    discount = calculator.calculate(order)
    
    # Assert
    assert discount == 10.0  # 10% for premium customers
```

### Fixture Usage
```python
@pytest.fixture
def sample_user():
    """Provide a sample user for testing."""
    return User(
        id=1,
        name="Test User",
        email="test@example.com"
    )

def test_user_full_name(sample_user):
    """Test full name property."""
    assert sample_user.full_name == "Test User"
```

### Mock Objects
```python
def test_send_notification_email(mocker):
    """Test notification email is sent correctly."""
    mock_mailer = mocker.patch("services.email.Mailer")
    
    notifier = Notifier(mock_mailer)
    notifier.send_welcome_email("user@example.com")
    
    mock_mailer.send.assert_called_once_with(
        to="user@example.com",
        subject="Welcome!",
        body=mocker.ANY
    )
```

## Example Generation Requests

### Example 1: Basic Function Testing
```
"Generate comprehensive unit tests for the calculate_shipping_cost() function in src/services/shipping.py. Include tests for different weight ranges, destinations, and shipping methods."
```

### Example 2: Class Testing
```
"Create unit tests for the UserRepository class in src/repositories/user.py. Test all CRUD operations with fixtures for database session and sample users."
```

### Example 3: API Endpoint Testing
```
"Generate integration tests for the POST /api/orders endpoint. Test successful order creation, validation errors, authentication failures, and duplicate order prevention."
```

### Example 4: Async Function Testing
```
"Create async tests for fetch_user_profile() in src/api/client.py. Include tests for successful fetches, timeout handling, network errors, and status code checking."
```

## Test Organization

### File Structure
```
tests/
  unit/
    test_user_service.py
    test_order_service.py
  integration/
    test_api_endpoints.py
    test_database_operations.py
  fixtures/
    conftest.py
    factories.py
```

### Test Class Organization
```python
class TestUserService:
    """Test suite for UserService."""
    
    class TestCreateUser:
        """Tests for create_user method."""
        
        def test_create_with_valid_data(self): ...
        def test_create_with_invalid_email(self): ...
        def test_create_with_duplicate_email(self): ...
    
    class TestUpdateUser:
        """Tests for update_user method."""
        
        def test_update_name(self): ...
        def test_update_email(self): ...
```

## Coverage Goals

### Target Metrics
- **Line Coverage**: 90%+ for new code
- **Branch Coverage**: 85%+ for conditional logic
- **Function Coverage**: 100% for public API
- **Integration Coverage**: Critical user flows tested

### Coverage Analysis
```bash
# Run tests with coverage
pytest --cov=src --cov-report=html

# Review uncovered lines
pytest --cov=src --cov-report=term-missing

# Check branch coverage
pytest --cov=src --cov-branch
```

## Testing Best Practices

### Test Independence
- Each test should run in isolation
- No shared state between tests
- Use fixtures for setup/teardown
- Avoid test execution order dependencies

### Test Clarity
- Descriptive test names explain what is tested
- Include docstrings for complex tests
- Use clear assertion messages
- One logical assertion per test when possible

### Test Maintenance
- Keep tests simple and readable
- Refactor tests when code changes
- Remove obsolete tests
- Update fixtures to match current data models

### Test Performance
- Mock external dependencies (databases, APIs)
- Use in-memory databases for speed
- Parallelize independent tests
- Profile slow tests and optimize

## Integration with CI/CD

### Automated Test Execution
- Run tests on every commit
- Enforce coverage thresholds
- Block merges if tests fail
- Generate coverage reports

### Test Reports
- Track coverage trends over time
- Identify flaky tests
- Monitor test execution time
- Alert on coverage drops

## Limitations

- Generated tests may need review for business logic correctness
- Complex scenarios may require manual test design
- Some edge cases may not be automatically identified
- Mocking strategies may need adjustment based on architecture
