# PV-BESS Tool - Unit Tests

## Running Tests

### Install test dependencies:
```bash
pip install pytest pytest-cov numpy pandas
```

### Run all tests:
```bash
# From project root
pytest tests/ -v

# With coverage report
pytest tests/ --cov=backend/app/services --cov-report=html

# Run specific test file
pytest tests/test_baseline_service.py -v

# Run specific test
pytest tests/test_optimization_service.py::TestOptimizationService::test_revenue_improvement -v
```

## Test Structure

```
tests/
├── __init__.py                    # Package marker
├── conftest.py                     # Shared fixtures and configuration
├── test_baseline_service.py        # Tests for PV baseline calculations
├── test_optimization_service.py    # Tests for LP optimization
└── test_auto_sizing_service.py     # Tests for battery sizing logic
```

## Test Coverage

### Baseline Service (`test_baseline_service.py`)
- ✅ Basic baseline calculation
- ✅ Capture rate calculation
- ✅ Cannibalization effect
- ✅ Negative price handling
- ✅ Battery recommendation logic
- ✅ Zero generation edge case
- ✅ Mismatched data lengths
- ✅ Extreme cannibalization scenarios

### Optimization Service (`test_optimization_service.py`)  
- ✅ LP solver completion
- ✅ Revenue improvement verification
- ✅ Arbitrage behavior (charge low, discharge high)
- ✅ Power constraint compliance
- ✅ Capacity constraint compliance
- ✅ Negative price handling
- ✅ Battery utilization calculations
- ✅ Annual cycles calculation
- ✅ Flat price edge case
- ✅ Short duration battery

### Auto-Sizing Service (`test_auto_sizing_service.py`)
- ✅ Smart defaults structure
- ✅ Conservative sizing (25%, 2h)
- ✅ Moderate sizing (40%, 4h)
- ✅ Aggressive sizing (60%, 6h)
- ✅ All sizing options
- ✅ Validation for reasonable sizing
- ✅ Validation warnings (oversized, short/long duration)
- ✅ Small and large PV systems
- ✅ Invalid mode handling
- ✅ Zero capacity edge cases

## Continuous Integration

Add to your CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
name: Tests
on: [push, pull_request]
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v2
      - uses: actions/setup-python@v2
        with:
          python-version: '3.9'
      - run: pip install -r requirements.txt
      - run: pip install pytest pytest-cov
      - run: pytest tests/ --cov=backend/app/services --cov-report=xml
      - uses: codecov/codecov-action@v2
```

## Writing New Tests

### Test Naming Convention
- Test files: `test_<module_name>.py`
- Test classes: `Test<FeatureName>`
- Test methods: `test_<what_it_tests>`

### Example Test Template
```python
def test_feature_name(self):
    """Test description."""
    # Arrange
    input_data = create_test_data()
    
    # Act
    result = function_under_test(input_data)
    
    # Assert
    assert result['expected_key'] == expected_value
    assert condition_is_true
```

### Fixtures
Use `@pytest.fixture` for reusable test data:
```python
@pytest.fixture
def sample_data(self):
    return {'key': 'value'}

def test_with_fixture(self, sample_data):
    assert sample_data['key'] == 'value'
```

## Test Philosophy

1. **Unit Tests**: Test individual functions/methods in isolation
2. **Fast**: All tests should complete in < 5 seconds
3. **Deterministic**: Same input = same output (no random failures)
4. **Independent**: Tests don't depend on each other
5. **Descriptive**: Test names explain what they verify

## Known Limitations

- No integration tests yet (Streamlit UI testing)
- No end-to-end tests (full workflow)
- Limited error handling tests for external API failures
- No performance/load tests

## Future Test Additions

- [ ] PV service tests (PVGIS API mocking)
- [ ] ENTSO-E service tests (API mocking)
- [ ] Financial calculation tests (IRR, NPV, payback)
- [ ] Integration tests for Stage 1-2-3 flow
- [ ] UI component tests (Streamlit testing framework)
