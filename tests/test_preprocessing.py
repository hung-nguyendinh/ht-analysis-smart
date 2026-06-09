import pytest
import pandas as pd
import numpy as np

from config.likert_mapping import auto_detect_mapping
from models.data_schema import SurveyData, ColumnType
from services.preprocessing import detect_column_type, preprocess_pipeline

def test_auto_detect_mapping_vi():
    values = ["hoàn toàn đồng ý", "đồng ý", "Bình THƯỜNG", "Không đồng ý", "hoàn toàn Không đồng ý"]
    res = auto_detect_mapping(values)
    assert res is not None
    assert res["name"] == "Likert 5 (VI)"
    assert res["scale"] == 5

def test_auto_detect_mapping_en():
    values = ["Strongly Agree", "Agree", "Neutral", "Disagree", "Strongly Disagree"]
    res = auto_detect_mapping(values)
    assert res is not None
    assert res["name"] == "Likert 5 (EN)"
    assert res["scale"] == 5

def test_auto_detect_mapping_fail():
    values = ["random text", "another one", "hello world"]
    res = auto_detect_mapping(values)
    assert res is None

def test_detect_column_type_id():
    series = pd.Series([1, 2, 3])
    assert detect_column_type("STT", series) == ColumnType.ID

def test_detect_column_type_demo():
    series = pd.Series(["Nam", "Nữ"])
    assert detect_column_type("Giới tính", series) == ColumnType.DEMOGRAPHIC

def test_preprocess_pipeline_missing_values():
    df = pd.DataFrame({"col1": ["a", "n/a", "missing", "b", ""]})
    sd = SurveyData(df=df)
    sd.is_loaded = True
    processed_sd = preprocess_pipeline(sd)
    
    res = processed_sd.df["col1"].tolist()
    assert res[0] == "a"
    assert pd.isna(res[1])
    assert pd.isna(res[2])
    assert res[3] == "b"
    assert pd.isna(res[4])

def test_preprocess_pipeline_likert_conversion():
    df = pd.DataFrame({
        "q1": ["hoàn toàn đồng ý", "đồng ý", "bình thường", "không đồng ý", "n/a"]
    })
    sd = SurveyData(df=df)
    sd.is_loaded = True
    processed_sd = preprocess_pipeline(sd)
    
    # Check conversion to numeric
    assert pd.api.types.is_numeric_dtype(processed_sd.df["q1"])
    res = processed_sd.df["q1"].tolist()
    assert res[0] == 5.0
    assert res[1] == 4.0
    assert res[2] == 3.0
    assert res[3] == 2.0
    assert np.isnan(res[4])
    
    # Check metadata
    info = processed_sd.columns_info["q1"]
    assert info.detected_type == ColumnType.LIKERT
    assert info.scale_points == 5
    assert info.is_converted is True


def test_preprocess_pipeline_numeric_strings_become_likert():
    df = pd.DataFrame({
        "B1_ITEM": ["1", "2", "3", "4", "5"],
        "A1_GIOITINH": ["1", "2", "1", "2", "1"],
    })
    sd = SurveyData(df=df)
    sd.is_loaded = True
    processed_sd = preprocess_pipeline(sd)

    assert pd.api.types.is_numeric_dtype(processed_sd.df["B1_ITEM"])
    assert processed_sd.columns_info["B1_ITEM"].detected_type == ColumnType.LIKERT
    assert processed_sd.columns_info["B1_ITEM"].scale_points == 5

    assert pd.api.types.is_numeric_dtype(processed_sd.df["A1_GIOITINH"])
    assert processed_sd.columns_info["A1_GIOITINH"].detected_type == ColumnType.DEMOGRAPHIC
