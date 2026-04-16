# Test Suite for DT_BloodSugar_Insulin_Team1

This folder contains unit tests for the Digital Twin Blood Sugar Insulin Simulation project.

## Test Structure

```
tests/
├── __init__.py
├── README.md (you are here)
└── test_digital_twin.py
```

## Writing Tests

### Test File Naming
- Must be `test_*.py` or `*_test.py`
- Discovery is automatic

### Test Function Naming
- Must be `def test_*():`
- Class-based: `class Test*:`

### Test Example

```python
import unittest
from src.DigitalTwin import GlucoseSimulation

class TestGlucoseSimulation(unittest.TestCase):
    """Tests for GlucoseSimulation class."""
    
    def setUp(self) -> None:
        """Set up test fixtures before each test."""
        self.sim = GlucoseSimulation()
    
    def test_initialization(self) -> None:
        """Test that simulation initializes with correct defaults."""
        self.assertEqual(self.sim.glucose[0], 5.0)
        self.assertEqual(self.sim.insulin[0], 10.0)
    
    def test_add_meal_positive(self) -> None:
        """Test adding a meal with positive carbs."""
        initial_buffer = self.sim.meal_buffer
        self.sim.add_meal(50.0)
        self.assertEqual(self.sim.meal_buffer, initial_buffer + 50.0)
    
    def test_add_meal_negative_raises(self) -> None:
        """Test that negative carbs raise ValueError."""
        with self.assertRaises(ValueError):
            self.sim.add_meal(-50.0)
    
    def test_simulate_step(self) -> None:
        """Test one simulation step produces valid output."""
        self.sim.simulate_step()
        # Check glucose is within valid range
        self.assertGreater(self.sim.glucose[1], 0)
        self.assertLess(self.sim.glucose[1], 500)
```

## Running Tests

### Run All Tests
```bash
pytest tests/ -v --tb=short
```

### Run Specific Test File
```bash
pytest tests/test_digital_twin.py -v
```

### Run Specific Test
```bash
pytest tests/test_digital_twin.py::TestGlucoseSimulation::test_initialization -v
```

### Run Tests Matching Pattern
```bash
pytest tests/ -k "meal" -v   # Run tests with "meal" in name
pytest tests/ -k "not slow"  # Skip tests marked as slow
```

### With Coverage Report
```bash
pytest tests/ --cov=src --cov-report=html
# Open htmlcov/index.html in browser
```

## Test Best Practices

### ✅ DO

- **Test one thing per test**: Each test should verify one behavior
- **Use descriptive names**: `test_add_meal_negative_raises()` not `test1()`
- **Use setUp/tearDown**: Initialize fixtures in `setUp()` method
- **Test edge cases**: Test boundary conditions, negative values, etc.
- **Use assertions**: `assertEqual`, `assertRaises`, `assertGreater`, etc.
- **Test error handling**: Verify exceptions are raised correctly

### ❌ DON'T

- **Don't test dependencies**: Test your code, not numpy/matplotlib
- **Don't use sleep**: Tests should be fast
- **Don't create side effects**: Tests should be isolated
- **Don't ignore test failures**: Fix them immediately
- **Don't test implementation**: Test behavior/API
- **Don't copy-paste test code**: Use fixtures and helper methods

## Common Assertions

```python
# Equality
self.assertEqual(actual, expected)
self.assertNotEqual(actual, expected)

# Truth
self.assertTrue(condition)
self.assertFalse(condition)
self.assertIsNone(value)
self.assertIsNotNone(value)

# Comparison
self.assertGreater(a, b)
self.assertLess(a, b)
self.assertGreaterEqual(a, b)
self.assertLessEqual(a, b)

# Collections
self.assertIn(item, collection)
self.assertNotIn(item, collection)
self.assertEqual(len(collection), expected_length)

# Exceptions
with self.assertRaises(ValueError):
    function_that_should_raise()

# Approximate equality (for floats)
self.assertAlmostEqual(actual, expected, places=2)
```

## Configuration

Tests are configured in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
addopts = "-v --strict-markers --tb=short"
```

## Minimum Test Coverage

For this project, aim for tests covering:
- ✅ Core simulation functions (glucose/insulin calculations)
- ✅ Input validation (negative values, boundary conditions)
- ✅ Callbacks and UI interactions
- ✅ State transitions

## Resources

- [pytest Documentation](https://docs.pytest.org/)
- [unittest Documentation](https://docs.python.org/3/library/unittest.html)
- [Python Testing Best Practices](https://docs.pytest.org/en/latest/goodpractices.html)
