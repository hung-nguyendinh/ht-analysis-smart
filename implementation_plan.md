# Phase 1: Input + Preprocessing Pipeline — Survey Data Analysis App

Xây dựng pipeline xử lý dữ liệu khảo sát ngôn ngữ, thay thế SPSS, với khả năng xử lý input thông minh (auto-detect Likert scale, clean text responses, validate data).

## Proposed Changes

### Project Setup

#### [NEW] [requirements.txt](file:///d:/Projects/HT_Analysis_Smart/requirements.txt)
- Dependencies: `streamlit`, `pandas`, `numpy`, `openpyxl`, `scipy`, `pingouin`, `chardet`

---

### Config Layer

#### [NEW] [likert_mapping.py](file:///d:/Projects/HT_Analysis_Smart/config/likert_mapping.py)
- Định nghĩa mapping Likert scales phổ biến (Vietnamese & English)
- 5-point: "Hoàn toàn không đồng ý" → 1, ..., "Hoàn toàn đồng ý" → 5
- 7-point scale, Yes/No, frequency scales
- Auto-detect function: nhận column values → trả mapping phù hợp

#### [NEW] [rules.py](file:///d:/Projects/HT_Analysis_Smart/config/rules.py)
- Cleaning rules: strip whitespace, normalize Unicode (NFC), case normalization
- Validation rules: min/max values per scale type, required columns, missing threshold (>50% → drop)

---

### Models Layer

#### [NEW] [data_schema.py](file:///d:/Projects/HT_Analysis_Smart/models/data_schema.py)
- `SurveyData` dataclass: holds DataFrame + metadata (column types, scales detected, issues found)
- `ColumnInfo`: per-column metadata (name, detected_type, scale, mapping, missing_count)
- `ValidationResult`: holds validation pass/fail + list of issues

---

### Utils Layer

#### [NEW] [logger.py](file:///d:/Projects/HT_Analysis_Smart/utils/logger.py)
- Structured logging with Python `logging` module
- File + console handlers, Vietnamese-friendly formatting

#### [NEW] [helpers.py](file:///d:/Projects/HT_Analysis_Smart/utils/helpers.py)
- `normalize_text()`: strip, lower, NFC normalize
- `detect_encoding()`: dùng `chardet` để detect file encoding
- `safe_convert_numeric()`: convert text → numeric, handle errors gracefully

---

### Services Layer (Core Phase 1)

#### [NEW] [data_loader.py](file:///d:/Projects/HT_Analysis_Smart/services/data_loader.py)
- Load `.csv`, `.xlsx`, `.xls` files
- Auto-detect encoding (UTF-8, UTF-16, Windows-1252, etc.) dùng `chardet`
- Auto-detect header row (skip metadata rows phía trên)
- Return raw DataFrame + file metadata

#### [NEW] [validator.py](file:///d:/Projects/HT_Analysis_Smart/services/validator.py)
- Validate loaded data:
  - Check empty DataFrame
  - Check duplicate column names
  - Check missing value thresholds
  - Check data type consistency per column
  - Check suspicious patterns (all same value, sequential IDs in answer columns)
- Return `ValidationResult` with categorized issues (error/warning/info)

#### [NEW] [preprocessing.py](file:///d:/Projects/HT_Analysis_Smart/services/preprocessing.py)
- ⭐ **CORE MODULE** — Pipeline xử lý thông minh:
  1. **Text normalization**: strip, NFC normalize, case handling
  2. **Likert auto-mapping**: detect text Likert responses → convert to numeric using `likert_mapping.py`
  3. **Missing value handling**: detect various NA representations ("", "N/A", "Không trả lời", etc.)
  4. **Outlier flagging**: flag values outside expected range per scale
  5. **Column type inference**: demographic vs. Likert vs. open-ended vs. numeric
  6. **Pipeline orchestrator**: `preprocess_pipeline(df)` → runs all steps in order, returns cleaned `SurveyData`

#### [NEW] [suggestion.py](file:///d:/Projects/HT_Analysis_Smart/services/suggestion.py)
- (Stub for Phase 3) — chỉ tạo interface cơ bản

---

### Entry Point

#### [NEW] [main.py](file:///d:/Projects/HT_Analysis_Smart/main.py)
- Minimal Streamlit entry point (stub for Phase 4)
- Import check to verify all modules load correctly

---

### Tests

#### [NEW] [test_preprocessing.py](file:///d:/Projects/HT_Analysis_Smart/tests/test_preprocessing.py)
- Test Likert auto-detection (Vietnamese & English labels)
- Test text normalization
- Test missing value detection
- Test column type inference
- Test full pipeline with sample survey data
- Test edge cases: empty DataFrame, all-missing column, mixed types

## Verification Plan

### Automated Tests
```bash
cd d:\Projects\HT_Analysis_Smart
python -m pytest tests/test_preprocessing.py -v
```

### Manual Verification
- Chạy test script riêng để load một file Excel mẫu (tự tạo) và verify output preprocessing pipeline
```bash
cd d:\Projects\HT_Analysis_Smart
python -c "from services.data_loader import load_file; from services.preprocessing import preprocess_pipeline; print('All imports OK')"
```
