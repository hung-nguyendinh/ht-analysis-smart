"""
Group comparison module — T-test, ANOVA, Mann-Whitney, Kruskal-Wallis.
Auto-detects parametric vs non-parametric tests based on data characteristics.
"""
import pandas as pd
import numpy as np
from scipy import stats as scipy_stats
from itertools import combinations

from models.data_schema import SurveyData, AnalysisResult, AnalysisType
from utils.logger import get_logger

logger = get_logger(__name__)


def _check_normality(series: pd.Series, alpha: float = 0.05) -> dict:
    """
    Check normality using Shapiro-Wilk test.
    For large samples (> 5000), use a sample.
    """
    data = series.dropna().values
    n = len(data)

    if n < 3:
        return {"is_normal": False, "test": "insufficient_data", "p_value": None, "n": n}

    # Shapiro-Wilk has a limit, sample if too large
    if n > 5000:
        rng = np.random.default_rng(42)
        data = rng.choice(data, size=5000, replace=False)

    stat, p = scipy_stats.shapiro(data)
    return {
        "is_normal": p > alpha,
        "test": "shapiro_wilk",
        "statistic": round(stat, 4),
        "p_value": round(p, 4),
        "n": n,
    }


def _check_equal_variance(*groups, alpha: float = 0.05) -> dict:
    """Check homogeneity of variances using Levene's test."""
    clean_groups = [g.dropna().values for g in groups if len(g.dropna()) >= 2]

    if len(clean_groups) < 2:
        return {"equal_var": True, "test": "insufficient_groups", "p_value": None}

    stat, p = scipy_stats.levene(*clean_groups)
    return {
        "equal_var": p > alpha,
        "test": "levene",
        "statistic": round(stat, 4),
        "p_value": round(p, 4),
    }


def _compute_effect_size_2groups(group1, group2):
    """Compute Cohen's d for two groups."""
    n1, n2 = len(group1), len(group2)
    if n1 < 2 or n2 < 2:
        return None

    var1, var2 = group1.var(ddof=1), group2.var(ddof=1)
    pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))

    if pooled_std == 0:
        return 0.0

    d = (group1.mean() - group2.mean()) / pooled_std
    return round(abs(d), 4)


def _compute_eta_squared(f_stat, df_between, df_within):
    """Compute eta-squared effect size for ANOVA."""
    if df_within == 0:
        return None
    eta_sq = (f_stat * df_between) / (f_stat * df_between + df_within)
    return round(max(0.0, min(1.0, eta_sq)), 4)


def _interpret_effect_size(value, test_type="cohen_d"):
    """Interpret effect size value."""
    if value is None:
        return "N/A"

    if test_type == "cohen_d":
        if value >= 0.8:
            return "large"
        elif value >= 0.5:
            return "medium"
        elif value >= 0.2:
            return "small"
        else:
            return "negligible"
    elif test_type == "eta_squared":
        if value >= 0.14:
            return "large"
        elif value >= 0.06:
            return "medium"
        elif value >= 0.01:
            return "small"
        else:
            return "negligible"
    elif test_type == "r":
        if value >= 0.5:
            return "large"
        elif value >= 0.3:
            return "medium"
        elif value >= 0.1:
            return "small"
        else:
            return "negligible"
    return "unknown"


def compare_groups(
    survey_data: SurveyData,
    group_col: str,
    value_col: str,
    test: str = "auto",
) -> AnalysisResult:
    """
    Compare means/distributions across groups.

    Auto-detects the appropriate test:
    - 2 groups: Independent T-test (parametric) or Mann-Whitney U (non-parametric)
    - 3+ groups: One-way ANOVA (parametric) or Kruskal-Wallis (non-parametric)

    Args:
        survey_data: Preprocessed SurveyData
        group_col: Grouping variable (categorical/demographic)
        value_col: Numeric variable to compare
        test: "auto", "ttest", "mannwhitney", "anova", "kruskal"

    Returns:
        AnalysisResult with test statistics, p-value, effect size
    """
    df = survey_data.df

    for col in [group_col, value_col]:
        if col not in df.columns:
            return AnalysisResult(
                analysis_type=AnalysisType.COMPARISON,
                title=f"Group Comparison: {value_col} by {group_col}",
                warnings=[f"Column '{col}' not found in dataset."],
            )

    # Split into groups
    groups_data = {}
    for name, grp in df.groupby(group_col):
        vals = grp[value_col].dropna()
        if len(vals) >= 2:
            groups_data[str(name)] = vals

    n_groups = len(groups_data)

    if n_groups < 2:
        return AnalysisResult(
            analysis_type=AnalysisType.COMPARISON,
            title=f"Group Comparison: {value_col} by {group_col}",
            warnings=[f"Need at least 2 groups with sufficient data. Found {n_groups} valid group(s)."],
            parameters={"group_col": group_col, "value_col": value_col},
        )

    # Group descriptives
    group_stats = []
    for name, vals in groups_data.items():
        n = len(vals)
        std_val = vals.std(ddof=1)
        se_val = std_val / np.sqrt(n) if n > 0 else 0
        group_stats.append({
            "group": name,
            "n": n,
            "mean": round(vals.mean(), 4),
            "std": round(std_val, 4),
            "se_mean": round(se_val, 4),
            "median": round(vals.median(), 4),
        })

    # Assumption checks
    normality_results = {}
    for name, vals in groups_data.items():
        normality_results[name] = _check_normality(vals)

    all_normal = all(r["is_normal"] for r in normality_results.values())
    variance_result = _check_equal_variance(*groups_data.values())
    equal_var = variance_result["equal_var"]

    # Auto-detect test
    warnings = []
    if test == "auto":
        if n_groups == 2:
            if all_normal and equal_var:
                test = "ttest"
            else:
                test = "mannwhitney"
                if not all_normal:
                    warnings.append("Normality assumption violated → using non-parametric test.")
                if not equal_var:
                    warnings.append("Equal variance assumption violated.")
        else:
            if all_normal and equal_var:
                test = "anova"
            else:
                test = "kruskal"
                if not all_normal:
                    warnings.append("Normality assumption violated → using non-parametric test.")

    # Execute test
    group_values = list(groups_data.values())
    group_names = list(groups_data.keys())

    if test == "ttest":
        if n_groups != 2:
            warnings.append(f"T-test is for 2 groups. Found {n_groups}. Only comparing the first two: {group_names[0]} vs {group_names[1]}.")
        
        g1, g2 = group_values[0], group_values[1]
        stat, p = scipy_stats.ttest_ind(g1, g2, equal_var=equal_var)
        test_name = "Independent Samples T-Test"
        effect = _compute_effect_size_2groups(g1, g2)
        effect_type = "cohen_d"
        effect_label = "Cohen's d"

        # Mean Difference & Confidence Interval
        mean_diff = g1.mean() - g2.mean()
        n1, n2 = len(g1), len(g2)
        var1, var2 = g1.var(ddof=1), g2.var(ddof=1)
        
        # Equal variances assumed
        stat_eq, p_eq = scipy_stats.ttest_ind(g1, g2, equal_var=True)
        pooled_var = ((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2)
        se_eq = np.sqrt(pooled_var * (1/n1 + 1/n2))
        df_eq = n1 + n2 - 2
        t_crit_eq = scipy_stats.t.ppf(0.975, df_eq) if df_eq > 0 else 0
        
        # Equal variances not assumed (Welch)
        stat_neq, p_neq = scipy_stats.ttest_ind(g1, g2, equal_var=False)
        se_neq = np.sqrt(var1/n1 + var2/n2)
        denom = ((var1/n1)**2 / (n1-1)) + ((var2/n2)**2 / (n2-1))
        df_neq = ((var1/n1 + var2/n2)**2 / denom) if denom > 0 else 1
        t_crit_neq = scipy_stats.t.ppf(0.975, df_neq)
        
        ttest_details = {
            "equal_assumed": {
                "t": round(stat_eq, 4),
                "df": round(df_eq, 4),
                "Sig": round(p_eq, 4),
                "Mean Difference": round(mean_diff, 4),
                "Std. Error Difference": round(se_eq, 4),
                "ci_lower": round(mean_diff - t_crit_eq * se_eq, 4),
                "ci_upper": round(mean_diff + t_crit_eq * se_eq, 4),
            },
            "equal_not_assumed": {
                "t": round(stat_neq, 4),
                "df": round(df_neq, 4),
                "Sig": round(p_neq, 4),
                "Mean Difference": round(mean_diff, 4),
                "Std. Error Difference": round(se_neq, 4),
                "ci_lower": round(mean_diff - t_crit_neq * se_neq, 4),
                "ci_upper": round(mean_diff + t_crit_neq * se_neq, 4),
            }
        }
    elif test == "mannwhitney":
        if n_groups != 2:
            warnings.append(f"Mann-Whitney is for 2 groups. Found {n_groups}. Only comparing the first two: {group_names[0]} vs {group_names[1]}.")
        stat, p = scipy_stats.mannwhitneyu(group_values[0], group_values[1], alternative="two-sided")
        test_name = "Mann-Whitney U Test"
        # Effect size: r = Z / sqrt(N)
        n_total = len(group_values[0]) + len(group_values[1])
        z = scipy_stats.norm.ppf(1 - p / 2) if p > 0 else 0
        effect = round(abs(z) / np.sqrt(n_total), 4) if n_total > 0 else None
        effect_type = "r"
        effect_label = "r (effect size)"

        # Mean Difference & Confidence Interval (same as t-test for display)
        mean_diff = round(group_values[0].mean() - group_values[1].mean(), 4)
        n1, n2 = len(group_values[0]), len(group_values[1])
        se_diff = round(np.sqrt(group_values[0].var(ddof=1)/n1 + group_values[1].var(ddof=1)/n2), 4)
        df_val = n1 + n2 - 2
        t_crit = scipy_stats.t.ppf(0.975, max(df_val, 1))
        ci_lower = round(mean_diff - t_crit * se_diff, 4)
        ci_upper = round(mean_diff + t_crit * se_diff, 4)

    elif test == "anova":
        if n_groups < 2:
            return AnalysisResult(
                analysis_type=AnalysisType.COMPARISON,
                title=f"Group Comparison: {value_col} by {group_col}",
                warnings=["ANOVA requires at least 2 groups."],
            )
        stat, p = scipy_stats.f_oneway(*group_values)
        test_name = "One-Way ANOVA"
        df_between = n_groups - 1
        df_within = sum(len(g) for g in group_values) - n_groups
        effect = _compute_eta_squared(stat, df_between, df_within)
        effect_type = "eta_squared"
        effect_label = "η² (Eta-squared)"

    elif test == "kruskal":
        if n_groups < 2:
            return AnalysisResult(
                analysis_type=AnalysisType.COMPARISON,
                title=f"Group Comparison: {value_col} by {group_col}",
                warnings=["Kruskal-Wallis requires at least 2 groups."],
            )
        stat, p = scipy_stats.kruskal(*group_values)
        test_name = "Kruskal-Wallis H Test"
        # Effect size: η² = (H - k + 1) / (N - k)
        n_total = sum(len(g) for g in group_values)
        if n_total > n_groups:
            eta_sq = (stat - n_groups + 1) / (n_total - n_groups)
            effect = round(max(0.0, min(1.0, eta_sq)), 4)
        else:
            effect = None
        effect_type = "eta_squared"
        effect_label = "η² (Eta-squared)"

    else:
        return AnalysisResult(
            analysis_type=AnalysisType.COMPARISON,
            title=f"Group Comparison: {value_col} by {group_col}",
            warnings=[f"Unknown test: '{test}'. Use 'auto', 'ttest', 'mannwhitney', 'anova', or 'kruskal'."],
        )

    stat = round(stat, 4)
    p = round(p, 4)
    sig = "significant" if p < 0.05 else "not significant"
    effect_interp = _interpret_effect_size(effect, effect_type)

    data = {
        "test_name": test_name,
        "statistic": stat,
        "p_value": p,
        "significant": p < 0.05,
        "effect_size": effect,
        "effect_size_label": effect_label,
        "effect_interpretation": effect_interp,
        "n_groups": n_groups,
        "group_statistics": group_stats,
        "assumptions": {
            "normality": normality_results,
            "equal_variance": variance_result,
        },
    }

    # Add T-test specific details
    if test == "ttest" and n_groups == 2:
        data["ttest_details"] = ttest_details
    elif test == "mannwhitney" and n_groups == 2:
        data["mean_difference"] = mean_diff
        data["std_error_difference"] = se_diff
        data["confidence_interval_95"] = {"lower": ci_lower, "upper": ci_upper}

    # Add Post Hoc for 3+ groups when significant
    if n_groups >= 3 and p < 0.05:
        post_hoc = _compute_post_hoc(groups_data)
        data["post_hoc"] = post_hoc

    summary = (
        f"{test_name}: statistic = {stat}, p = {p} ({sig}). "
        f"{effect_label} = {effect} ({effect_interp}). "
        f"Groups: {', '.join(group_names)}."
    )

    return AnalysisResult(
        analysis_type=AnalysisType.COMPARISON,
        title=f"Group Comparison: {value_col} by {group_col}",
        data=data,
        summary_text=summary,
        parameters={"group_col": group_col, "value_col": value_col, "test": test},
        warnings=warnings,
    )


def _compute_post_hoc(groups_data: dict) -> dict:
    """
    Compute Post Hoc pairwise comparisons using Tukey-like approach.
    Uses pairwise t-tests with Bonferroni correction.
    Falls back to scipy.stats.tukey_hsd if available.
    """
    group_names = list(groups_data.keys())
    group_values = list(groups_data.values())
    n_comparisons = len(group_names) * (len(group_names) - 1) // 2

    pairwise_results = []

    # Try scipy's tukey_hsd (available in scipy >= 1.8)
    try:
        tukey_result = scipy_stats.tukey_hsd(*[g.values for g in group_values])
        for i, j in combinations(range(len(group_names)), 2):
            mean_diff = round(group_values[i].mean() - group_values[j].mean(), 4)
            ci = tukey_result.confidence_interval(confidence_level=0.95)
            p_val = round(float(tukey_result.pvalue[i][j]), 4)
            pairwise_results.append({
                "group1": group_names[i],
                "group2": group_names[j],
                "mean_difference": mean_diff,
                "p_value": p_val,
                "significant": p_val < 0.05,
                "ci_lower": round(float(ci.low[i][j]), 4),
                "ci_upper": round(float(ci.high[i][j]), 4),
                "method": "Tukey HSD",
            })
        return {
            "method": "Tukey HSD",
            "n_comparisons": n_comparisons,
            "results": pairwise_results,
        }
    except (AttributeError, TypeError, Exception):
        pass

    # Fallback: pairwise t-tests with Bonferroni correction
    for i, j in combinations(range(len(group_names)), 2):
        g1, g2 = group_values[i], group_values[j]
        t_stat, p_raw = scipy_stats.ttest_ind(g1, g2)
        p_bonf = min(round(p_raw * n_comparisons, 4), 1.0)  # Bonferroni correction
        mean_diff = round(g1.mean() - g2.mean(), 4)

        # Confidence interval for mean difference
        n1, n2 = len(g1), len(g2)
        se = np.sqrt(g1.var(ddof=1)/n1 + g2.var(ddof=1)/n2)
        df_val = n1 + n2 - 2
        t_crit = scipy_stats.t.ppf(1 - 0.05 / (2 * n_comparisons), df_val)  # Bonferroni-adjusted
        ci_lower = round(mean_diff - t_crit * se, 4)
        ci_upper = round(mean_diff + t_crit * se, 4)

        pairwise_results.append({
            "group1": group_names[i],
            "group2": group_names[j],
            "mean_difference": mean_diff,
            "p_value": p_bonf,
            "significant": p_bonf < 0.05,
            "ci_lower": ci_lower,
            "ci_upper": ci_upper,
            "method": "Bonferroni",
        })

    return {
        "method": "Bonferroni",
        "n_comparisons": n_comparisons,
        "results": pairwise_results,
    }
