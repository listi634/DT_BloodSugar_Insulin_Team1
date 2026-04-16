# Scripts Documentation

This folder contains verification and utility scripts for the GitHub Copilot workflow.

## Verification Scripts

### `verify.py` (Python - Cross-platform)
- **Usage**: `python verify.py` or `python verify.py src/file.py`
- **Platform**: Works on Windows, macOS, Linux
- **Requires**: Python 3.13+
- **Features**: Runs Black, Pylint, mypy, pytest

```bash
python verify.py              # Check all src/
python verify.py src/file.py  # Check specific file
```

### `verify.ps1` (PowerShell - Windows Recommended)
- **Usage**: `.\verify.ps1` or `.\verify.ps1 -Target "src/file.py"`
- **Platform**: Windows only
- **Requires**: PowerShell 5.0+
- **Features**: Color-coded output, better error reporting

```powershell
.\verify.ps1                          # Check all src/
.\verify.ps1 -Target "src/file.py"   # Check specific file
Get-Help .\verify.ps1                # Show help
```

### `verify.bat` (Batch - Windows Legacy)
- **Usage**: `verify.bat` or `verify.bat src/file.py`
- **Platform**: Windows (Command Prompt/Git Bash)
- **Requires**: Windows 7+
- **Features**: Works in legacy environments

```cmd
verify.bat              # Check all src/
verify.bat src/file.py  # Check specific file
```

---

## Which Script Should I Use?

**Recommendation Order**:

1. **Windows + PowerShell** → Use `verify.ps1` (best experience)
2. **Windows + Command Prompt** → Use `verify.bat` (simple & reliable)
3. **Linux/macOS** → Use `verify.py` (cross-platform)
4. **Need to script** → Use `verify.py` (easiest to integrate)

---

## Tool Pipeline

All scripts run in this order:

```
1. Black        (Auto-formatter)
   ↓
2. Pylint       (Linter)
   ↓
3. mypy         (Type checker)
   ↓
4. pytest       (Test runner)
```

If any step fails, you should fix it before committing.

---

## Exit Codes

- `0` - All checks passed ✅
- `1` - One or more checks failed ❌

---

## Detailed Documentation

See `.github/VERIFICATION_SETUP.md` for:
- Installation instructions
- Understanding each tool
- Troubleshooting guide
- Advanced usage

See `.github/copilot-instructions.md` for:
- Code style standards
- Quick start guide
- Prompting best practices
