# PyPI Release Guide

This document provides step-by-step instructions for building, testing, and releasing `kindle-pdf-annotator` to PyPI.

## Quick Start (Automated Scripts)

**For most releases, use the automated scripts:**

```bash
# 1. Release to TestPyPI (patch version bump: 1.0.1 -> 1.0.2)
./release.sh patch testpypi

# 2. Push to GitHub so screenshots work
git push origin main
git push origin v1.0.2

# 3. Test the package
./test_package.sh 1.0.2

# 4. If all tests pass, release to production PyPI
./release.sh patch pypi
git push origin main
git push origin v1.0.3
```

See [Automated Release Scripts](#automated-release-scripts) section below for details.

## Prerequisites

1. **PyPI Account**: Create accounts on both [PyPI](https://pypi.org) and [TestPyPI](https://test.pypi.org)
2. **API Tokens**: Generate API tokens for both PyPI and TestPyPI
   - PyPI: https://pypi.org/manage/account/token/
   - TestPyPI: https://test.pypi.org/manage/account/token/
3. **Required Tools**: Install build and upload tools
   ```bash
   pip install --upgrade build twine
   ```

## Package Structure

The package follows modern Python packaging standards (PEP 517/621):

```
kindle-pdf-annotator/
├── src/kindle_pdf_annotator/    # Main package
│   ├── __init__.py             # Version and metadata
│   ├── cli.py                  # CLI entry point
│   ├── main.py                 # GUI entry point
│   ├── gui/                    # GUI modules
│   ├── kindle_parser/          # Kindle parsing modules
│   ├── pdf_processor/          # PDF annotation modules
│   └── utils/                  # Utility modules
├── pyproject.toml              # Modern package configuration (PEP 621)
├── setup.py                    # Backward compatibility
├── MANIFEST.in                 # Package data inclusion rules
├── README.md                   # Package description
├── LICENSE                     # GPL-3.0-or-later license
├── AUTHORS                     # Contributors list
├── CHANGELOG.md                # Version history
└── requirements.txt            # Dependencies
```

## Version Management

Version is defined in two locations (must be kept in sync):
1. `src/kindle_pdf_annotator/__init__.py` - `__version__` variable
2. `pyproject.toml` - `version` field

**Automated version bumping** (recommended):
```bash
# Use the release script to automatically bump version
./release.sh patch testpypi   # 1.0.1 -> 1.0.2
./release.sh minor testpypi   # 1.0.2 -> 1.1.0
./release.sh major testpypi   # 1.1.0 -> 2.0.0
```

**Manual version bumping**:
1. Update `__version__` in `src/kindle_pdf_annotator/__init__.py`
2. Update `version` in `pyproject.toml`
3. Add entry to `CHANGELOG.md`
4. Commit changes: `git commit -am "Bump version to X.Y.Z"`
5. Tag release: `git tag vX.Y.Z`

## Automated Release Scripts

Two shell scripts are provided to automate the release and testing process:

### `release.sh` - Automated Release

**Usage:**
```bash
./release.sh [patch|minor|major] [testpypi|pypi]
```

**Examples:**
```bash
# Patch release to TestPyPI (default)
./release.sh

# Minor release to TestPyPI
./release.sh minor testpypi

# Patch release directly to PyPI
./release.sh patch pypi
```

**What it does:**
1. ✓ Calculates and updates version in both `__init__.py` and `pyproject.toml`
2. ✓ Runs tests (if pytest is available)
3. ✓ Cleans old build artifacts
4. ✓ Builds the package
5. ✓ Validates with twine check
6. ✓ Uploads to TestPyPI or PyPI
7. ✓ Commits changes to git
8. ✓ Creates version tag
9. ✓ Shows next steps for pushing

**Features:**
- Color-coded output (green = success, yellow = warning, red = error)
- Interactive confirmation before release
- Automatic rollback on failure
- Clear next-step instructions

### `test_package.sh` - Package Testing

**Usage:**
```bash
./test_package.sh [version]
```

**Examples:**
```bash
# Test latest version from current __init__.py
./test_package.sh

# Test specific version
./test_package.sh 1.0.2
```

**What it does:**
1. ✓ Creates isolated test environment in /tmp
2. ✓ Creates fresh virtual environment
3. ✓ Installs from TestPyPI (with PyPI fallback for dependencies)
4. ✓ Tests imports work
5. ✓ Verifies version matches
6. ✓ Tests CLI command (`kindle-pdf-annotator --help`)
7. ✓ Verifies GUI command exists
8. ✓ Tests core module imports
9. ✓ Cleans up test environment automatically
10. ✓ Shows next steps

**Features:**
- Fully isolated testing (doesn't affect your environment)
- Automatic cleanup on success or failure
- Comprehensive validation
- Clear success/failure reporting

### Complete Release Workflow

```bash
# 1. Make your code changes and commit them
git add .
git commit -m "Add new feature"

# 2. Release to TestPyPI for testing
./release.sh patch testpypi

# 3. Push to GitHub (required for README screenshots to work)
git push origin main
git push origin v1.0.2

# 4. Wait a minute for GitHub to update, then test
./test_package.sh 1.0.2

# 5. Check TestPyPI page for README rendering
#    https://test.pypi.org/project/kindle-pdf-annotator/

# 6. If everything looks good, release to production PyPI
./release.sh patch pypi

# 7. Push the new version
git push origin main
git push origin v1.0.3

# 8. Create GitHub Release (see Post-Release Tasks)
```

## Manual Build Process

If you prefer manual control or the scripts don't work for your use case:

## Manual Build Process

If you prefer manual control or the scripts don't work for your use case:

### Clean Previous Builds

```bash
# Remove old build artifacts
rm -rf build/ dist/ src/*.egg-info
```

### Build Distribution Files

```bash
# Build both wheel and source distribution
python -m build

# This creates:
# - dist/kindle_pdf_annotator-X.Y.Z-py3-none-any.whl (wheel)
# - dist/kindle_pdf_annotator-X.Y.Z.tar.gz (source)
```

### Verify Package

```bash
# Check package with twine
python -m twine check dist/*

# Expected output: PASSED for both files
```

## Testing the Package

### Test on TestPyPI First

```bash
# Upload to TestPyPI
python -m twine upload --repository testpypi dist/*

# You'll be prompted for:
# Username: __token__
# Password: <your-testpypi-token>
```

### Install from TestPyPI

```bash
# Create a test environment
python -m venv test-env
source test-env/bin/activate  # On Windows: test-env\Scripts\activate

# Install from TestPyPI
pip install --index-url https://test.pypi.org/simple/ \
    --extra-index-url https://pypi.org/simple/ \
    kindle-pdf-annotator

# Test the CLI
kindle-pdf-annotator --help

# Test the GUI
kindle-pdf-annotator-gui

# Test importing
python -c "from kindle_pdf_annotator import __version__; print(__version__)"

# Deactivate and cleanup
deactivate
rm -rf test-env
```

## Publishing to PyPI

### Upload to PyPI (Production)

```bash
# Upload to PyPI
python -m twine upload dist/*

# You'll be prompted for:
# Username: __token__
# Password: <your-pypi-token>
```

### Verify on PyPI

Visit https://pypi.org/project/kindle-pdf-annotator/ to verify:
- Package metadata (description, author, license)
- README rendering
- Dependencies
- Download links

### Install from PyPI

```bash
# Test installation from PyPI
pip install kindle-pdf-annotator

# Or with dev dependencies
pip install kindle-pdf-annotator[dev]
```

## Configuration File (.pypirc)

Optionally, create `~/.pypirc` to avoid entering credentials each time:

```ini
[distutils]
index-servers =
    pypi
    testpypi

[pypi]
username = __token__
password = <your-pypi-token>

[testpypi]
repository = https://test.pypi.org/legacy/
username = __token__
password = <your-testpypi-token>
```

**Security Note**: Keep `.pypirc` secure (chmod 600) and never commit it to git.

## Post-Release Tasks

1. **Git Tag**: Create and push git tag
   ```bash
   git tag vX.Y.Z
   git push origin vX.Y.Z
   ```

2. **GitHub Release**: Create a GitHub release with:
   - Tag: vX.Y.Z
   - Title: Version X.Y.Z
   - Description: Copy from CHANGELOG.md
   - Attach: dist/*.whl and dist/*.tar.gz

3. **Announcement**: Announce on:
   - GitHub Discussions
   - Social media (use docs/ announcements as templates)
   - Relevant communities

## Troubleshooting

### Build Failures

```bash
# Check for syntax errors
python -m compileall src/

# Run tests before building
pytest tests/

# Check for missing dependencies
pip install -e .
```

### Upload Failures

- **403 Forbidden**: Check API token has upload permissions
- **400 Bad Request**: 
  - Version already exists (bump version number)
  - **Important**: Even after deleting a release from TestPyPI, you cannot reuse the same version number due to security restrictions
  - Solution: Always increment the version number
- **File already exists**: Cannot re-upload same version (increment version)

### Screenshot/Image Issues on TestPyPI

If screenshots show "bad url scheme" errors:
- Images must be hosted externally (GitHub, not in the package)
- Use absolute URLs: `https://raw.githubusercontent.com/USER/REPO/main/screenshot.png`
- **Important**: Push changes to GitHub BEFORE screenshots will display on TestPyPI/PyPI
- TestPyPI has stricter security than production PyPI

### Import Errors After Installation

```bash
# Verify package structure
pip show kindle-pdf-annotator
pip show -f kindle-pdf-annotator  # Show all files

# Check console scripts
which kindle-pdf-annotator
kindle-pdf-annotator --help
```

## Release Checklist

**Automated (using release.sh):**
- [ ] Make and commit code changes
- [ ] Run: `./release.sh patch testpypi`
- [ ] Push to GitHub: `git push origin main && git push origin vX.Y.Z`
- [ ] Wait 1 minute for GitHub to update
- [ ] Test: `./test_package.sh X.Y.Z`
- [ ] Check TestPyPI page for README/screenshots
- [ ] If all good: `./release.sh patch pypi`
- [ ] Push: `git push origin main && git push origin vX.Y.Z`
- [ ] Create GitHub Release

**Manual (if not using scripts):**
- [ ] All tests passing: `pytest tests/ -v`
- [ ] Version bumped in `__init__.py` and `pyproject.toml`
- [ ] CHANGELOG.md updated
- [ ] README.md up to date
- [ ] Clean build: `rm -rf build/ dist/ *.egg-info src/*.egg-info`
- [ ] Build package: `python -m build`
- [ ] Verify package: `python -m twine check dist/*`
- [ ] Test on TestPyPI first
- [ ] Upload to PyPI: `python -m twine upload dist/*`
- [ ] Verify on pypi.org
- [ ] Create git tag and GitHub release
- [ ] Test installation: `pip install kindle-pdf-annotator`
- [ ] Test console scripts work
- [ ] Post announcement

## Continuous Integration (Optional)

Consider setting up GitHub Actions for automated:
- Testing on pull requests
- Building on tags
- Publishing to PyPI on release

Example workflow in `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [published]

jobs:
  build-and-publish:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.10'
      - name: Install build tools
        run: pip install build twine
      - name: Build package
        run: python -m build
      - name: Publish to PyPI
        env:
          TWINE_USERNAME: __token__
          TWINE_PASSWORD: ${{ secrets.PYPI_API_TOKEN }}
        run: python -m twine upload dist/*
```

## Additional Resources

- [Python Packaging Guide](https://packaging.python.org/)
- [PyPI Documentation](https://pypi.org/help/)
- [TestPyPI Documentation](https://test.pypi.org/help/)
- [PEP 621 - Pyproject.toml](https://peps.python.org/pep-0621/)
- [Twine Documentation](https://twine.readthedocs.io/)
- [Semantic Versioning](https://semver.org/)
- [TestPyPI File Name Reuse Policy](https://test.pypi.org/help/#file-name-reuse)

## Common Pitfalls

1. **Forgetting to push to GitHub before checking TestPyPI**: Screenshots won't load until GitHub has the files
2. **Reusing version numbers on TestPyPI**: Once uploaded (even if deleted), a version number cannot be reused
3. **Not testing on TestPyPI first**: Always test before releasing to production PyPI
4. **Mixing relative and absolute paths in README**: Use absolute GitHub URLs for all images
5. **Not updating both version locations**: Keep `__init__.py` and `pyproject.toml` in sync
6. **Forgetting to push tags**: Tags must be pushed separately: `git push origin vX.Y.Z`

## Tips for Success

- Use the automated scripts (`release.sh` and `test_package.sh`) - they handle most edge cases
- Always increment version numbers, even for TestPyPI-only releases
- Test the TestPyPI package in a fresh environment before releasing to PyPI
- Wait a minute after pushing to GitHub before checking if screenshots load
- Keep a .pypirc file with tokens to avoid entering credentials each time
- Use semantic versioning consistently
- Document all changes in CHANGELOG.md before releasing
