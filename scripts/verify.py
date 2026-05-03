#!/usr/bin/env python3
"""Verification script for GitHub Copilot generated code.

This script runs all required checks (Black, Pylint, mypy) on the project
to ensure AI-generated code meets the project's style and quality standards.

Usage:
    python verify.py              # Check all files
    python verify.py src/file.py  # Check specific file
"""

import subprocess
import sys
from pathlib import Path


def run_command(cmd: list[str], description: str) -> bool:
    """Runs a command and returns success status.
    
    Args:
        cmd: Command to run as list of strings.
        description: Human-readable description of what's being checked.
    
    Returns:
        True if command succeeded, False otherwise.
    """
    print(f"\n{'='*70}")
    print(f"[STEP] {description}")
    print(f"{'='*70}")
    print(f"Running: {' '.join(cmd)}\n")
    
    try:
        result = subprocess.run(cmd, check=False)
        return result.returncode == 0
    except FileNotFoundError as e:
        print(f"[ERROR] Command not found: {e}")
        print(f"   Install with: pipenv install --dev")
        return False


def main(target_path: str = "src") -> int:
    """Main verification workflow.
    
    Args:
        target_path: Path to check (default: "src").
    
    Returns:
        Exit code (0 = success, 1 = failure).
    """
    print("="*70)
    print("GITHUB COPILOT CODE VERIFICATION")
    print("DT_BloodSugar_Insulin_Team1")
    print("="*70)
    
    results = {}
    
    # Step 1: Black (Auto-formatter)
    print("\n" + "=" * 70)
    results['black'] = run_command(
        ['black', target_path, '--line-length=79'],
        '1. AUTO-FORMATTING WITH BLACK'
    )
    
    # Step 2: Pylint (Linter)
    print("\n" + "=" * 70)
    results['pylint'] = run_command(
        ['pylint', target_path, '--rcfile=.pylintrc'],
        '2. LINTING WITH PYLINT'
    )
    
    # Step 3: mypy (Type checker)
    print("\n" + "=" * 70)
    results['mypy'] = run_command(
        ['mypy', target_path, '--strict'],
        '3. TYPE CHECKING WITH MYPY'
    )
    
    # Step 4: Use-case document presence and minimal content check
    print("\n" + "=" * 70)
    print("[STEP] CHECKING PROJECT USE-CASE DOCUMENT")
    use_case = Path('project_files/USE_CASES_AND_GOALS.md')
    if use_case.exists():
        try:
            text = use_case.read_text(encoding='utf8')
        except Exception:
            print(f"[ERROR] Cannot read {use_case}")
            results['use_case_doc'] = False
        else:
            required = [
                "Use Cases",
                "Virtual & physical entities",
                "Acceptance criteria",
            ]
            ok = all(k in text for k in required)
            results['use_case_doc'] = ok
            if ok:
                print("[OK] Use-case document present and contains required sections")
            else:
                print("[WARNING] Use-case document is missing required headers")
    else:
        print("[FAILED] project_files/USE_CASES_AND_GOALS.md is missing")
        results['use_case_doc'] = False

    # Step 4: Run tests if they exist
    print("\n" + "=" * 70)
    if Path('tests').exists():
        results['pytest'] = run_command(
            ['pytest', 'tests/', '-v', '--tb=short'],
            '4. RUNNING TESTS'
        )
    else:
        print("\n[SKIP] No tests directory found (tests/ does not exist)")
        results['pytest'] = True
    
    # Print summary
    print("\n" + "="*70)
    print("VERIFICATION SUMMARY")
    print("="*70)
    
    for tool, passed in results.items():
        status = "PASSED" if passed else "FAILED"
        print(f"{tool:12} {status}")
    
    all_passed = all(results.values())
    
    print("="*70)
    if all_passed:
        print("ALL CHECKS PASSED - Code is ready for commit!")
        print("="*70)
        return 0
    else:
        print("SOME CHECKS FAILED - Fix issues before committing")
        print("="*70)
        return 1


if __name__ == '__main__':
    target = sys.argv[1] if len(sys.argv) > 1 else "src"
    exit_code = main(target)
    sys.exit(exit_code)
