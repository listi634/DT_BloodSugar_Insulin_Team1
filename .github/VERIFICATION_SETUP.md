# Verification Setup and Troubleshooting Guide

**For Quick Start**: See `.github/copilot-instructions.md`

This document provides detailed information about the verification system, tool configuration, and troubleshooting.

---

## Table of Contents

1. [Installation](#installation)
2. [Running Verification](#running-verification)
3. [Understanding Each Tool](#understanding-each-tool)
4. [Configuration Deep Dive](#configuration-deep-dive)
5. [Troubleshooting](#troubleshooting)
6. [Advanced Usage](#advanced-usage)

---

## Installation

### Option 1: Using Pipenv (Recommended)

```bash
# Install all dependencies including dev tools
pipenv install --dev

# Activate environment
pipenv shell
```

This installs:
- **Production**: numpy, matplotlib
- **Development**: black, pylint, mypy, pytest, flake8, isort

### Option 2: Using pip

```bash
pip install black pylint mypy pytest flake8 isort numpy matplotlib
```

### Verify Installation

```bash
black --version
pylint --version
mypy --version
pytest --version
```

---

## Running Verification

### Windows PowerShell (Recommended)

```powershell
# Check all code
.\scripts\verify.ps1

# Check specific file
.\scripts\verify.ps1 -Target "src/DigitalTwin.py"

# See all options
Get-Help .\scripts\verify.ps1
```

**Features**:
- Color-coded output
- Progress indicators
- Auto-opens HTML reports (optional)

### Windows Command Prompt

```cmd
# Check all code
scripts\verify.bat

# Check specific file
scripts\verify.bat src/DigitalTwin.py
```

### macOS/Linux

```bash
# Check all code
python scripts/verify.py

# Check specific file
python scripts/verify.py src/DigitalTwin.py

# See all options
python scripts/verify.py --help
```

### Expected Output (All Pass)

```
========================================================================
    GITHUB COPILOT CODE VERIFICATION
    DT_BloodSugar_Insulin_Team1
========================================================================

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
[STEP 1] AUTO-FORMATTING WITH BLACK
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
All done! 3 files left unchanged.

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
[STEP 2] LINTING WITH PYLINT
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src/DigitalTwin.py:1:0: C0114: Missing module docstring (missing-docstring)

Your code has been rated at 9.50/10

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
[STEP 3] TYPE CHECKING WITH MYPY
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Success: no issues found in 3 source files

^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
[STEP 4] RUNNING TESTS
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
tests/test_digital_twin.py::TestGlucoseSimulation::test_init PASSED
tests/test_digital_twin.py::TestGlucoseSimulation::test_simulate PASSED

========================================================================
VERIFICATION SUMMARY
========================================================================
Black          ✓ PASSED
Pylint         ⚠ ISSUES (non-critical)
mypy           ✓ PASSED
Tests          ✓ PASSED
========================================================================
✓ ALL CHECKS PASSED - Code is ready for commit!
========================================================================
```

---

## Understanding Each Tool

### Black (Code Formatter)

**What it does**: Automatically formats code to PEP 8 standard.

**Auto-fixes**:
- ✅ Line length violations (> 79 chars)
- ✅ Inconsistent spacing
- ✅ Quote styles (` to ")
- ✅ Import ordering
- ✅ Parentheses placement

**Manual command**:
```bash
black src/ --line-length=79
black src/DigitalTwin.py --check  # Dry-run (no changes)
```

**Config**: `pyproject.toml` `[tool.black]`

---

### Pylint (Linter)

**What it does**: Checks for style violations, potential bugs, and code smell.

**Common warnings**:

| Code | Meaning | Fix |
|------|---------|-----|
| `C0103` | Invalid name (not snake_case) | Rename variable/function |
| `C0114` | Missing module docstring | Add module docstring at top of file |
| `C0116` | Missing function docstring | Add docstring to function |
| `W0612` | Unused variable | Remove or use variable |
| `C0301` | Line too long (after Black) | Rare - check line manually |
| `W0611` | Unused import | Remove import |

**Suppress warnings** (when appropriate):
```python
def unusual_name():  # pylint: disable=invalid-name
    """Explanation of why this name is necessary."""
    pass
```

**Manual command**:
```bash
pylint src/ --rcfile=.pylintrc
pylint src/ --list-msgs           # List all possible warnings
pylint src/ --help-msg=C0103      # Info on specific warning
```

**Config**: `.pylintrc`

---

### mypy (Type Checker)

**What it does**: Verifies type hints are correct and complete.

**Common errors**:

| Error | Meaning | Fix |
|-------|---------|-----|
| `error: Function is missing a type annotation for one or more arguments` | Parameter missing type hint | Add `: Type` to parameter |
| `error: Argument 1 to "func" has incompatible type "str"; expected "float"` | Wrong type passed | Check function call |
| `error: Name "x" is not defined` | Variable undefined or misspelled | Check variable name |

**Manual command**:
```bash
mypy src/ --strict                          # Strict mode (recommended)
mypy src/ --no-strict                       # Lenient mode (debugging)
mypy src/ --show-error-codes --pretty       # Detailed output
```

**Config**: `mypy.ini`

**Add type hints**:
```python
# Before
def calculate_glucose(insulin, carbs):
    return -(insulin * 0.1) + (carbs * 0.05)

# After
def calculate_glucose(insulin: float, carbs: float) -> float:
    return -(insulin * 0.1) + (carbs * 0.05)
```

---

### pytest (Test Runner)

**What it does**: Discovers and runs unit tests.

**File discovery**:
- Files: `test_*.py` or `*_test.py`
- Functions: `def test_*():`
- Classes: `class Test*:`

**Manual command**:
```bash
pytest tests/ -v --tb=short          # Run all tests, verbose
pytest tests/test_digital_twin.py    # Run specific file
pytest tests/ -k "glucose"           # Run tests matching "glucose"
pytest tests/ --cov=src              # With coverage report
```

**Config**: `pyproject.toml` `[tool.pytest.ini_options]`

**Example test**:
```python
import unittest
from src.DigitalTwin import GlucoseSimulation

class TestGlucoseSimulation(unittest.TestCase):
    def setUp(self) -> None:
        self.sim = GlucoseSimulation()
    
    def test_initial_state(self) -> None:
        self.assertEqual(self.sim.glucose[0], 5.0)
    
    def test_negative_glucose_raises(self) -> None:
        with self.assertRaises(ValueError):
            self.sim.add_meal(-50)
```

---

## Configuration Deep Dive

### `.pylintrc` (Root)

Key sections:

```ini
[MASTER]
ignore-patterns=test_.*?py
max-line-length=79

[MESSAGES CONTROL]
disable=
    missing-module-docstring,
    too-few-public-methods,

[FORMAT]
max-line-length=79
indent-string='    '

[BASIC]
good-names=i,j,k,ex,Run,_

[DESIGN]
max-locals=15
max-arguments=5
```

**Customize**:
- Add to `disable` list to suppress warnings
- Change `max-line-length` if needed (keep ≤ 79)
- Add short variable names to `good-names`

---

### `pyproject.toml` (Root)

**Black section**:
```toml
[tool.black]
line-length = 79
target-version = ['py313']
```

**pytest section**:
```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py", "*_test.py"]
addopts = "-v --strict-markers --tb=short"
```

**Coverage section**:
```toml
[tool.coverage.run]
source = ["src"]
omit = ["*/tests/*"]
```

---

### `mypy.ini` (Root)

```ini
[mypy]
python_version = 3.13
warn_return_any = True
disallow_untyped_defs = True
strict_optional = True

[mypy-numpy]
ignore_missing_imports = True

[mypy-matplotlib.*]
ignore_missing_imports = True
```

**Strictness levels**:
- **Strictest**: All flags enabled (current)
- **Strict**: `disallow_untyped_defs = True`
- **Lenient**: Only `warn_return_any = True`

---

## Troubleshooting

### Black Issues

#### "Black doesn't format my file"
**Possible causes**:
1. Syntax error in file
2. Already formatted correctly
3. Line is in a long string/comment (Black respects these)

**Debug**:
```bash
python -m py_compile src/file.py
```

---

#### "Black added unwanted line break"
**Reason**: Black prioritizes readability. Line was probably >79 chars.

**Options**:
1. Accept the break (it's often better)
2. Refactor to shorter variable names
3. Disable line length just for that line:
```python
# fmt: off
very_long_line = something + something_else + more_stuff
# fmt: on
```

---

### Pylint Issues

#### "Pylint gives too many warnings"
**Steps**:
1. Fix actual errors first (marked with E)
2. Address warnings (marked with W)
3. Consider code refactoring for suggestions

**Grade your code**:
```bash
pylint src/ --rcfile=.pylintrc
# Last line shows score like "9.50/10"
```

---

#### "Suppress warning for good reason"
```python
def add_meal(event):  # pylint: disable=unused-argument
    """Button callback receives event but doesn't use it."""
    # Button event is required by matplotlib callback signature
    self.meal_buffer += 50
```

---

### mypy Issues

#### "mypy complains about numpy/matplotlib"
**Expected**: These libraries don't have full type support.

**Solution**: Already handled in `mypy.ini`:
```ini
[mypy-numpy]
ignore_missing_imports = True

[mypy-matplotlib.*]
ignore_missing_imports = True
```

---

#### "mypy: 'None' is not assignable to 'float'"
**Problem**:
```python
def calculate() -> float:
    if condition:
        return None  # ERROR: None is not float
```

**Fix**: Use Optional
```python
from typing import Optional

def calculate() -> Optional[float]:
    if condition:
        return None
    return 5.0
```

---

#### "I don't know what type to use"
**Reference**: Common types for this project:

```python
from typing import Optional, Union, List, Dict, Tuple

# Basic types
x: int = 5
y: float = 5.0
z: str = "hello"
is_valid: bool = True

# Collections
values: List[float] = [1.0, 2.0, 3.0]
state: Dict[str, float] = {"glucose": 5.0, "insulin": 10.0}
pair: Tuple[float, float] = (5.0, 10.0)

# Optional (can be None)
result: Optional[float] = None

# Function types
Callable[[float, float], float]  # Takes two floats, returns float
```

---

### pytest Issues

#### "pytest can't find tests"
**Checklist**:
1. Files named `test_*.py`?
2. Functions named `test_*()`?
3. In `tests/` directory?
4. File has `import unittest`?

```bash
# Debug
pytest tests/ -v --collect-only
```

---

#### "Test fails after Copilot change"
**Process**:
1. Understand what changed: `git diff`
2. Update test if function signature changed
3. Run just that test: `pytest tests/test_file.py::test_name -v`
4. Check if Copilot change broke test logic

---

### Script Issues

#### "verify.ps1: cannot be loaded because running scripts is disabled"
**Windows PowerShell**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

#### "python: command not found"
**Pipenv**:
```bash
pipenv shell
python scripts/verify.py
```

**Direct Python**:
```bash
python3 scripts/verify.py  # Use python3 instead
```

---

## Advanced Usage

### Generate Coverage Report

```bash
pytest tests/ --cov=src --cov-report=html
# Open htmlcov/index.html in browser
```

---

### Run Specific Tool Only

```bash
# Just Black
black src/ --line-length=79

# Just Pylint
pylint src/ --rcfile=.pylintrc

# Just mypy
mypy src/ --strict

# Just pytest
pytest tests/ -v
```

---

### Create Test Coverage Badge

```bash
pytest tests/ --cov=src --cov-report=term-missing
# Shows which lines aren't covered by tests
```

---

### Pre-Commit Hook

Auto-run verification before every commit:

**Windows**:
Create `.git/hooks/pre-commit` (no extension):
```powershell
#!/usr/bin/env powershell
if (-Not (& .\scripts\verify.ps1)) {
    exit 1
}
```

**macOS/Linux**:
Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash
python scripts/verify.py || exit 1
```

Make executable:
```bash
chmod +x .git/hooks/pre-commit
```

---

## Typical Workflow Example

### Scenario: Copilot generates glucose calculation function

**1. Accept suggestion in editor**

**2. Run verification**
```powershell
.\scripts\verify.ps1
```

**3. Black formats** (auto-fixes)
```
[STEP 1] AUTO-FORMATTING
All done! 1 file reformatted.
```

**4. Pylint warns**
```
C0116: Missing function docstring (missing-docstring)
W0612: Unused variable 'unused_val' (unused-variable)
```

**5. Fix issues**
```python
def calculate_glucose_delta(
    insulin: float,
    carbs: float
) -> float:
    """Calculate glucose change per time step.
    
    Args:
        insulin: Insulin level in mU/L.
        carbs: Carbs absorbed in grams.
    
    Returns:
        Glucose delta in mmol/l.
    """
    return -(insulin * 0.1) + (carbs * 0.05)
```

**6. Run verification again**
```powershell
.\scripts\verify.ps1
# ✓ ALL CHECKS PASSED
```

**7. Commit**
```bash
git add src/DigitalTwin.py
git commit -m "Add calculate_glucose_delta function - AI assisted"
```

---

## Resources

- [Black Docs](https://black.readthedocs.io/)
- [Pylint Docs](https://pylint.readthedocs.io/)
- [mypy Handbook](https://mypy.readthedocs.io/)
- [pytest Docs](https://docs.pytest.org/)
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [PEP 8](https://pep8.org/)

---

**Need more help?** Check `.github/copilot-instructions.md` for the main guidelines.
