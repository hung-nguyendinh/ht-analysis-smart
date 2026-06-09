"""
Linear regression module — Simple and Multiple OLS regression.
"""
import pandas as pd
import numpy as np
from scipy import stats as scipy_stats

from models.data_schema import SurveyData, AnalysisResult, AnalysisType
from utils.logger import get_logger

logger = get_logger(__name__)


def _compute_vif(X: np.ndarray, col_index: int) -> float:
    """
    Compute Variance Inflation Factor for a single predictor.
    VIF = 1 / (1 - R²) where R² is from regressing that predictor on all others.
    """
    n, k = X.shape
    if k < 2 or n < 3:
        return 1.0

    y = X[:, col_index]
    X_others = np.delete(X, col_index, axis=1)
    X_others_int = np.column_stack([np.ones(n), X_others])

    try:
        betas = np.linalg.lstsq(X_others_int, y, rcond=None)[0]
        y_pred = X_others_int @ betas
        ss_res = np.sum((y - y_pred) ** 2)
        ss_tot = np.sum((y - y.mean()) ** 2)
        r_sq = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0.0
        return 1.0 / (1 - r_sq) if r_sq < 1.0 else float('inf')
    except (np.linalg.LinAlgError, ValueError):
        return float('inf')


def compute_linear_regression(
    survey_data: SurveyData,
    dependent_col: str,
    independent_cols: list,
) -> AnalysisResult:
    """
    Perform OLS linear regression.

    Args:
        survey_data: Preprocessed SurveyData
        dependent_col: Dependent variable (Y)
        independent_cols: List of independent variables (X1, X2, ...)

    Returns:
        AnalysisResult with R², adjusted R², coefficient table, F-statistic
    """
    df = survey_data.df

    # Validate columns
    all_cols = [dependent_col] + independent_cols
    missing_cols = [c for c in all_cols if c not in df.columns]
    if missing_cols:
        return AnalysisResult(
            analysis_type=AnalysisType.REGRESSION,
            title=f"Linear Regression: {dependent_col}",
            warnings=[f"Column(s) not found: {', '.join(missing_cols)}"],
        )

    if len(independent_cols) < 1:
        return AnalysisResult(
            analysis_type=AnalysisType.REGRESSION,
            title=f"Linear Regression: {dependent_col}",
            warnings=["Need at least 1 independent variable."],
        )

    # Prepare data (listwise deletion)
    data = df[all_cols].dropna()
    n = len(data)
    k = len(independent_cols)  # number of predictors

    if n < k + 2:
        return AnalysisResult(
            analysis_type=AnalysisType.REGRESSION,
            title=f"Linear Regression: {dependent_col}",
            warnings=[f"Not enough valid observations ({n}). Need at least {k + 2}."],
            parameters={"dependent": dependent_col, "independent": independent_cols},
        )

    Y = data[dependent_col].values
    X = data[independent_cols].values

    # Add intercept (column of ones)
    X_with_intercept = np.column_stack([np.ones(n), X])

    try:
        # OLS: β = (X'X)^(-1) X'Y
        XtX = X_with_intercept.T @ X_with_intercept
        XtY = X_with_intercept.T @ Y
        betas = np.linalg.solve(XtX, XtY)
    except np.linalg.LinAlgError:
        return AnalysisResult(
            analysis_type=AnalysisType.REGRESSION,
            title=f"Linear Regression: {dependent_col}",
            warnings=["Singular matrix — cannot compute regression. Check for multicollinearity."],
            parameters={"dependent": dependent_col, "independent": independent_cols},
        )

    # Predictions and residuals
    Y_pred = X_with_intercept @ betas
    residuals = Y - Y_pred

    # R² and Adjusted R²
    ss_res = np.sum(residuals ** 2)
    ss_tot = np.sum((Y - Y.mean()) ** 2)

    r_squared = 1 - (ss_res / ss_tot) if ss_tot != 0 else 0.0
    adj_r_squared = 1 - ((1 - r_squared) * (n - 1) / (n - k - 1)) if n > k + 1 else 0.0

    # F-statistic
    ss_reg = ss_tot - ss_res
    df_reg = k
    df_res = n - k - 1
    ms_reg = ss_reg / df_reg if df_reg > 0 else 0
    ms_res = ss_res / df_res if df_res > 0 else 0
    f_stat = ms_reg / ms_res if ms_res > 0 else 0
    f_p_value = 1 - scipy_stats.f.cdf(f_stat, df_reg, df_res) if df_res > 0 else 1.0

    # Standard errors of coefficients
    if ms_res > 0:
        try:
            cov_matrix = ms_res * np.linalg.inv(XtX)
            se = np.sqrt(np.abs(np.diag(cov_matrix)))
        except np.linalg.LinAlgError:
            se = np.full(k + 1, np.nan)
    else:
        se = np.full(k + 1, np.nan)

    # T-values and p-values for coefficients
    t_values = betas / se if not np.any(np.isnan(se)) else np.full(k + 1, np.nan)
    p_values = [
        round(2 * (1 - scipy_stats.t.cdf(abs(t), df_res)), 4) if df_res > 0 and not np.isnan(t) else np.nan
        for t in t_values
    ]

    # Build coefficient table
    coef_names = ["(Constant)"] + independent_cols
    coefficients = []
    for i, name in enumerate(coef_names):
        coefficients.append({
            "variable": name,
            "B": round(betas[i], 4),
            "std_error": round(se[i], 4) if not np.isnan(se[i]) else None,
            "t_value": round(t_values[i], 4) if not np.isnan(t_values[i]) else None,
            "p_value": p_values[i] if not np.isnan(p_values[i]) else None,
            "significant": p_values[i] < 0.05 if not np.isnan(p_values[i]) else False,
        })

    # Standardized coefficients (Beta) and VIF for predictors only
    vif_warnings = []
    if k >= 1 and np.std(Y) != 0:
        for i, col in enumerate(independent_cols):
            x_std = np.std(data[col].values)
            y_std = np.std(Y)
            if x_std > 0 and y_std > 0:
                coefficients[i + 1]["beta_standardized"] = round(betas[i + 1] * x_std / y_std, 4)
            else:
                coefficients[i + 1]["beta_standardized"] = None

            # VIF & Tolerance
            vif = round(_compute_vif(X, i), 4)
            tolerance = round(1.0 / vif, 4) if vif > 0 and vif != float('inf') else 0.0
            coefficients[i + 1]["vif"] = vif
            coefficients[i + 1]["tolerance"] = tolerance

            if vif >= 10:
                vif_warnings.append(
                    f"Biến '{col}' có VIF = {vif} ≥ 10 → Đa cộng tuyến nghiêm trọng."
                )
            elif vif >= 5:
                vif_warnings.append(
                    f"Biến '{col}' có VIF = {vif} ≥ 5 → Cần lưu ý đa cộng tuyến."
                )

    # Model summary
    r_value = round(np.sqrt(abs(r_squared)), 4)
    std_error_estimate = round(np.sqrt(ms_res), 4) if ms_res > 0 else 0.0

    data_result = {
        "r": r_value,
        "r_squared": round(r_squared, 4),
        "adj_r_squared": round(adj_r_squared, 4),
        "std_error_estimate": std_error_estimate,
        "f_statistic": round(f_stat, 4),
        "f_p_value": round(f_p_value, 4),
        "df_regression": df_reg,
        "df_residual": df_res,
        "ss_regression": round(ss_reg, 4),
        "ss_residual": round(ss_res, 4),
        "ss_total": round(ss_tot, 4),
        "ms_regression": round(ms_reg, 4),
        "ms_residual": round(ms_res, 4),
        "n": n,
        "coefficients": coefficients,
        "durbin_watson": round(_durbin_watson(residuals), 4),
    }

    sig = "significant" if f_p_value < 0.05 else "not significant"
    summary = (
        f"R = {r_value}, R² = {round(r_squared, 4)}, Adjusted R² = {round(adj_r_squared, 4)}. "
        f"F({df_reg}, {df_res}) = {round(f_stat, 4)}, p = {round(f_p_value, 4)} ({sig}). "
        f"N = {n}."
    )

    warnings = []
    if r_squared < 0.1:
        warnings.append("R² is very low. The model explains less than 10% of variance.")
    if f_p_value >= 0.05:
        warnings.append("Overall model is not statistically significant (p ≥ 0.05).")

    # Check Durbin-Watson
    dw = data_result["durbin_watson"]
    if dw < 1.5 or dw > 2.5:
        warnings.append(f"Durbin-Watson = {dw}. Possible autocorrelation in residuals.")

    # VIF warnings
    warnings.extend(vif_warnings)

    return AnalysisResult(
        analysis_type=AnalysisType.REGRESSION,
        title=f"Linear Regression: {dependent_col}",
        data=data_result,
        summary_text=summary,
        parameters={"dependent": dependent_col, "independent": independent_cols},
        warnings=warnings,
    )


def _durbin_watson(residuals: np.ndarray) -> float:
    """Compute Durbin-Watson statistic for autocorrelation check."""
    diff = np.diff(residuals)
    ss_res = np.sum(residuals ** 2)
    if ss_res == 0:
        return 2.0  # Perfect fit, no autocorrelation
    return np.sum(diff ** 2) / ss_res
