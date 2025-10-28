# TODO - Future Development

## Potential Improvements

### Code Quality
- [x] ~~Consider removing `pdt_parser.py` if confirmed that PDT files never contain useful annotation data~~ (Removed October 28, 2025)
- [x] ~~Review and potentially remove unused legacy test code in `test_parsers.py`~~ (Removed PDT parser tests October 28, 2025 - remaining tests are active)
- [ ] Add more edge case tests for multi-column PDF layouts

### Features
- [ ] Add support for exporting annotations to other formats (JSON, CSV, etc.) via CLI
- [ ] Improve error messages for common user mistakes
- [ ] Add progress indicators for large PDF processing

### Testing
- [ ] Expand test coverage for different Kindle device versions
- [ ] Add integration tests with sample PDFs from newer Kindle models
- [ ] Performance testing with very large PDFs (1000+ pages)

### Documentation
- [ ] Add troubleshooting guide for common issues
- [ ] Create video tutorial for GUI usage
- [ ] Document coordinate system validation methodology

### Compatibility
- [ ] Test with Kindle Scribe annotations
- [ ] Verify compatibility with latest Kindle firmware
- [ ] Add support for newer Kindle annotation formats if needed

## Completed (Historical Reference)

For historical context on completed work, see:
- `docs/COORDINATE_SYSTEM.md` - Coordinate conversion implementation
- `docs/VALIDATION_SUMMARY.md` - Validation results
- `CHANGELOG.md` - Version history
- Git commit history for detailed implementation notes

---
Last updated: October 28, 2025
