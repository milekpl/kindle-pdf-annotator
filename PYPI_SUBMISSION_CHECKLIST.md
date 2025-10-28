# PyPI Submission Checklist

Use this checklist when preparing to submit to PyPI.

## Pre-Submission Verification

### Code Quality
- [ ] All tests passing: `pytest tests/ -v`
- [ ] No syntax errors: `python -m compileall src/`
- [ ] Code follows project conventions
- [ ] No debug print statements or TODO comments in production code

### Documentation
- [ ] README.md is up to date
- [ ] CHANGELOG.md has entry for this version
- [ ] All docstrings are complete
- [ ] Examples work correctly

### Version Management
- [ ] Version bumped in `src/kindle_pdf_annotator/__init__.py`
- [ ] Version bumped in `pyproject.toml`
- [ ] Version follows semantic versioning (X.Y.Z)
- [ ] CHANGELOG.md updated with version changes

### Clean Build
- [ ] Removed old artifacts: `rm -rf build/ dist/ *.egg-info src/*.egg-info`
- [ ] Built fresh package: `python3 -m build`
- [ ] Verified build output (no errors)
- [ ] Package size reasonable (< 1MB for this project)

### Package Validation
- [ ] Twine check passed: `python3 -m twine check dist/*`
- [ ] No missing dependencies
- [ ] Console scripts defined correctly
- [ ] Entry points work

### Package Contents
- [ ] Wheel file created: `dist/*.whl`
- [ ] Source distribution created: `dist/*.tar.gz`
- [ ] Package includes LICENSE
- [ ] Package includes README.md
- [ ] Package includes AUTHORS

## TestPyPI Submission

### Upload
- [ ] TestPyPI account created
- [ ] API token generated for TestPyPI
- [ ] Uploaded to TestPyPI: `python3 -m twine upload --repository testpypi dist/*`
- [ ] Upload successful (no errors)

### Testing
- [ ] Created test virtual environment
- [ ] Installed from TestPyPI successfully
- [ ] CLI command works: `kindle-pdf-annotator --help`
- [ ] GUI command works: `kindle-pdf-annotator-gui`
- [ ] Can import package: `python -c "import kindle_pdf_annotator"`
- [ ] Version correct: `python -c "from kindle_pdf_annotator import __version__; print(__version__)"`
- [ ] All features work as expected

### TestPyPI Verification
- [ ] Package page looks correct: https://test.pypi.org/project/kindle-pdf-annotator/
- [ ] README renders properly
- [ ] Metadata is accurate
- [ ] Links work
- [ ] License displayed correctly

## PyPI Submission

### Final Checks
- [ ] TestPyPI testing completed successfully
- [ ] All issues from TestPyPI resolved
- [ ] PyPI account created
- [ ] API token generated for PyPI
- [ ] Double-checked version number (cannot reuse versions!)

### Upload
- [ ] Uploaded to PyPI: `python3 -m twine upload dist/*`
- [ ] Upload successful (no errors)
- [ ] Package page accessible: https://pypi.org/project/kindle-pdf-annotator/

### PyPI Verification
- [ ] Package metadata correct
- [ ] README renders properly
- [ ] Can install: `pip install kindle-pdf-annotator`
- [ ] Console scripts work after installation
- [ ] Documentation links work

## Post-Release

### Git
- [ ] Committed all changes: `git add . && git commit -m "Release v1.0.0"`
- [ ] Tagged release: `git tag v1.0.0`
- [ ] Pushed commits: `git push origin main`
- [ ] Pushed tags: `git push origin v1.0.0`

### GitHub
- [ ] Created GitHub Release
- [ ] Release title: "Version 1.0.0"
- [ ] Release notes from CHANGELOG.md
- [ ] Attached wheel file
- [ ] Attached source tarball
- [ ] Published release

### Testing Production Install
- [ ] Fresh virtual environment created
- [ ] Installed from PyPI: `pip install kindle-pdf-annotator`
- [ ] CLI works: `kindle-pdf-annotator --help`
- [ ] GUI works: `kindle-pdf-annotator-gui`
- [ ] Can process sample data successfully

### Communication
- [ ] Updated README badges (if applicable)
- [ ] Announced on GitHub Discussions
- [ ] Posted on social media (optional)
- [ ] Notified interested users

## Troubleshooting

### Common Issues

**Build fails:**
- Check for syntax errors
- Verify all imports work
- Check pyproject.toml syntax

**Upload fails with 403:**
- Verify API token permissions
- Check token is for correct service (PyPI vs TestPyPI)

**Upload fails with 400:**
- Version already exists (bump version)
- Invalid package metadata

**Install fails:**
- Check dependencies are available on PyPI
- Verify Python version compatibility
- Check package name spelling

**Console scripts don't work:**
- Verify entry_points in pyproject.toml
- Check script names
- Reinstall package

## Quick Commands Reference

```bash
# Clean build
rm -rf build/ dist/ *.egg-info src/*.egg-info

# Build package
python3 -m build

# Check package
python3 -m twine check dist/*

# Upload to TestPyPI
python3 -m twine upload --repository testpypi dist/*

# Upload to PyPI
python3 -m twine upload dist/*

# Create git tag
git tag v1.0.0
git push origin v1.0.0
```

## Notes

- Version X.Y.Z where:
  - X = Major (breaking changes)
  - Y = Minor (new features, backward compatible)
  - Z = Patch (bug fixes)

- Cannot re-upload same version to PyPI
- Always test on TestPyPI first
- Keep API tokens secure
- Document all changes in CHANGELOG.md

---
Last updated: 2025-10-26
