# PowerShell verification script for Windows
# Usage: .\verify.ps1 [optional target path]

param(
    [string]$Target = "src"
)

Write-Host ""
Write-Host "========================================================================"
Write-Host "    GITHUB COPILOT CODE VERIFICATION"
Write-Host "    DT_BloodSugar_Insulin_Team1"
Write-Host "========================================================================"
Write-Host ""

$script:results = @{
    "Black"  = $false
    "Pylint" = $false
    "mypy"   = $false
    "Tests"  = $true
}

# Helper function to run a tool
function Run-Check {
    param(
        [string]$Tool,
        [array]$Command,
        [string]$Description
    )
    
    Write-Host ""
    Write-Host ("^" * 70)
    Write-Host "[STEP] $Description"
    Write-Host ("^" * 70)
    Write-Host "Running: $($Command -join ' ')"
    Write-Host ""
    
    try {
        & $Command[0] $Command[1..($Command.Length-1)] | Tee-Object -Variable output
        if ($LASTEXITCODE -eq 0) {
            Write-Host "[OK] $Tool completed successfully"
            return $true
        } else {
            Write-Host "[FAILED] $Tool reported issues (exit code: $LASTEXITCODE)"
            return $false
        }
    } catch {
        Write-Host "[ERROR] Could not run $Tool"
        Write-Host "  $_"
        Write-Host "  Install with: pipenv install --dev"
        return $false
    }
}

# Step 1: Black
Write-Host ""
Write-Host ("=" * 70)
$script:results["Black"] = Run-Check `
    "Black" `
    @("black", $Target, "--line-length=79") `
    "1. AUTO-FORMATTING WITH BLACK"

# Step 2: Pylint
Write-Host ""
Write-Host ("=" * 70)
$script:results["Pylint"] = Run-Check `
    "Pylint" `
    @("pylint", $Target, "--rcfile=.pylintrc") `
    "2. LINTING WITH PYLINT"

# Step 3: mypy
Write-Host ""
Write-Host ("=" * 70)
$script:results["mypy"] = Run-Check `
    "mypy" `
    @("mypy", $Target, "--strict") `
    "3. TYPE CHECKING WITH MYPY"

# Step 4: Tests
if (Test-Path "tests") {
    Write-Host ""
    Write-Host ("=" * 70)
    $script:results["Tests"] = Run-Check `
        "pytest" `
        @("pytest", "tests/", "-v", "--tb=short") `
        "4. RUNNING TESTS"
} else {
    Write-Host ""
    Write-Host "[SKIP] No tests directory found"
    $script:results["Tests"] = $true
}

# Print summary
Write-Host ""
Write-Host "========================================================================"
Write-Host "VERIFICATION SUMMARY"
Write-Host "========================================================================"

foreach ($tool in $script:results.Keys) {
    $status = if ($script:results[$tool]) { "PASSED" } else { "FAILED" }
    Write-Host ("{0,-12} {1}" -f $tool, $status)
}

Write-Host "========================================================================"

$allPassed = $script:results.Values | Where-Object { -not $_ } | Measure-Object | Select-Object -ExpandProperty Count
if ($allPassed -eq 0) {
    Write-Host "ALL CHECKS PASSED - Code is ready for commit!"
    Write-Host "========================================================================"
    exit 0
} else {
    Write-Host "SOME CHECKS FAILED - Fix issues before committing"
    Write-Host "========================================================================"
    exit 1
}
