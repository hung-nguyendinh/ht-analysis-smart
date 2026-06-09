"""
Service for loading survey data from various file formats.
"""
import os
from pathlib import Path

import pandas as pd

from models.data_schema import SurveyData
from utils.helpers import detect_encoding, detect_header_row
from utils.logger import get_logger

logger = get_logger(__name__)


def _numeric_like_ratio(series: pd.Series) -> float:
    """Return the ratio of non-empty values that can be parsed as numbers."""
    valid = series.dropna()
    if valid.empty:
        return 0.0

    parsed = pd.to_numeric(valid, errors="coerce")
    return parsed.notna().sum() / len(valid)


def _drop_variable_label_row(df: pd.DataFrame) -> tuple[pd.DataFrame, bool]:
    """
    Drop an SPSS-style variable-label row below the header when detected.

    Some Excel survey templates use row 1 for variable names and row 2 for
    long labels. Keeping that label row causes numeric Likert columns to be
    loaded as object/categorical, so we remove it when the first data row is
    mostly text and the next row is mostly numeric.
    """
    if len(df) < 3:
        return df, False

    first = df.iloc[0]
    second = df.iloc[1]
    first_valid = first.dropna()
    if first_valid.empty:
        return df, False

    first_text_ratio = first_valid.map(lambda value: isinstance(value, str)).mean()
    first_numeric_ratio = _numeric_like_ratio(first)
    second_numeric_ratio = _numeric_like_ratio(second)

    if (
        first_text_ratio >= 0.7
        and second_numeric_ratio >= 0.4
        and (second_numeric_ratio - first_numeric_ratio) >= 0.3
    ):
        return df.iloc[1:].reset_index(drop=True), True

    return df, False


def get_excel_sheets(file_path: str) -> list[str]:
    """
    Get the names of all sheets in an Excel file.

    Args:
        file_path: Path to the Excel file

    Returns:
        List of sheet names
    """
    path = Path(file_path)
    ext = path.suffix.lower()
    if ext not in (".xlsx", ".xls"):
        return []

    try:
        # Using pd.ExcelFile to read only the sheet names
        with pd.ExcelFile(str(path)) as xls:
            return xls.sheet_names
    except Exception as e:
        logger.error(f"Error reading sheet names from {file_path}: {str(e)}")
        return []


def load_file(file_path: str, sheet_name: str | None = None) -> SurveyData:
    """
    Load a survey data file (.csv, .xlsx, .xls) into a SurveyData object.

    Args:
        file_path: Path to the data file
        sheet_name: Optional name of the sheet to load (for Excel files)

    Returns:
        SurveyData object containing the loaded DataFrame and metadata

    Raises:
        FileNotFoundError: If file does not exist
        ValueError: If file format is not supported
        Exception: For other loading errors
    """
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    ext = path.suffix.lower()
    survey_data = SurveyData(filename=path.name)
    survey_data.log(f"Loading file: {path.name}")

    try:
        # Detect where the actual header starts
        header_row = detect_header_row(str(path))
        if header_row > 0:
            survey_data.log(f"Detected header at row {header_row}. Skipping preceding rows.")

        if ext == ".csv":
            # Detect encoding for CSV files
            encoding = detect_encoding(str(path))
            survey_data.file_encoding = encoding
            survey_data.log(f"Detected encoding: {encoding}")

            # Try loading CSV
            try:
                df = pd.read_csv(
                    str(path),
                    header=header_row,
                    encoding=encoding,
                    on_bad_lines="skip",
                    skip_blank_lines=True,
                )
            except UnicodeDecodeError:
                # Fallback to a safer encoding if detection was wrong
                fallback = "latin-1" if encoding == "utf-8" else "utf-8"
                survey_data.log(f"UnicodeDecodeError with {encoding}. Falling back to {fallback}.")
                df = pd.read_csv(
                    str(path),
                    header=header_row,
                    encoding=fallback,
                    on_bad_lines="skip",
                    skip_blank_lines=True,
                )
                survey_data.file_encoding = fallback

        elif ext in (".xlsx", ".xls"):
            survey_data.file_encoding = "binary (excel)"
            
            # If sheet_name is not provided, pd.read_excel defaults to the first sheet
            if sheet_name:
                survey_data.log(f"Loading sheet: {sheet_name}")
            
            df = pd.read_excel(
                str(path),
                header=header_row,
                sheet_name=sheet_name if sheet_name else 0,
                engine="openpyxl" if ext == ".xlsx" else None,
            )

        else:
            raise ValueError(f"Unsupported file extension: {ext}. Valid extensions are: .csv, .xlsx, .xls")

        # Basic cleaning immediately after load
        df.dropna(how="all", inplace=True)  # Drop completely empty rows
        df.dropna(axis=1, how="all", inplace=True)  # Drop completely empty cols
        df, dropped_label_row = _drop_variable_label_row(df)
        if dropped_label_row:
            survey_data.log("Dropped detected variable-label row below the header.")

        # Ensure column names are strings and stripped
        df.columns = [str(col).strip() for col in df.columns]

        # Handle duplicate column names by appending .1, .2, etc.
        cols = pd.Series(df.columns)
        for dup in cols[cols.duplicated()].unique():
            cols[cols[cols == dup].index.values.tolist()] = [
                dup if i == 0 else f"{dup}.{i}"
                for i in range(sum(cols == dup))
            ]
        df.columns = cols

        survey_data.df = df
        survey_data.original_df = df.copy()
        survey_data.original_shape = df.shape
        survey_data.is_loaded = True

        survey_data.log(f"Successfully loaded {df.shape[0]} rows and {df.shape[1]} columns.")
        return survey_data

    except Exception as e:
        logger.error(f"Error loading file {file_path}: {str(e)}")
        raise
