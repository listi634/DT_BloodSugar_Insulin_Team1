"""Main README for DT_BloodSugar_Insulin_Team1 project.

This is the Digital Twin for Blood Sugar and Insulin Simulation project
developed as part of the Digital Twin lecture.
"""

# DT_BloodSugar_Insulin_Team1

**Digital Twin for Blood Sugar and Insulin Simulation**

---

## Project Overview

This project implements a modular digital twin simulation for blood glucose
and insulin dynamics. It models the physiological relationships between
meals, insulin dosing, and blood glucose levels, and combines a simulation
core with a responsive GUI for interactive experiments.

**Language**: Python 3.13  
**Team**: Team 1  
**Assignment**: SW05 Blutzucker Insulin Simulation

---

## Quick Start

### 1. Install Dependencies
```bash
pipenv install --dev
```

### 2. Run Verification (After Code Changes)
**Windows PowerShell** (Recommended):
```powershell
.\scripts\verify.ps1
```

**macOS/Linux**:
```bash
python scripts/verify.py
```

### 3. Run Application
```bash
python -m src.main
```

### 4. Run Tests
```bash
pytest tests/ -v
```

---

## Project Structure

```
DT_BloodSugar_Insulin_Team1/
├── .github/
│   ├── copilot-instructions.md      ← GitHub Copilot Guidelines (START HERE!)
│   └── VERIFICATION_SETUP.md        ← Detailed setup & troubleshooting
├── archive/
│   └── DigitalTwin.py               ← Legacy implementation (reference)
├── project_files/
│   ├── DT_glucose_insulin_tasks.pdf
│   ├── DT_glucose_insulin_task_summary.md
│   └── SW05 Blutzucker Insulin Simulation.pdf
├── scripts/
│   ├── verify.py                    ← Verification script (Python)
│   ├── verify.ps1                   ← Verification script (PowerShell)
│   ├── verify.bat                   ← Verification script (Batch)
│   └── README.md                    ← Scripts documentation
├── src/
│   ├── core/
│   │   ├── controller.py            ← Automated insulin control logic
│   │   ├── integrator.py            ← Numeric integration helpers
│   │   ├── model.py                 ← Glucose-insulin model equations
│   │   ├── simulator.py             ← Simulation loop and event handling
│   │   ├── state.py                 ← Simulation state/data containers
│   │   └── __init__.py
│   ├── gui/
│   │   ├── app.py                   ← Main CustomTkinter application
│   │   ├── control_panel.py         ← User inputs for meal/sport/actions
│   │   ├── plot_frame.py            ← Embedded Matplotlib live charts
│   │   └── __init__.py
│   ├── main.py                      ← Entry point
│   └── __init__.py
├── tests/
│   ├── __init__.py
│   ├── README.md                   ← Testing documentation
│   ├── test_controller.py
│   ├── test_integrator.py
│   ├── test_model.py
│   └── test_simulator.py
├── .gitignore
├── .pylintrc                        ← Pylint configuration
├── pyproject.toml                   ← Black & pytest configuration
├── mypy.ini                         ← Type checker configuration
├── Pipfile                          ← Dependency management
├── README.md                        ← You are here
```

---

## Using GitHub Copilot

**IMPORTANT**: All AI-generated code must be verified before committing.

### Workflow

1. **Accept Copilot suggestion** in your editor
2. **Run verification**:
   ```powershell
   .\scripts\verify.ps1
   ```
3. **Fix any issues** reported by the tools
4. **Commit** only when all checks pass

### Guidelines

See [`.github/copilot-instructions.md`](.github/copilot-instructions.md) for:
- Code style standards (Google Python Style Guide)
- Type hints requirements
- Docstring format
- Common patterns for this domain
- Best practices for prompting Copilot

### Verification Tools

The verification script automatically runs:
- **Black** - Auto-formats code
- **Pylint** - Lints for style violations
- **mypy** - Type checking
- **pytest** - Unit tests

---

## Code Style

This project follows the **Google Python Style Guide**.

### Key Requirements

- ✅ **Line length**: Max 79 characters
- ✅ **Naming**: `snake_case` for functions, `PascalCase` for classes, `UPPER_CASE` for constants
- ✅ **Type hints**: Required on all function signatures (PEP 484)
- ✅ **Docstrings**: Google format, required for all public functions
- ✅ **Imports**: Use full package names, order: stdlib → third-party → local
- ✅ **Comments**: Explain **why**, not **what**

### Example

```python
def calculate_glucose_delta(
    insulin: float,
    current_glucose: float
) -> float:
    """Calculates glucose change for this time step.
    
    Uses simplified pharmacokinetic model.
    
    Args:
        insulin: Current insulin level in mU/L.
        current_glucose: Current glucose level in mmol/l.
    
    Returns:
        Change in glucose (mmol/l).
    
    Raises:
        ValueError: If insulin or glucose are negative.
    """
    if insulin < 0 or current_glucose < 0:
        raise ValueError("Values must be non-negative")
    return -(insulin / 100.0) * (current_glucose / 100.0)
```

---

## Verification Checklist

**Before committing ANY code:**

- [ ] Run `.\scripts\verify.ps1` (or equivalent)
- [ ] All checks show ✅ PASSED
- [ ] Manually review diff: `git diff`
- [ ] Docstrings are complete
- [ ] Type hints are present
- [ ] Tests pass
- [ ] No hardcoded values (use constants)
- [ ] Commit message is descriptive

---

## Documentation

- [GitHub Copilot Instructions](.github/copilot-instructions.md) - Guidelines for AI-generated code
- [Verification Setup](.github/VERIFICATION_SETUP.md) - Detailed tool documentation
- [Scripts README](scripts/README.md) - Verification scripts guide
- [Tests README](tests/README.md) - Testing documentation
- [Use Cases & Goals](project_files/USE_CASES_AND_GOALS.md) - Canonical project use-cases and high-level goals
- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html) - Official reference

---

## Dependencies

### Runtime
- **numpy** - Numerical computations
- **matplotlib** - Visualization and UI
- **customtkinter** - Modern Tkinter-based GUI framework
- **scipy** - Scientific utilities for numerical workflows

### Development
- **black** - Code formatter
- **pylint** - Linter
- **mypy** - Type checker
- **pytest** - Testing framework
- **flake8** - Additional style checking
- **isort** - Import sorting

### Installation
```bash
pipenv install --dev
```

---

## Testing

### Run Tests
```bash
pytest tests/ -v --tb=short
```

### Run Specific Test
```bash
pytest tests/test_simulator.py::test_reset_restores_initial_state_and_history -v
```

### With Coverage
```bash
pytest tests/ --cov=src --cov-report=html
# Open htmlcov/index.html
```

See [tests/README.md](tests/README.md) for detailed testing documentation.

---

## Configuration Files

| File | Purpose |
|------|---------|
| `.github/copilot-instructions.md` | GitHub Copilot guidelines |
| `.github/VERIFICATION_SETUP.md` | Tool setup & troubleshooting |
| `.pylintrc` | Pylint linting rules |
| `pyproject.toml` | Black formatter & pytest config |
| `mypy.ini` | Type checker configuration |
| `Pipfile` | Dependency management |
| `.gitignore` | Git ignore rules |

---

## Troubleshooting

### "Command not found: black"
```bash
pipenv install --dev
```

### "Black cannot format file"
```bash
python -m py_compile src/file.py
```

### "mypy shows too many errors"
See [VERIFICATION_SETUP.md](.github/VERIFICATION_SETUP.md#mypy-issues)

### "Tests fail after code change"
1. Review diff: `git diff src/`
2. Update tests if needed
3. Run specific test: `pytest tests/test_file.py -v`

---

## Resources

- [Google Python Style Guide](https://google.github.io/styleguide/pyguide.html)
- [Black Documentation](https://black.readthedocs.io/)
- [Pylint Guide](https://pylint.readthedocs.io/)
- [mypy Handbook](https://mypy.readthedocs.io/)
- [pytest Documentation](https://docs.pytest.org/)
- [PEP 8](https://pep8.org/)
- [PEP 484 (Type Hints)](https://www.python.org/dev/peps/pep-0484/)

---

## Getting Help

1. Check [`.github/copilot-instructions.md`](.github/copilot-instructions.md) for guidelines
2. See [`.github/VERIFICATION_SETUP.md`](.github/VERIFICATION_SETUP.md) for tool details
3. Review [task summary](project_files/DT_glucose_insulin_task_summary.md)
4. Check git log for similar changes: `git log --oneline`

---

**Created**: April 16, 2026  
**Project**: DT_BloodSugar_Insulin_Team1  
**Python**: 3.13
