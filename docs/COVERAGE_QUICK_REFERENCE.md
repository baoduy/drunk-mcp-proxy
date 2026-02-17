# Code Coverage Quick Reference

## 📊 Viewing Coverage Reports

### Terminal Report (Quick)

```bash
./scripts/tests.sh
```

Shows coverage statistics directly in console after tests complete.

### HTML Report (Interactive)

```bash
./scripts/tests.sh --html
open htmlcov/index.html
```

Open the interactive HTML dashboard in your browser to explore coverage by file and see line-by-line highlighting.

### JSON Report (Machine-Readable)

```bash
cat coverage.json
```

Machine-readable format useful for CI/CD pipelines and data analysis.

## 🎯 Common Tasks

### Check Overall Coverage Percentage

```bash
./scripts/tests.sh | grep "TOTAL"
```

### Test Specific Module

```bash
./scripts/tests.sh -k test_auth --html
```

### View Files with Low Coverage

Open `htmlcov/index.html` and sort by coverage percentage, or check the terminal report for files < 80%.

### Measure Coverage for New Feature

```bash
./scripts/tests.sh -k "test_new_feature" --html
```

## 📈 Coverage Targets

| Target           | Current | Status       |
|------------------|---------|--------------|
| Overall          | 78.19%  | ⚠️ Fair      |
| Critical Modules | 95%+    | ✅ Good       |
| App Module       | 27-33%  | ❌ Needs Work |
| Tools Module     | 79-100% | ✅ Good       |

## 🔍 Understanding the Report

### HTML Report Features

- **Green highlight**: Covered code
- **Red highlight**: Uncovered code
- **Yellow highlight**: Partially covered (branches)
- **Numbers on left**: Line hit counts

### Coverage Metrics

- **Stmts** (Statements): Total executable statements
- **Miss**: Uncovered statements
- **Cover**: Percentage of coverage
- **Branch**: Branch coverage (if enabled)

## ⚡ Performance Tips

- Coverage measurement adds ~20-30% to test runtime
- Run without coverage for fast iteration: `pytest tests/`
- Use `--cov` only when you need the report
- For CI/CD: Use JSON output for faster parsing

## 📋 Report Artifacts

| File            | Purpose                        | Size   |
|-----------------|--------------------------------|--------|
| `.coverage`     | Coverage data (binary)         | ~1KB   |
| `coverage.json` | Coverage metrics (JSON)        | ~100KB |
| `htmlcov/`      | Interactive report (directory) | ~2MB   |
| `.coveragerc`   | Configuration file             | <1KB   |

## 🐛 Troubleshooting

### Issue: No coverage data generated

**Solution**: Run with `./scripts/tests.sh` not just `pytest`

### Issue: Some modules not in report

**Solution**: Check `.coveragerc` - source paths must match project structure

### Issue: Coverage lower than expected

**Solution**: Some code is excluded. Check `.coveragerc` for `exclude_lines`

## 🚀 Integration with CI/CD

### GitHub Actions Example

```yaml
- name: Run tests with coverage
  run: ./scripts/tests.sh --html

- name: Upload coverage
  uses: codecov/codecov-action@v3
  with:
    files: ./coverage.json
```

### Reading Coverage from JSON

```python
import json

with open('coverage.json') as f:
    data = json.load(f)
    total_coverage = data['totals']['percent_covered']
    print(f"Total Coverage: {total_coverage}%")
```

## 📚 Learn More

- Full guide: `docs/CODE_COVERAGE.md`
- Coverage.py: https://coverage.readthedocs.io/
- pytest-cov: https://pytest-cov.readthedocs.io/

---

**Pro Tip**: Bookmark `htmlcov/index.html` for quick access to detailed coverage analysis!

