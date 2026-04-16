# GitHub Copilot Instructions for DT_BloodSugar_Insulin_Team1

**Version**: 1.0  
**Last Updated**: April 16, 2026  
**Project**: Digital Twin for Blood Sugar and Insulin Simulation  
**Python**: 3.13

This document defines the guidelines and workflow for using GitHub Copilot in this project. **All code generated or modified by GitHub Copilot MUST pass automated verification checks before committing.**

---

## Table of Contents

1. [Quick Start](#quick-start)
2. [Code Style Standards](#code-style-standards)
3. [Project Overview](#project-overview)
4. [Verification Workflow](#verification-workflow)
5. [Configuration Files](#configuration-files)
6. [Common Patterns](#common-patterns)
7. [Prompting Best Practices](#prompting-best-practices)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

### 1️⃣ Install Development Tools
```bash
pipenv install --dev
```

### 2️⃣ After Copilot Generates Code
**Windows PowerShell (Recommended)**:
```powershell
.\scripts\verify.ps1
```

**Windows Command Prompt**:
```cmd
scripts\verify.bat
```

**macOS/Linux**:
```bash
python scripts/verify.py
```

### 3️⃣ Review Output
- ✅ All checks passed? → Proceed to commit
- ❌ Issues found? → Fix and run verification again

### 4️⃣ Commit Changes
```bash
git add .
git commit -m "Add [feature] - AI assisted"
```

---

## Code Style Standards

This project follows the **[Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)**.

### Line Length
- **Maximum**: 79 characters (80 column terminals)
- **Exception**: Long URLs, imports may exceed if necessary

### 2.1 Naming Conventions

| Element | Convention | Example |
|---------|-----------|---------|
| Constants | `UPPER_CASE_WITH_UNDERSCORES` | `G_BASAL = 5.0` |
| Classes | `PascalCase` | `class GlucoseSimulation` |
| Functions/Methods | `snake_case` | `def calculate_glucose()` |
| Variables | `snake_case` | `current_glucose` |
| Private/Protected | Prefix `_` | `self._internal_state` |

### 2.2 Imports

**Order** (strict):
```python
# 1. Standard library
import os
import sys

# 2. Third-party
import numpy as np
import matplotlib.pyplot as plt

# 3. Local modules
from src.DigitalTwin import GlucoseSimulation
```

**Rule**: Use `import` for packages/modules, NOT for individual items

```python
# ✅ CORRECT
import numpy as np
glucose_array = np.zeros(10)

# ❌ INCORRECT
from numpy import zeros
glucose_array = zeros(10)
```

### 2.3 Docstrings (Google Format)

**REQUIRED** for all public functions, methods, classes.

```python
def calculate_glucose_delta(
    insulin: float,
    current_glucose: float
) -> float:
    """Calculates glucose change for this time step.
    
    Uses simplified pharmacokinetic model for digital twin simulation.
    
    Args:
        insulin: Current insulin level in mU/L.
        current_glucose: Current glucose level in mmol/l.
    
    Returns:
        Change in glucose (mmol/l) for this time step.
    
    Raises:
        ValueError: If insulin or glucose are negative.
    """
    if insulin < 0 or current_glucose < 0:
        raise ValueError("Values must be non-negative")
    return -(insulin / 100.0) * (current_glucose / 100.0)
```

### 2.4 Type Hints (PEP 484)

**REQUIRED** on all function signatures.

```python
# ✅ CORRECT
def simulate_step(
    self,
    carbs: float,
    insulin_units: float
) -> tuple[float, float]:
    """Simulates one time step."""
    pass

# ❌ INCORRECT
def simulate_step(self, carbs, insulin_units):
    pass
```

### 2.5 Comments

- Explain **WHY**, not **WHAT**
- Use `#` before code
- Never use `"""` for comments (only docstrings)

```python
# ✅ CORRECT: Explains reasoning
# Absorb 3% insulin per minute per realistic pharmacokinetics
insulin_absorbed = self.insulin * 0.03

# ❌ INCORRECT: States the obvious
# Multiply insulin by absorption rate
insulin_absorbed = self.insulin * 0.03
```

### 2.6 Exception Handling

- Catch **specific** exceptions only
- Never use bare `except:`
- Use `ValueError` for invalid inputs

```python
# ✅ CORRECT
try:
    glucose_value = float(user_input)
except ValueError:
    print("Invalid glucose value")
except KeyboardInterrupt:
    print("Interrupted")

# ❌ INCORRECT
try:
    glucose_value = float(user_input)
except:  # TOO BROAD
    print("Error occurred")
```

### 2.7 Global State

**AVOID** mutable globals. Use constants if needed:

```python
# ✅ ACCEPTABLE - Immutable constant
MAX_GLUCOSE_THRESHOLD = 300.0
MIN_INSULIN_THRESHOLD = 2.0

# ❌ AVOID - Mutable global state
simulation_state = {}  # Use dependency injection instead
```

---

## Project Overview

**Domain**: Medical simulation / Digital twin modeling  
**Key Modules**:
- `src/DigitalTwin.py` - Core simulation engine
- `src/main.py` - Entry point and UI

**Dependencies**:
- numpy - Numerical computations
- matplotlib - Visualization and UI

**Python Version**: 3.13

---

## Verification Workflow

### 🔄 Complete Workflow

```
┌─────────────────────────────┐
│ Accept Copilot Suggestion   │
└──────────────┬──────────────┘
               │
               ▼
        ┌──────────────┐
        │ Run verify.* │
        └──────────────┘
               │
        ┌──────┴──────┬──────┬────────┐
        ▼             ▼      ▼        ▼
     Black         Pylint  mypy    pytest
   (Format)       (Lint) (Types)  (Tests)
        │             │      │        │
        └──────┬──────┴──────┴────────┘
               │
         ┌─────▼─────┐
         │ All Pass? │
         └─────┬─────┘
            ┌──┴──┐
            │     │
           YES    NO
            │     │
            ▼     ▼
         Commit  Fix Issues
                 & Re-run
```

### Tool Details

| Tool | Purpose | Auto-fixes | Config |
|------|---------|-----------|--------|
| **Black** | Code formatter | ✅ Yes | `pyproject.toml` |
| **Pylint** | Linter & style checker | ❌ No | `.pylintrc` |
| **mypy** | Type hint validator | ❌ No | `mypy.ini` |
| **pytest** | Unit test runner | ❌ No | `pyproject.toml` |

### Step-by-Step Process

#### Step 1: Auto-Format with Black
```bash
black src/ --line-length=79
```
Automatically fixes:
- Line length violations
- Spacing inconsistencies
- Quote styles
- Import grouping

#### Step 2: Lint with Pylint
```bash
pylint src/ --rcfile=.pylintrc
```
Checks for:
- `C0103` - Invalid names
- `W0612` - Unused variables
- `C0301` - Line too long
- `C0114` - Missing docstring

#### Step 3: Type Check with mypy
```bash
mypy src/ --strict
```
Verifies:
- All functions have type hints
- Type compatibility
- No `Any` types without justification

#### Step 4: Run Tests
```bash
pytest tests/ -v --tb=short
```
Ensures:
- No functional regressions
- All edge cases covered

---

## Configuration Files

### `.pylintrc` (Root)
Pylint configuration following Google standards.
- Line length: 79 characters
- Naming conventions enforced
- Google-style docstrings required

### `pyproject.toml` (Root)
Multi-tool configuration:
- **Black**: Line length, target version
- **pytest**: Test discovery, markers
- **Coverage**: Report settings

### `mypy.ini` (Root)
Type checking with strict mode:
- `disallow_untyped_defs = True`
- `strict_optional = True`

### `Pipfile` (Root)
Dependency management:
- **Production**: numpy, matplotlib
- **Development**: black, pylint, mypy, pytest, flake8, isort

---

## Common Patterns

### Pattern 1: Glucose Simulation Step
```python
def simulate_step(self) -> None:
    """Simulates one time step of glucose-insulin dynamics."""
    # Insulin reduces glucose (simplified pharmacokinetics)
    glucose_delta = -self.insulin * K_GLUCOSE_SENSITIVITY
    
    # Carbs increase glucose
    glucose_delta += self.meal_buffer * K_CARB_ABSORPTION
    
    # Update state
    self.glucose = max(MIN_GLUCOSE, self.glucose + glucose_delta)
    self.meal_buffer *= (1 - K_CARB_ABSORPTION)
```

### Pattern 2: Input Validation
```python
def add_meal(self, carbs: float) -> None:
    """Add meal with carbohydrate content.
    
    Args:
        carbs: Carbohydrates in grams.
    
    Raises:
        ValueError: If carbs is negative.
    """
    if carbs < 0:
        raise ValueError(f"Carbs must be non-negative, got {carbs}")
    self.meal_buffer += carbs
```

### Pattern 3: Type-Hinted Return
```python
def get_state(self) -> dict[str, float]:
    """Returns current glucose and insulin state.
    
    Returns:
        Dictionary with 'glucose' and 'insulin' keys.
    """
    return {
        'glucose': float(self.glucose),
        'insulin': float(self.insulin),
    }
```

---

## Prompting Best Practices

When requesting code from GitHub Copilot, use this template:

```
Generate a function that [DESCRIPTION].

Requirements:
- Follow Google Python Style Guide
- Include complete docstring (Args, Returns, Raises)
- Add type hints (PEP 484)
- Use snake_case for variables, PascalCase for classes
- Maximum line length: 79 characters
- Use UPPER_CASE for constants
- Include error handling with specific exceptions
- Include comments explaining why, not what

Domain context: Medical simulation (diabetes/insulin model)

Example usage:
[provide example if complex]
```

**Example Request**:
```
Generate a function that calculates the absorption rate of carbohydrates 
into the bloodstream over time.

Requirements:
- Follow Google Python Style Guide
- Complete docstring with Args/Returns/Raises
- Type hints on all parameters
- Maximum 79 characters per line
- Handle negative input values with ValueError

Domain: Medical simulation (blood sugar dynamics)
```

---

## Troubleshooting

### ❌ "Command not found: black"
**Solution**: Install dev dependencies
```bash
pipenv install --dev
```

### ❌ Black says "cannot format src/file.py"
**Cause**: Syntax error in file
```bash
python -m py_compile src/file.py
```

### ❌ mypy shows too many errors
**Solution**: Disable strict temporarily to identify real issues
```bash
mypy src/ --no-strict
```

### ❌ Pylint warnings won't go away
**Solution**: Suppress when appropriate (with explanation)
```python
def unusual_name():  # pylint: disable=invalid-name
    """This name is required by external API."""
    pass
```

### ❌ Tests fail after Copilot change
**Steps**:
1. Review diff: `git diff src/`
2. Check if logic changed
3. Update tests if function signature changed
4. Run test individually: `pytest tests/test_specific.py -v`

---

## Pre-Commit Hook (Optional)

Automatically verify code before committing:

### Windows PowerShell

Create `.git/hooks/pre-commit` (no extension):
```powershell
#!/usr/bin/env powershell
$ErrorActionPreference = "Stop"

Write-Host "Running pre-commit checks..."
if (-Not (& .\scripts\verify.ps1)) {
    exit 1
}
exit 0
```

Make executable:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### macOS/Linux

Create `.git/hooks/pre-commit`:
```bash
#!/bin/bash
set -e
python scripts/verify.py
```

Make executable:
```bash
chmod +x .git/hooks/pre-commit
```

---

## Mandatory Checklist

**Before committing ANY AI-generated code:**

- [ ] Run verification script (see Quick Start)
- [ ] All checks show ✅ PASSED
- [ ] Manually review git diff
- [ ] Docstrings are complete and accurate
- [ ] Type hints present on all functions
- [ ] No hardcoded values (use constants)
- [ ] Tests pass
- [ ] Commit message is descriptive

---

## Directory Structure

```
DT_BloodSugar_Insulin_Team1/
├── .github/
│   ├── copilot-instructions.md    ← You are here
│   └── VERIFICATION_SETUP.md      ← Detailed setup guide
├── .gitignore
├── .pylintrc                       ← Pylint configuration
├── Pipfile                         ← Dependencies
├── pyproject.toml                  ← Tool configuration
├── mypy.ini                        ← Type checker config
├── README.md
├── scripts/
│   ├── verify.py                   ← Python verification
│   ├── verify.ps1                  ← PowerShell verification
│   ├── verify.bat                  ← Batch verification
│   └── README.md                   ← Scripts documentation
├── src/
│   ├── DigitalTwin.py
│   └── main.py
├── tests/
│   ├── __init__.py
│   ├── test_digital_twin.py
│   └── README.md
└── project_files/
    └── SW05 Blutzucker Insulin Simulation.pdf
```

---

## Resources

- **[Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)** - Official reference
- **[PEP 8](https://pep8.org/)** - Python style guide
- **[PEP 484](https://www.python.org/dev/peps/pep-0484/)** - Type hints
- **[Black Documentation](https://black.readthedocs.io/)** - Code formatter
- **[Pylint Guide](https://pylint.readthedocs.io/)** - Linter
- **[mypy Handbook](https://mypy.readthedocs.io/)** - Type checker
- **[pytest Documentation](https://docs.pytest.org/)** - Testing framework

---

## Summary

✅ **Consistency** - All code follows the same standards  
✅ **Quality** - Automated checks catch errors early  
✅ **Reliability** - Type checking prevents runtime bugs  
✅ **Maintainability** - Clear docs and naming conventions  
✅ **Collaboration** - Team members know what to expect  

**Key Takeaway**: Run the verification script after EVERY AI code change. No exceptions.

---

**Questions?** See `.github/VERIFICATION_SETUP.md` for detailed setup and troubleshooting.
