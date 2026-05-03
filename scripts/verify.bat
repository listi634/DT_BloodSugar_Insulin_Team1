@REM Verification script for Windows (Command Prompt version)
@REM Run all required checks for GitHub Copilot generated code
@REM Usage: verify.bat [target_path]

@echo off
setlocal enabledelayedexpansion

echo.
echo ========================================================================
echo    GITHUB COPILOT CODE VERIFICATION
echo    DT_BloodSugar_Insulin_Team1
echo ========================================================================
echo.

set TARGET=%1
if "%TARGET%"=="" set TARGET=src

set BLACK_PASS=0
set PYLINT_PASS=0
set MYPY_PASS=0
set PYTEST_PASS=0
set USECASE_PASS=0

REM Step 1: Black (Auto-formatter)
echo.
echo ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
echo [STEP 1] AUTO-FORMATTING WITH BLACK
echo ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
echo Running: black %TARGET% --line-length=79
echo.
call black "%TARGET%" --line-length=79
if %errorlevel% equ 0 (
    echo. [OK] Black formatting completed
    set BLACK_PASS=1
) else (
    echo. [ERROR] Black formatting failed
    set BLACK_PASS=0
)

REM Step 2: Pylint (Linter)
echo.
echo ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
echo [STEP 2] LINTING WITH PYLINT
echo ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
echo Running: pylint %TARGET% --rcfile=.pylintrc
echo.
call pylint "%TARGET%" --rcfile=.pylintrc
if %errorlevel% equ 0 (
    echo. [OK] Pylint check passed
    set PYLINT_PASS=1
) else (
    echo. [WARNING] Pylint found issues (may be non-critical)
    set PYLINT_PASS=0
)

REM Step 3: mypy (Type checker)
echo.
echo ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
echo [STEP 3] TYPE CHECKING WITH MYPY
echo ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
echo Running: mypy %TARGET% --strict
echo.
call mypy "%TARGET%" --strict
if %errorlevel% equ 0 (
    echo. [OK] mypy type checking passed
    set MYPY_PASS=1
) else (
    echo. [WARNING] mypy found type issues
    set MYPY_PASS=0
)

REM Step 4: Check use-case document presence
echo.
echo ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
echo [STEP] CHECKING PROJECT USE-CASE DOCUMENT
echo ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
if exist project_files\USE_CASES_AND_GOALS.md (
    echo. [OK] Use-case document found
    set USECASE_PASS=1
) else (
    echo. [FAILED] project_files\USE_CASES_AND_GOALS.md is missing
    set USECASE_PASS=0
)

REM Step 4: Run tests if they exist
if exist tests (
    echo.
    echo ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    echo [STEP 4] RUNNING TESTS
    echo ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    echo Running: pytest tests/ -v --tb=short
    echo.
    call pytest tests/ -v --tb=short
    if %errorlevel% equ 0 (
        echo. [OK] All tests passed
        set PYTEST_PASS=1
    ) else (
        echo. [ERROR] Tests failed
        set PYTEST_PASS=0
    )
) else (
    echo. [SKIP] No tests directory found
    set PYTEST_PASS=1
)

REM Print summary
echo.
echo ========================================================================
echo VERIFICATION SUMMARY
echo ========================================================================
if !BLACK_PASS! equ 1 (
    echo Black          [PASSED]
) else (
    echo Black          [FAILED]
)
if !PYLINT_PASS! equ 1 (
    echo Pylint         [PASSED]
) else (
    echo Pylint         [ISSUES]
)
if !MYPY_PASS! equ 1 (
    echo mypy           [PASSED]
) else (
    echo mypy           [ISSUES]
)
if !PYTEST_PASS! equ 1 (
    echo Tests          [PASSED]
) else (
    echo Tests          [FAILED]
)
if !USECASE_PASS! equ 1 (
    echo UseCaseDoc      [PRESENT]
) else (
    echo UseCaseDoc      [MISSING]
)
echo ========================================================================

if !BLACK_PASS! equ 1 if !MYPY_PASS! equ 1 if !PYTEST_PASS! equ 1 if !USECASE_PASS! equ 1 (
    echo ALL CRITICAL CHECKS PASSED - Code is ready for commit!
    endlocal
    exit /b 0
) else (
    echo SOME CHECKS FAILED - Fix issues before committing
    endlocal
    exit /b 1
)
