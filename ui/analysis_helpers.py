"""
Shared UI helper functions for analysis pages.
"""
from __future__ import annotations

import hashlib

import pandas as pd
import streamlit as st

from models.data_schema import ColumnType


def get_numeric_column_names(df: pd.DataFrame) -> list[str]:
    """
    Return column names that contain numeric data.

    This is more robust than pd.api.types.is_numeric_dtype() because
    after preprocessing, some numeric columns may have object dtype
    (e.g., when None replaces missing values).

    Strategy:
    1. If column is already numeric dtype → include
    2. If column is object dtype → try pd.to_numeric coercion.
       If ≥50% of non-null values convert successfully → include
    """
    numeric_cols = []
    for col in df.columns:
        if pd.api.types.is_numeric_dtype(df[col]):
            numeric_cols.append(col)
        else:
            # Try coercion
            coerced = pd.to_numeric(df[col], errors="coerce")
            non_null_original = df[col].notna().sum()
            non_null_coerced = coerced.notna().sum()
            if non_null_original > 0 and (non_null_coerced / non_null_original) >= 0.5:
                numeric_cols.append(col)
    return numeric_cols


def get_categorical_column_names(df: pd.DataFrame, max_unique: int = 15) -> list[str]:
    """
    Return column names suitable as grouping/categorical variables.

    Includes:
    - Non-numeric object/string columns
    - Numeric columns with very few unique values (≤ max_unique)
    """
    cat_cols = []
    for col in df.columns:
        nunique = df[col].nunique()
        if not pd.api.types.is_numeric_dtype(df[col]):
            cat_cols.append(col)
        elif nunique <= max_unique:
            cat_cols.append(col)
    return cat_cols


_COLUMN_TYPE_LABELS = {
    ColumnType.LIKERT.value: "📊 Likert",
    ColumnType.NUMERIC.value: "🔢 Số",
    ColumnType.DEMOGRAPHIC.value: "👤 Nhân khẩu học",
    ColumnType.CATEGORICAL.value: "🏷️ Định danh",
    ColumnType.OPEN_ENDED.value: "💬 Câu trả lời mở",
    ColumnType.ID.value: "🔑 ID",
    ColumnType.UNKNOWN.value: "❓ Chưa rõ",
}


def render_column_picker(
    df: pd.DataFrame,
    *,
    key: str,
    label: str,
    all_columns: list[str] | None = None,
    default_columns: list[str] | None = None,
    recommended_columns: list[str] | None = None,
    columns_info: dict | None = None,
    min_columns: int = 1,
    help_text: str = "",
) -> list[str]:
    """
    Render a visual column picker with search, quick filters, and metadata.

    The selected values are stored in ``st.session_state[f"{key}_selected"]`` so
    hidden rows stay selected while users search/filter the table.
    """
    all_columns = [c for c in (all_columns or list(df.columns)) if c in df.columns]
    default_columns = [c for c in (default_columns or []) if c in all_columns]
    recommended_columns = [c for c in (recommended_columns or []) if c in all_columns]

    selected_key = f"{key}_selected"
    initialized_key = f"{key}_initialized"
    version_key = f"{key}_table_version"

    if initialized_key not in st.session_state:
        st.session_state[selected_key] = default_columns.copy()
        st.session_state[initialized_key] = True
        st.session_state[version_key] = 0

    current_selected = [
        col for col in st.session_state.get(selected_key, [])
        if col in all_columns
    ]
    st.session_state[selected_key] = current_selected
    st.session_state.setdefault(version_key, 0)

    numeric_columns = set(get_numeric_column_names(df))
    recommended_set = set(recommended_columns)

    with st.container(border=True):
        st.markdown(f"**{label}**")
        if help_text:
            st.caption(help_text)

        metric_cols = st.columns(4)
        metric_cols[0].metric("Đã chọn", len(current_selected))
        metric_cols[1].metric("Gợi ý", len(recommended_columns))
        metric_cols[2].metric("Tổng cột", len(all_columns))
        metric_cols[3].metric("Cần tối thiểu", min_columns)

        filter_col, search_col = st.columns([1.2, 2])
        with filter_col:
            filter_mode = st.radio(
                "Lọc nhanh",
                ["Tất cả", "Gợi ý", "Số/Likert", "Định danh", "Đã chọn"],
                horizontal=True,
                key=f"{key}_filter",
            )
        with search_col:
            search_text = st.text_input(
                "Tìm cột",
                placeholder="Nhập tên cột hoặc từ khóa...",
                key=f"{key}_search",
            ).strip().lower()

        visible_columns = _filter_columns(
            df=df,
            columns=all_columns,
            columns_info=columns_info,
            numeric_columns=numeric_columns,
            recommended_columns=recommended_set,
            selected_columns=set(current_selected),
            filter_mode=filter_mode,
            search_text=search_text,
        )

        btn_cols = st.columns(4)
        with btn_cols[0]:
            if st.button(
                "Chọn gợi ý",
                key=f"{key}_select_recommended",
                use_container_width=True,
                disabled=not recommended_columns,
            ):
                _set_selected_columns(key, recommended_columns)
        with btn_cols[1]:
            if st.button(
                "Chọn tất cả đang lọc",
                key=f"{key}_select_visible",
                use_container_width=True,
                disabled=not visible_columns,
            ):
                merged = _ordered_unique(current_selected + visible_columns, all_columns)
                _set_selected_columns(key, merged)
        with btn_cols[2]:
            if st.button(
                "Bỏ chọn đang lọc",
                key=f"{key}_unselect_visible",
                use_container_width=True,
                disabled=not visible_columns,
            ):
                visible_set = set(visible_columns)
                kept = [col for col in current_selected if col not in visible_set]
                _set_selected_columns(key, kept)
        with btn_cols[3]:
            if st.button(
                "Xóa chọn",
                key=f"{key}_clear",
                use_container_width=True,
                disabled=not current_selected,
            ):
                _set_selected_columns(key, [])

        current_selected = [
            col for col in st.session_state.get(selected_key, [])
            if col in all_columns
        ]

        if not visible_columns:
            st.warning("Không tìm thấy cột phù hợp với bộ lọc hiện tại.")
            _render_selected_columns_preview(current_selected)
            return current_selected

        table_df = pd.DataFrame([
            _build_column_picker_row(
                df=df,
                col=col,
                info=(columns_info or {}).get(col),
                selected=col in current_selected,
                recommended=col in recommended_set,
                numeric=col in numeric_columns,
            )
            for col in visible_columns
        ])

        table_key = _column_picker_table_key(
            key,
            st.session_state[version_key],
            visible_columns,
        )
        st.caption("Tick các cột cần dùng, sau đó bấm **Áp dụng lựa chọn** để cập nhật một lần.")
        with st.form(f"{table_key}_form", clear_on_submit=False):
            edited_df = st.data_editor(
                table_df,
                key=table_key,
                use_container_width=True,
                hide_index=True,
                height=_table_height(len(table_df)),
                disabled=["Cột", "Loại", "Gợi ý", "Hợp lệ", "Missing", "Unique", "Ví dụ"],
                column_config={
                    "Chọn": st.column_config.CheckboxColumn("Chọn", width="small"),
                    "Cột": st.column_config.TextColumn("Cột", width="large"),
                    "Loại": st.column_config.TextColumn("Loại", width="medium"),
                    "Gợi ý": st.column_config.CheckboxColumn("Gợi ý", width="small"),
                    "Hợp lệ": st.column_config.NumberColumn("Hợp lệ", width="small"),
                    "Missing": st.column_config.TextColumn("Missing", width="small"),
                    "Unique": st.column_config.NumberColumn("Unique", width="small"),
                    "Ví dụ": st.column_config.TextColumn("Ví dụ", width="large"),
                },
            )
            apply_selection = st.form_submit_button(
                "Áp dụng lựa chọn",
                type="primary",
                use_container_width=True,
            )

        updated_selected = current_selected
        if apply_selection:
            visible_selected = set(
                edited_df.loc[edited_df["Chọn"].fillna(False), "Cột"].tolist()
            )
            visible_set = set(visible_columns)
            updated_selected = [
                col for col in current_selected
                if col not in visible_set or col in visible_selected
            ]
            updated_selected.extend(
                col for col in visible_columns
                if col in visible_selected and col not in updated_selected
            )
            updated_selected = _ordered_unique(updated_selected, all_columns)
            st.session_state[selected_key] = updated_selected
            st.session_state[version_key] = st.session_state.get(version_key, 0) + 1
            st.success(f"Đã cập nhật {len(updated_selected)} cột được chọn.")

        _render_selected_columns_preview(updated_selected)
        return updated_selected


def _set_selected_columns(key: str, selected_columns: list[str]) -> None:
    st.session_state[f"{key}_selected"] = selected_columns
    st.session_state[f"{key}_table_version"] = (
        st.session_state.get(f"{key}_table_version", 0) + 1
    )


def _filter_columns(
    *,
    df: pd.DataFrame,
    columns: list[str],
    columns_info: dict | None,
    numeric_columns: set[str],
    recommended_columns: set[str],
    selected_columns: set[str],
    filter_mode: str,
    search_text: str,
) -> list[str]:
    visible = []
    for col in columns:
        info = (columns_info or {}).get(col)
        type_value = _column_type_value(info)

        if filter_mode == "Gợi ý" and col not in recommended_columns:
            continue
        if filter_mode == "Số/Likert" and not (
            col in numeric_columns or type_value in {ColumnType.LIKERT.value, ColumnType.NUMERIC.value}
        ):
            continue
        if filter_mode == "Định danh" and type_value not in {
            ColumnType.DEMOGRAPHIC.value,
            ColumnType.CATEGORICAL.value,
            ColumnType.ID.value,
        }:
            continue
        if filter_mode == "Đã chọn" and col not in selected_columns:
            continue
        if search_text and search_text not in _searchable_column_text(df, col, info):
            continue
        visible.append(col)
    return visible


def _build_column_picker_row(
    *,
    df: pd.DataFrame,
    col: str,
    info,
    selected: bool,
    recommended: bool,
    numeric: bool,
) -> dict:
    series = df[col]
    missing_count = _info_value(info, "missing_count", int(series.isna().sum()))
    missing_ratio = _info_value(info, "missing_ratio", _safe_missing_ratio(series))
    unique_count = _info_value(info, "unique_count", int(series.nunique(dropna=True)))
    valid_count = int(series.notna().sum())
    type_value = _column_type_value(info)
    type_label = _COLUMN_TYPE_LABELS.get(type_value, "🔢 Số" if numeric else "❓ Chưa rõ")

    return {
        "Chọn": selected,
        "Cột": col,
        "Loại": type_label,
        "Gợi ý": recommended,
        "Hợp lệ": valid_count,
        "Missing": f"{missing_count} ({float(missing_ratio) * 100:.1f}%)",
        "Unique": unique_count,
        "Ví dụ": _sample_values(series),
    }


def _column_type_value(info) -> str:
    detected_type = getattr(info, "detected_type", ColumnType.UNKNOWN)
    return getattr(detected_type, "value", detected_type or ColumnType.UNKNOWN.value)


def _info_value(info, attr: str, fallback):
    value = getattr(info, attr, None)
    return fallback if value is None else value


def _safe_missing_ratio(series: pd.Series) -> float:
    if len(series) == 0:
        return 0.0
    return float(series.isna().sum() / len(series))


def _sample_values(series: pd.Series, max_items: int = 3) -> str:
    samples = []
    for value in series.dropna().astype(str).unique().tolist():
        value = value.strip()
        if not value:
            continue
        if len(value) > 28:
            value = f"{value[:25]}..."
        samples.append(value)
        if len(samples) >= max_items:
            break
    return ", ".join(samples) if samples else "—"


def _searchable_column_text(df: pd.DataFrame, col: str, info) -> str:
    parts = [
        col,
        _column_type_value(info),
        str(getattr(info, "scale_name", "") or ""),
        _sample_values(df[col], max_items=5),
    ]
    return " ".join(parts).lower()


def _ordered_unique(values: list[str], order: list[str]) -> list[str]:
    value_set = set(values)
    return [col for col in order if col in value_set]


def _render_selected_columns_preview(selected_columns: list[str]) -> None:
    if not selected_columns:
        st.caption("Chưa chọn cột nào.")
        return

    preview = ", ".join(selected_columns[:8])
    if len(selected_columns) > 8:
        preview += f", ... (+{len(selected_columns) - 8})"
    st.caption(f"Đã chọn {len(selected_columns)} cột: {preview}")


def _table_height(n_rows: int) -> int:
    return min(420, max(180, 38 * (n_rows + 1)))


def _column_picker_table_key(key: str, version: int, visible_columns: list[str]) -> str:
    digest = hashlib.md5("||".join(visible_columns).encode("utf-8")).hexdigest()[:8]
    return f"{key}_table_{version}_{digest}"
