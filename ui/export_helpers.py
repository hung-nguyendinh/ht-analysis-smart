"""
Download helpers for analysis result tables.
"""
from io import BytesIO
import re

import pandas as pd
import streamlit as st

from models.data_schema import AnalysisType


def _safe_sheet_name(name: str, used: set[str]) -> str:
    base = re.sub(r"[\[\]\:\*\?\/\\]", "_", str(name))[:31] or "Sheet"
    candidate = base
    suffix = 1
    while candidate in used:
        tail = f"_{suffix}"
        candidate = f"{base[:31 - len(tail)]}{tail}"
        suffix += 1
    used.add(candidate)
    return candidate


def _to_dataframe(value) -> pd.DataFrame:
    if isinstance(value, pd.DataFrame):
        return value.copy()
    if isinstance(value, list):
        return pd.DataFrame(value)
    if isinstance(value, dict):
        return pd.DataFrame(value)
    return pd.DataFrame([{"value": value}])


def _add_table(tables: dict[str, pd.DataFrame], name: str, value):
    if value is None:
        return
    df = _to_dataframe(value)
    if not df.empty:
        tables[name] = df


def result_to_tables(result) -> dict[str, pd.DataFrame]:
    """Convert an AnalysisResult into named DataFrames for export."""
    data = result.data or {}
    tables: dict[str, pd.DataFrame] = {
        "Summary": pd.DataFrame([{
            "type": result.analysis_type.value,
            "title": result.title,
            "summary": result.summary_text,
            "parameters": str(result.parameters),
            "warnings": " | ".join(result.warnings),
        }])
    }

    if result.analysis_type == AnalysisType.DESCRIPTIVE:
        _add_table(tables, "Descriptive", data.get("descriptive_table"))
        _add_table(tables, "Grouped_Means", data.get("grouped_means"))

    elif result.analysis_type == AnalysisType.FREQUENCY:
        _add_table(tables, "Frequency", data.get("frequency_table"))

    elif result.analysis_type == AnalysisType.RELIABILITY:
        summary = {
            key: data.get(key)
            for key in ["alpha", "n_items", "n_valid", "interpretation"]
            if key in data
        }
        _add_table(tables, "Reliability_Summary", [summary] if summary else None)
        _add_table(tables, "Item_Statistics", data.get("item_statistics"))

    elif result.analysis_type == AnalysisType.EFA:
        kmo = data.get("kmo", {})
        bartlett = data.get("bartlett", {})
        _add_table(tables, "EFA_Summary", [{
            "kmo": kmo.get("overall"),
            "kmo_interpretation": kmo.get("interpretation"),
            "bartlett_chi_square": bartlett.get("chi_square"),
            "bartlett_df": bartlett.get("df"),
            "bartlett_p": bartlett.get("p_value"),
            "n_factors": data.get("n_factors"),
            "cumulative_variance": data.get("cumulative_variance_extracted"),
            "n_samples": data.get("n_samples"),
        }])
        _add_table(tables, "KMO_Per_Variable", kmo.get("per_variable"))
        _add_table(tables, "Variance_Explained", data.get("variance_explained"))
        _add_table(tables, "Communalities", data.get("communalities"))
        _add_table(tables, "Rotated_Matrix", data.get("rotated_matrix"))
        _add_table(tables, "Cross_Loadings", data.get("cross_loadings"))

    elif result.analysis_type == AnalysisType.CORRELATION:
        _add_table(tables, "Correlation_Matrix", data.get("correlation_matrix"))
        _add_table(tables, "P_Value_Matrix", data.get("p_value_matrix"))
        _add_table(tables, "N_Matrix", data.get("n_matrix"))
        _add_table(tables, "Significant_Pairs", data.get("significant_pairs"))

    elif result.analysis_type == AnalysisType.REGRESSION:
        model_keys = [
            "r", "r_squared", "adj_r_squared", "std_error_estimate",
            "f_statistic", "f_p_value", "df_regression", "df_residual",
            "ss_regression", "ss_residual", "ss_total",
            "ms_regression", "ms_residual", "n", "durbin_watson",
        ]
        _add_table(tables, "Model_Summary", [{k: data.get(k) for k in model_keys}])
        _add_table(tables, "ANOVA", [
            {
                "source": "Regression",
                "SS": data.get("ss_regression"),
                "df": data.get("df_regression"),
                "MS": data.get("ms_regression"),
                "F": data.get("f_statistic"),
                "Sig": data.get("f_p_value"),
            },
            {
                "source": "Residual",
                "SS": data.get("ss_residual"),
                "df": data.get("df_residual"),
                "MS": data.get("ms_residual"),
            },
            {"source": "Total", "SS": data.get("ss_total")},
        ])
        _add_table(tables, "Coefficients", data.get("coefficients"))

    elif result.analysis_type == AnalysisType.COMPARISON:
        _add_table(tables, "Test_Summary", [{
            "test_name": data.get("test_name"),
            "statistic": data.get("statistic"),
            "p_value": data.get("p_value"),
            "significant": data.get("significant"),
            "effect_size": data.get("effect_size"),
            "effect_size_label": data.get("effect_size_label"),
            "effect_interpretation": data.get("effect_interpretation"),
            "n_groups": data.get("n_groups"),
        }])
        _add_table(tables, "Group_Statistics", data.get("group_statistics"))
        assumptions = data.get("assumptions", {})
        normality = assumptions.get("normality", {})
        if normality:
            _add_table(
                tables,
                "Normality",
                [{"group": group, **stats} for group, stats in normality.items()],
            )
        _add_table(tables, "Equal_Variance", [assumptions.get("equal_variance", {})])
        ttest_details = data.get("ttest_details", {})
        if ttest_details:
            _add_table(
                tables,
                "TTest_Details",
                [{"assumption": key, **value} for key, value in ttest_details.items()],
            )
        post_hoc = data.get("post_hoc", {})
        _add_table(tables, "Post_Hoc", post_hoc.get("results") if post_hoc else None)

    return tables


def tables_to_excel_bytes(tables: dict[str, pd.DataFrame]) -> bytes:
    """Serialize named tables into an Excel workbook."""
    output = BytesIO()
    used: set[str] = set()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        for name, df in tables.items():
            df.to_excel(writer, sheet_name=_safe_sheet_name(name, used), index=False)
    return output.getvalue()


def render_result_downloads(result, filename_prefix: str, key_prefix: str):
    """Render Excel and CSV download buttons for an AnalysisResult."""
    tables = result_to_tables(result)
    if not tables:
        return

    main_name = next((name for name in tables if name != "Summary"), "Summary")
    main_csv = tables[main_name].to_csv(index=False).encode("utf-8-sig")
    excel_bytes = tables_to_excel_bytes(tables)

    st.markdown("#### Export")
    col1, col2 = st.columns(2)
    with col1:
        st.download_button(
            "Download Excel report",
            data=excel_bytes,
            file_name=f"{filename_prefix}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            key=f"{key_prefix}_excel",
            use_container_width=True,
        )
    with col2:
        st.download_button(
            f"Download CSV ({main_name})",
            data=main_csv,
            file_name=f"{filename_prefix}_{main_name}.csv",
            mime="text/csv",
            key=f"{key_prefix}_csv",
            use_container_width=True,
        )
