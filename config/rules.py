"""
Cleaning and validation rules for survey data preprocessing.
"""

# ============================================================
# MISSING VALUE REPRESENTATIONS
# ============================================================

# Strings that should be treated as missing/NA values
MISSING_VALUES = [
    "",
    "n/a",
    "na",
    "nan",
    "null",
    "none",
    "-",
    "--",
    ".",
    "không trả lời",
    "khong tra loi",
    "không có",
    "bỏ trống",
    "bo trong",
    "không biết",
    "khong biet",
    "chưa trả lời",
    "chua tra loi",
    "không áp dụng",
    "không xác định",
    "missing",
    "no answer",
    "no response",
    "not applicable",
    "not available",
    "undefined",
    "unknown",
]

# ============================================================
# VALIDATION THRESHOLDS
# ============================================================

# If a column has more than this ratio of missing values → suggest dropping
MISSING_THRESHOLD_DROP = 0.50

# If a column has more than this ratio of missing values → warning
MISSING_THRESHOLD_WARN = 0.20

# If a respondent has more than this ratio of missing values → suggest dropping
RESPONDENT_MISSING_THRESHOLD = 0.50

# Minimum number of rows required for analysis
MIN_ROWS = 10

# Minimum number of valid (non-null) values per column for analysis
MIN_VALID_PER_COLUMN = 5

# ============================================================
# OUTLIER DETECTION
# ============================================================

# IQR multiplier for outlier detection
IQR_MULTIPLIER = 1.5

# Z-score threshold for outlier flagging
ZSCORE_THRESHOLD = 3.0

# ============================================================
# COLUMN TYPE DETECTION HEURISTICS
# ============================================================

# Maximum unique values for a column to be considered categorical
MAX_UNIQUE_CATEGORICAL = 20

# If column name contains these keywords → likely demographic
DEMOGRAPHIC_KEYWORDS_VI = [
    "giới tính", "gioi tinh", "tuổi", "tuoi", "nghề", "nghe",
    "trình độ", "trinh do", "học vấn", "hoc van",
    "thu nhập", "thu nhap", "nơi ở", "noi o", "địa chỉ", "dia chi",
    "tỉnh", "tinh", "thành phố", "thanh pho",
    "năm sinh", "nam sinh", "lớp", "lop", "khoa", "trường", "truong",
    "chuyên ngành", "chuyen nganh", "dân tộc", "dan toc",
    "tôn giáo", "ton giao", "tình trạng", "tinh trang",
    "số điện thoại", "email", "mã", "ma", "stt",
]

DEMOGRAPHIC_KEYWORDS_EN = [
    "gender", "sex", "age", "occupation", "education",
    "income", "address", "city", "province", "state", "country",
    "birth", "class", "department", "faculty", "school", "university",
    "major", "ethnicity", "religion", "marital", "status",
    "phone", "email", "id", "stt", "no.", "number",
]

# If column name contains these keywords → likely an ID column (skip analysis)
ID_KEYWORDS = [
    "stt", "id", "mã", "ma", "số thứ tự", "so thu tu",
    "respondent", "response_id", "timestamp", "thời gian", "ngày",
]

# ============================================================
# TEXT NORMALIZATION
# ============================================================

# Unicode normalization form
UNICODE_FORM = "NFC"

# Whether to convert text to lowercase during normalization
NORMALIZE_LOWERCASE = True

# Whether to strip leading/trailing whitespace
NORMALIZE_STRIP = True

# Whether to collapse multiple spaces into one
NORMALIZE_COLLAPSE_SPACES = True
