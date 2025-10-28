# PyPI Release Guide

This document provides step-by-step instructions for building, testing, and releasing `kindle-pdf-annotator` to PyPI.

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

Version is defined in a single location: `src/kindle_pdf_annotator/__init__.py`

To bump the version:
1. Update `__version__` in `src/kindle_pdf_annotator/__init__.py`
2. Update `version` in `pyproject.toml`
3. Add entry to `CHANGELOG.md`
4. Commit changes: `git commit -am "Bump version to X.Y.Z"`
5. Tag release: `git tag vX.Y.Z`

## Building the Package

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
- **400 Bad Request**: Version already exists (bump version)
- **File already exists**: Cannot re-upload same version (increment version)

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

- [ ] All tests passing: `pytest tests/ -v`
- [ ] Version bumped in `__init__.py` and `pyproject.toml`
- [ ] CHANGELOG.md updated
- [ ] README.md up to date
- [ ] Clean build: `rm -rf build/ dist/ *.egg-info`
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
- [PEP 621 - Pyproject.toml](https://peps.python.org/pep-0621/)
- [Twine Documentation](https://twine.readthedocs.io/)
- [Semantic Versioning](https://semver.org/)
