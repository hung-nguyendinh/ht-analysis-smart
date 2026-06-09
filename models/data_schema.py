"""
Data schema models for survey data.
"""
from dataclasses import dataclass, field
from typing import Optional
from enum import Enum

import pandas as pd


class ColumnType(Enum):
    """Detected column type."""
    DEMOGRAPHIC = "demographic"
    LIKERT = "likert"
    NUMERIC = "numeric"
    CATEGORICAL = "categorical"
    OPEN_ENDED = "open_ended"
    ID = "id"
    UNKNOWN = "unknown"


class IssueSeverity(Enum):
    """Severity of a data quality issue."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ColumnInfo:
    """Per-column metadata after analysis."""
    name: str
    original_dtype: str
    detected_type: ColumnType = ColumnType.UNKNOWN
    scale_name: Optional[str] = None
    scale_points: Optional[int] = None
    mapping_used: Optional[dict] = None
    missing_count: int = 0
    missing_ratio: float = 0.0
    unique_count: int = 0
    is_converted: bool = False  # True if text → numeric conversion applied

    def to_dict(self):
        return {
            "name": self.name,
            "original_dtype": self.original_dtype,
            "detected_type": self.detected_type.value,
            "scale_name": self.scale_name,
            "scale_points": self.scale_points,
            "missing_count": self.missing_count,
            "missing_ratio": round(self.missing_ratio, 4),
            "unique_count": self.unique_count,
            "is_converted": self.is_converted,
        }


@dataclass
class DataIssue:
    """A single data quality issue."""
    severity: IssueSeverity
    column: Optional[str]  # None for row-level or dataset-level issues
    row: Optional[int]     # None for column-level or dataset-level issues
    message: str
    suggestion: str = ""

    def to_dict(self):
        return {
            "severity": self.severity.value,
            "column": self.column,
            "row": self.row,
            "message": self.message,
            "suggestion": self.suggestion,
        }


@dataclass
class ValidationResult:
    """Result of data validation step."""
    is_valid: bool = True
    issues: list = field(default_factory=list)  # list of DataIssue
    errors: int = 0
    warnings: int = 0
    infos: int = 0

    def add_issue(self, issue: DataIssue):
        self.issues.append(issue)
        if issue.severity == IssueSeverity.ERROR:
            self.errors += 1
            self.is_valid = False
        elif issue.severity == IssueSeverity.WARNING:
            self.warnings += 1
        else:
            self.infos += 1

    def summary(self) -> str:
        return (
            f"Validation: {'PASS' if self.is_valid else 'FAIL'} | "
            f"Errors: {self.errors}, Warnings: {self.warnings}, Info: {self.infos}"
        )

    def get_issues_by_severity(self, severity: IssueSeverity) -> list:
        return [i for i in self.issues if i.severity == severity]


class AnalysisType(Enum):
    """Type of statistical analysis performed."""
    DESCRIPTIVE = "descriptive"
    FREQUENCY = "frequency"
    RELIABILITY = "reliability"
    CORRELATION = "correlation"
    COMPARISON = "comparison"
    REGRESSION = "regression"
    EFA = "efa"
    QUALITY_REPORT = "quality_report"
    SUGGESTION = "suggestion"


@dataclass
class AnalysisResult:
    """Container for a single analysis result."""
    analysis_type: AnalysisType
    title: str
    data: dict = field(default_factory=dict)       # Main result data (DataFrames stored as dicts)
    summary_text: str = ""                          # Human-readable summary
    parameters: dict = field(default_factory=dict)  # Parameters used for the analysis
    warnings: list = field(default_factory=list)    # Any warnings generated

    def to_dict(self) -> dict:
        return {
            "type": self.analysis_type.value,
            "title": self.title,
            "summary": self.summary_text,
            "parameters": self.parameters,
            "data": self.data,
            "warnings": self.warnings,
        }


@dataclass
class SurveyData:
    """
    Main data container for survey data throughout the pipeline.
    Holds the DataFrame and all associated metadata.
    """
    # Core data
    df: pd.DataFrame = field(default_factory=pd.DataFrame)
    original_df: pd.DataFrame = field(default_factory=pd.DataFrame)

    # File metadata
    filename: str = ""
    file_encoding: str = ""
    original_shape: tuple = (0, 0)

    # Column metadata
    columns_info: dict = field(default_factory=dict)  # col_name -> ColumnInfo

    # Validation
    validation: ValidationResult = field(default_factory=ValidationResult)

    # Analysis results (Phase 2)
    analysis_results: list = field(default_factory=list)  # list of AnalysisResult

    # Processing state
    is_loaded: bool = False
    is_validated: bool = False
    is_preprocessed: bool = False

    # Processing log
    processing_log: list = field(default_factory=list)  # list of str

    def log(self, message: str):
        self.processing_log.append(message)

    def add_analysis(self, result: AnalysisResult):
        """Add an analysis result and log it."""
        self.analysis_results.append(result)
        self.log(f"Analysis completed: {result.title}")

    def get_analysis_by_type(self, analysis_type: AnalysisType) -> list:
        """Return all analysis results of a given type."""
        return [r for r in self.analysis_results if r.analysis_type == analysis_type]

    def get_likert_columns(self) -> list:
        """Return column names detected as Likert scale."""
        return [
            name for name, info in self.columns_info.items()
            if info.detected_type == ColumnType.LIKERT
        ]

    def get_demographic_columns(self) -> list:
        """Return column names detected as demographic."""
        return [
            name for name, info in self.columns_info.items()
            if info.detected_type == ColumnType.DEMOGRAPHIC
        ]

    def get_numeric_columns(self) -> list:
        """Return column names that are numeric (including converted Likert)."""
        return [
            name for name, info in self.columns_info.items()
            if info.detected_type in (ColumnType.LIKERT, ColumnType.NUMERIC)
        ]

    def get_categorical_columns(self) -> list:
        """Return column names detected as categorical."""
        return [
            name for name, info in self.columns_info.items()
            if info.detected_type == ColumnType.CATEGORICAL
        ]

    def summary(self) -> dict:
        return {
            "filename": self.filename,
            "encoding": self.file_encoding,
            "original_shape": self.original_shape,
            "current_shape": self.df.shape if not self.df.empty else (0, 0),
            "column_types": {
                ct.value: len([
                    c for c in self.columns_info.values()
                    if c.detected_type == ct
                ])
                for ct in ColumnType
            },
            "is_preprocessed": self.is_preprocessed,
            "analyses_completed": len(self.analysis_results),
            "validation": self.validation.summary() if self.is_validated else "Not validated",
        }
