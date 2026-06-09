"""
Exploratory Factor Analysis (EFA) module.
KMO, Bartlett's test, Communalities, Variance Explained, Rotated Component Matrix.
"""
import pandas as pd
import numpy as np
from scipy import stats as scipy_stats

from models.data_schema import SurveyData, AnalysisResult, AnalysisType
from utils.logger import get_logger

logger = get_logger(__name__)


def _kmo_test(corr_matrix: np.ndarray) -> tuple:
    """
    Compute Kaiser-Meyer-Olkin (KMO) measure of sampling adequacy.
    
    Returns:
        (kmo_per_variable, kmo_overall)
    """
    n = corr_matrix.shape[0]
    
    # Compute partial correlation matrix (anti-image correlation)
    try:
        inv_corr = np.linalg.inv(corr_matrix)
    except np.linalg.LinAlgError:
        # Use pseudo-inverse if singular
        inv_corr = np.linalg.pinv(corr_matrix)
    
    # Diagonal scaling
    diag_inv = np.diag(1.0 / np.sqrt(np.diag(inv_corr)))
    partial_corr = -diag_inv @ inv_corr @ diag_inv
    np.fill_diagonal(partial_corr, 1.0)
    
    # KMO per variable and overall
    corr_sq = corr_matrix ** 2
    partial_sq = partial_corr ** 2
    
    np.fill_diagonal(corr_sq, 0)
    np.fill_diagonal(partial_sq, 0)
    
    sum_corr_sq = corr_sq.sum(axis=0)
    sum_partial_sq = partial_sq.sum(axis=0)
    
    denom = sum_corr_sq + sum_partial_sq
    kmo_per_variable = np.where(denom > 0, sum_corr_sq / denom, 0.0)
    
    total_corr_sq = corr_sq.sum()
    total_partial_sq = partial_sq.sum()
    kmo_overall = total_corr_sq / (total_corr_sq + total_partial_sq) if (total_corr_sq + total_partial_sq) > 0 else 0.0
    
    return kmo_per_variable, kmo_overall


def _bartlett_test(corr_matrix: np.ndarray, n_samples: int) -> tuple:
    """
    Bartlett's Test of Sphericity.
    Tests whether the correlation matrix is an identity matrix.
    
    Returns:
        (chi_square, p_value, df)
    """
    p = corr_matrix.shape[0]
    det = np.linalg.det(corr_matrix)
    
    if det <= 0:
        det = 1e-10  # Avoid log(0)
    
    chi_sq = -((n_samples - 1) - (2 * p + 5) / 6) * np.log(det)
    df = p * (p - 1) / 2
    p_value = 1 - scipy_stats.chi2.cdf(chi_sq, df)
    
    return chi_sq, p_value, int(df)


def _interpret_kmo(kmo: float) -> str:
    """Interpret KMO value."""
    if kmo >= 0.9:
        return "Marvelous"
    elif kmo >= 0.8:
        return "Meritorious"
    elif kmo >= 0.7:
        return "Middling"
    elif kmo >= 0.6:
        return "Mediocre"
    elif kmo >= 0.5:
        return "Miserable"
    else:
        return "Unacceptable"


def compute_efa(
    survey_data: SurveyData,
    columns: list = None,
    n_factors: int = None,
    rotation: str = "varimax",
    loading_threshold: float = 0.5,
) -> AnalysisResult:
    """
    Perform Exploratory Factor Analysis (EFA).
    
    Args:
        survey_data: Preprocessed SurveyData object
        columns: List of column names. If None, use all Likert columns.
        n_factors: Number of factors to extract. If None, use eigenvalue > 1 rule.
        rotation: Rotation method ('varimax' or 'promax')
        loading_threshold: Minimum factor loading to highlight (default 0.5)
    
    Returns:
        AnalysisResult with EFA results
    """
    if columns is None:
        columns = survey_data.get_likert_columns()
    
    if len(columns) < 3:
        return AnalysisResult(
            analysis_type=AnalysisType.EFA,
            title="Exploratory Factor Analysis (EFA)",
            summary_text="Cần ít nhất 3 biến để chạy EFA.",
            warnings=["Không đủ biến cho phân tích nhân tố."],
            parameters={"columns": columns},
        )
    
    df = survey_data.df[columns].dropna()
    n_samples = len(df)
    
    if n_samples < len(columns):
        return AnalysisResult(
            analysis_type=AnalysisType.EFA,
            title="Exploratory Factor Analysis (EFA)",
            summary_text=f"Không đủ mẫu ({n_samples}) cho {len(columns)} biến.",
            warnings=[f"Cần ít nhất {len(columns)} mẫu hợp lệ (hiện tại: {n_samples})."],
            parameters={"columns": columns},
        )
    
    # Correlation matrix
    corr_matrix = df.corr().values
    
    # KMO Test
    kmo_per_var, kmo_overall = _kmo_test(corr_matrix)
    kmo_overall = round(float(kmo_overall), 4)
    kmo_interpretation = _interpret_kmo(kmo_overall)
    
    kmo_per_variable = [
        {"variable": col, "kmo": round(float(kmo_per_var[i]), 4)}
        for i, col in enumerate(columns)
    ]
    
    # Bartlett's Test
    chi_sq, bartlett_p, bartlett_df = _bartlett_test(corr_matrix, n_samples)
    chi_sq = round(float(chi_sq), 4)
    bartlett_p = round(float(bartlett_p), 6)
    
    warnings = []
    
    # Check conditions
    if kmo_overall < 0.5:
        warnings.append(
            f"KMO = {kmo_overall} < 0.5 → Dữ liệu KHÔNG phù hợp cho EFA."
        )
    
    if bartlett_p >= 0.05:
        warnings.append(
            f"Bartlett's Test p = {bartlett_p} ≥ 0.05 → Ma trận tương quan là ma trận đơn vị, không phù hợp cho EFA."
        )
    
    # Eigenvalue decomposition
    eigenvalues, eigenvectors = np.linalg.eigh(corr_matrix)
    # Sort descending
    idx = np.argsort(eigenvalues)[::-1]
    eigenvalues = eigenvalues[idx]
    eigenvectors = eigenvectors[:, idx]
    
    # Determine number of factors (eigenvalue > 1 rule if not specified)
    if n_factors is None:
        n_factors = max(1, int(np.sum(eigenvalues > 1)))
    
    n_factors = min(n_factors, len(columns))
    
    # Total Variance Explained
    total_variance = eigenvalues.sum()
    variance_explained = []
    cumulative = 0.0
    
    for i, ev in enumerate(eigenvalues):
        pct = (ev / total_variance * 100) if total_variance > 0 else 0
        cumulative += pct
        variance_explained.append({
            "component": i + 1,
            "eigenvalue": round(float(ev), 4),
            "variance_pct": round(float(pct), 4),
            "cumulative_pct": round(float(cumulative), 4),
            "extracted": i < n_factors,
        })
    
    # Check cumulative variance for extracted factors
    cumulative_extracted = variance_explained[n_factors - 1]["cumulative_pct"] if n_factors > 0 else 0
    if cumulative_extracted < 50:
        warnings.append(
            f"Tổng phương sai giải thích ({cumulative_extracted:.1f}%) < 50%. "
            "Có thể cần thêm nhân tố hoặc xem lại biến."
        )
    
    # Eigenvalues for Scree Plot
    scree_data = [round(float(ev), 4) for ev in eigenvalues]
    
    # Factor loadings (unrotated)
    # Loading = eigenvector * sqrt(eigenvalue)
    loadings_unrotated = eigenvectors[:, :n_factors] * np.sqrt(eigenvalues[:n_factors])
    
    # Communalities
    communalities = []
    for i, col in enumerate(columns):
        initial = 1.0  # For PCA-based initial estimate
        extraction = round(float(np.sum(loadings_unrotated[i, :] ** 2)), 4)
        communalities.append({
            "variable": col,
            "initial": initial,
            "extraction": extraction,
        })
    
    # Apply rotation
    if n_factors >= 2:
        rotated_loadings = _varimax_rotation(loadings_unrotated) if rotation == "varimax" else _promax_rotation(loadings_unrotated)
    else:
        rotated_loadings = loadings_unrotated.copy()
    
    # Rotated Component Matrix
    rotated_matrix = []
    for i, col in enumerate(columns):
        row = {"variable": col}
        max_loading = 0
        max_factor = 0
        for j in range(n_factors):
            loading = round(float(rotated_loadings[i, j]), 4)
            row[f"Factor_{j+1}"] = loading
            if abs(loading) > abs(max_loading):
                max_loading = loading
                max_factor = j + 1
        row["max_loading"] = round(float(max_loading), 4)
        row["assigned_factor"] = max_factor
        row["meets_threshold"] = abs(max_loading) >= loading_threshold
        rotated_matrix.append(row)
    
    # Cross-loading detection
    cross_loadings = []
    for i, col in enumerate(columns):
        high_loadings = []
        for j in range(n_factors):
            if abs(rotated_loadings[i, j]) >= loading_threshold:
                high_loadings.append(j + 1)
        if len(high_loadings) > 1:
            cross_loadings.append({
                "variable": col,
                "factors": high_loadings,
                "loadings": [round(float(rotated_loadings[i, f-1]), 4) for f in high_loadings],
            })
    
    if cross_loadings:
        cross_vars = [c["variable"] for c in cross_loadings]
        warnings.append(
            f"Phát hiện cross-loading: {', '.join(cross_vars)}. "
            "Các biến này tải lên nhiều nhân tố (≥ threshold)."
        )
    
    # Low loading detection
    low_loading_vars = [r["variable"] for r in rotated_matrix if not r["meets_threshold"]]
    if low_loading_vars:
        warnings.append(
            f"Biến có factor loading thấp (< {loading_threshold}): {', '.join(low_loading_vars)}. "
            "Nên xem xét loại bỏ."
        )
    
    data = {
        "kmo": {
            "overall": kmo_overall,
            "interpretation": kmo_interpretation,
            "per_variable": kmo_per_variable,
        },
        "bartlett": {
            "chi_square": chi_sq,
            "df": bartlett_df,
            "p_value": bartlett_p,
            "significant": bartlett_p < 0.05,
        },
        "n_factors": n_factors,
        "n_samples": n_samples,
        "n_variables": len(columns),
        "variance_explained": variance_explained,
        "cumulative_variance_extracted": round(cumulative_extracted, 2),
        "scree_data": scree_data,
        "communalities": communalities,
        "rotated_matrix": rotated_matrix,
        "rotation_method": rotation,
        "loading_threshold": loading_threshold,
        "cross_loadings": cross_loadings,
    }
    
    summary = (
        f"EFA: KMO = {kmo_overall} ({kmo_interpretation}), "
        f"Bartlett χ² = {chi_sq} (p = {bartlett_p}). "
        f"{n_factors} nhân tố được trích, giải thích {cumulative_extracted:.1f}% phương sai. "
        f"N = {n_samples}."
    )
    
    return AnalysisResult(
        analysis_type=AnalysisType.EFA,
        title="Exploratory Factor Analysis (EFA)",
        data=data,
        summary_text=summary,
        parameters={"columns": columns, "n_factors": n_factors, "rotation": rotation},
        warnings=warnings,
    )


def _varimax_rotation(loadings: np.ndarray, max_iter: int = 100, tol: float = 1e-6) -> np.ndarray:
    """
    Varimax rotation for factor loadings.
    Orthogonal rotation that maximizes the variance of squared loadings.
    """
    n_vars, n_factors = loadings.shape
    rotated = loadings.copy()
    
    for _ in range(max_iter):
        old_rotated = rotated.copy()
        
        for i in range(n_factors):
            for j in range(i + 1, n_factors):
                # Compute rotation angle
                u = rotated[:, i] ** 2 - rotated[:, j] ** 2
                v = 2 * rotated[:, i] * rotated[:, j]
                
                A = u.sum()
                B = v.sum()
                C = (u ** 2 - v ** 2).sum()
                D = (2 * u * v).sum()
                
                num = D - 2 * A * B / n_vars
                den = C - (A ** 2 - B ** 2) / n_vars
                
                if abs(den) < 1e-10:
                    continue
                
                angle = 0.25 * np.arctan2(num, den)
                
                cos_a = np.cos(angle)
                sin_a = np.sin(angle)
                
                new_i = rotated[:, i] * cos_a + rotated[:, j] * sin_a
                new_j = -rotated[:, i] * sin_a + rotated[:, j] * cos_a
                
                rotated[:, i] = new_i
                rotated[:, j] = new_j
        
        # Check convergence
        if np.max(np.abs(rotated - old_rotated)) < tol:
            break
    
    return rotated


def _promax_rotation(loadings: np.ndarray, power: int = 4) -> np.ndarray:
    """
    Promax rotation (oblique).
    First applies varimax, then raises loadings to a power to achieve simple structure.
    """
    varimax_loadings = _varimax_rotation(loadings)
    
    # Raise absolute loadings to power, preserve sign
    target = np.sign(varimax_loadings) * np.abs(varimax_loadings) ** power
    
    # Find rotation matrix via least squares
    try:
        rotation_matrix = np.linalg.lstsq(varimax_loadings, target, rcond=None)[0]
        promax_loadings = varimax_loadings @ rotation_matrix
        
        # Normalize columns
        for j in range(promax_loadings.shape[1]):
            col_norm = np.sqrt(np.sum(promax_loadings[:, j] ** 2))
            if col_norm > 0:
                promax_loadings[:, j] *= np.sqrt(np.sum(varimax_loadings[:, j] ** 2)) / col_norm
        
        return promax_loadings
    except np.linalg.LinAlgError:
        return varimax_loadings
