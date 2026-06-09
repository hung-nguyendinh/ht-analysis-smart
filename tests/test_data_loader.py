"""Tests for survey data loading cleanup."""
import pandas as pd

from services.data_loader import load_file


def test_load_file_drops_spss_variable_label_row(tmp_path):
    path = tmp_path / "survey.xlsx"
    df = pd.DataFrame({
        "ID": ["Respondent ID", 1, 2, 3],
        "B1_ITEM": ["B1. Likert item label", 5, 4, 3],
        "B2_ITEM": ["B2. Likert item label", 4, 3, 2],
    })
    df.to_excel(path, index=False)

    survey_data = load_file(str(path))

    assert survey_data.df.shape == (3, 3)
    assert survey_data.df.iloc[0]["ID"] == 1
    assert any("variable-label row" in entry for entry in survey_data.processing_log)
