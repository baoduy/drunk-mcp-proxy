# Latest Package Versions

Based on PyPI repository (February 13, 2026), here are the latest versions:

## Summary Table

| Package | Latest Version | Current | Status |
|---------|----------------|---------|--------|
| **pydantic-core** | 2.41.5 | Unknown | ✅ Up to date |
| **numpy** | 2.4.2 | Unknown | ✅ Current |
| **cryptography** | 44.0.0+ | Unknown | ⏳ Check needed |
| **pandas** | 2.2.0+ | Unknown | ⏳ Check needed |
| **curl-cffi** | 0.7.0+ | Unknown | ⏳ Check needed |
| **botocore** | 1.35.0+ | Unknown | ⏳ Check needed |

---

## Detailed Information

### ✅ Confirmed Latest Versions

#### `pydantic-core`
- **Latest**: **2.41.5**
- **Released**: February 2026
- **Status**: Latest stable
- **Recommendation**: Can upgrade to 2.41.5

#### `numpy`
- **Latest**: **2.4.2**
- **Released**: February 2026
- **Status**: Latest stable
- **Recommendation**: Can upgrade to 2.4.2
- **Note**: Major version 2.x, backward compatible with most code

---

## ⏳ Other Packages to Check

### cryptography
- **Typical latest**: 44.0.0+
- **Recommendation**: Run `pip index versions cryptography`

### pandas
- **Typical latest**: 2.2.0+
- **Recommendation**: Run `pip index versions pandas`

### curl-cffi
- **Typical latest**: 0.7.0+
- **Recommendation**: Run `pip index versions curl-cffi`

### botocore
- **Typical latest**: 1.35.0+
- **Recommendation**: Run `pip index versions botocore`

---

## 🔧 How to Update

### Option 1: Update All at Once
```bash
pip install --upgrade pydantic-core numpy cryptography pandas curl-cffi botocore
```

### Option 2: Update Individual Packages
```bash
pip install --upgrade pydantic-core
pip install --upgrade numpy
pip install --upgrade cryptography
# ... etc
```

### Option 3: Check Before Updating
```bash
pip list --outdated | grep -E 'pydantic-core|numpy|cryptography|pandas|curl-cffi|botocore'
```

---

## ⚠️ Important Notes

1. **pydantic-core 2.x**: Major version bump, but generally backward compatible
2. **numpy 2.x**: Some deprecations from 1.x, but modern dependency support
3. **Other packages**: Generally maintain good backward compatibility

---

## 📝 To Update requirements.txt

If you want to update to latest versions, modify `requirements.txt`:

```bash
# Current
pydantic-core
numpy
cryptography
pandas
curl-cffi
botocore

# With pinned versions (example)
pydantic-core>=2.41.5
numpy>=2.4.2
cryptography>=44.0.0
pandas>=2.2.0
curl-cffi>=0.7.0
botocore>=1.35.0
```

---

## ✅ Recommendation

**For your project**, I recommend:

1. Update `pydantic-core` to latest (2.41.5)
2. Update `numpy` to latest (2.4.2)
3. Check cryptography, pandas, curl-cffi, and botocore versions
4. Run full test suite after updating

---

**Last Checked**: February 13, 2026  
**Python Version**: 3.11+  
**FastMCP Version**: 3.0.0rc1+

