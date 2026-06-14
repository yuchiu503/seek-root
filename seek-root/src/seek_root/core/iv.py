"""工具变量法（Instrumental Variables）分析器模块。

工具变量法用于处理内生性问题（endogeneity）。
当处理变量与误差项相关时，普通最小二乘（OLS）估计会有偏。
工具变量 Z 满足两个条件:
1. 相关性: Z 与处理变量 T 相关
2. 外生性: Z 与结果变量 Y 的误差项无关

原理:
    两阶段最小二乘法（2SLS）:
    第一阶段: T = π0 + π1*Z + X*π2 + ν
    第二阶段: Y = β0 + β1*T_hat + X*β2 + ε

    其中 T_hat = π0_hat + π1_hat*Z + X*π2_hat

适用场景:
    - 处理变量内生性问题
    - 自然实验（natural experiments）
    - 评估政策干预
"""

from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass
import polars as pl
import pandas as pd
import numpy as np

from seek_root.core.base import (
    BaseCausalAnalyzer,
    CausalMethod,
    AnalysisResult,
    DiagnosticPlot,
)


@dataclass
class IVConfig:
    """IV分析配置数据类。

    参数:
        treatment_col: 处理变量列名（内生变量）
        instrument_col: 工具变量列名
        outcome_col: 结果变量列名
        covariates: 协变量列名列表
    """

    treatment_col: str
    instrument_col: str
    outcome_col: str
    covariates: List[str] = None

    def __post_init__(self) -> None:
        """初始化后处理。"""
        if self.covariates is None:
            self.covariates = []


class IVAnalyzer(BaseCausalAnalyzer):
    """工具变量法分析器。

    使用两阶段最小二乘法（2SLS）估计处理效应。

    参数:
        data (pl.DataFrame): Polars DataFrame
        config (Dict[str, Any]): 配置字典

    示例:
        >>> df = pl.DataFrame({
        ...     "treatment": [0,1,0,1,0,1,0,1],
        ...     "instrument": [0,1,0,1,0,1,0,1],
        ...     "outcome": [100,120,105,125,110,130,115,135],
        ...     "age": [25,30,35,40,28,32,38,42]
        ... })
        >>> analyzer = IVAnalyzer(data=df, config={
        ...     "treatment_col": "treatment",
        ...     "instrument_col": "instrument",
        ...     "outcome_col": "outcome",
        ...     "covariates": ["age"]
        ... })
        >>> analyzer.fit()
    """

    def __init__(self, data: pl.DataFrame, config: Dict[str, Any]) -> None:
        """初始化IV分析器。

        参数:
            data: 输入数据
            config: 配置字典
        """
        super().__init__(data, config)
        self.config = IVConfig(
            treatment_col=config["treatment_col"],
            instrument_col=config["instrument_col"],
            outcome_col=config["outcome_col"],
            covariates=config.get("covariates", []),
        )

    def validate_config(self) -> Tuple[bool, Optional[str]]:
        """验证IV配置是否有效。

        返回:
            tuple: (是否有效, 错误消息)
        """
        required = [self.config.treatment_col,
                  self.config.instrument_col,
                  self.config.outcome_col]
        valid, msg = self.check_required_columns(self.data, required)
        if not valid:
            return False, msg

        # 检查工具变量是否有足够的变异
        instrument_values = self.data[self.config.instrument_col].to_numpy()
        n_zero = np.sum(instrument_values == 0)
        n_one = np.sum(instrument_values != 0)

        if n_zero < 2 or n_one < 2:
            return False, "工具变量缺乏足够的变异"

        return True, None

    def fit(self) -> None:
        """执行IV估计（2SLS）。

        返回:
            None: 结果存入 self._result 属性
        """
        from scipy import stats

        valid, msg = self.validate_config()
        if not valid:
            raise ValueError(f"配置验证失败: {msg}")

        T = self.config.treatment_col
        Z = self.config.instrument_col
        Y = self.config.outcome_col
        X_cols = self.config.covariates

        df = self.data.to_pandas()

        # 1. 第一阶段: T = π0 + π1*Z + X*π2
        Z_matrix = np.column_stack([np.ones(len(df)), df[Z].values, df[X_cols].values])
        T_actual = df[T].values

        # OLS估计第一阶段
        pi_hat, _, _, _ = np.linalg.lstsq(Z_matrix, T_actual, rcond=None)
        T_hat = Z_matrix @ pi_hat

        # 2. 第二阶段: Y = β0 + β1*T_hat + X*β2
        X_matrix = np.column_stack([np.ones(len(df)), T_hat, df[X_cols].values])
        Y_actual = df[Y].values

        # OLS估计第二阶段
        beta, residuals, rank, s = np.linalg.lstsq(X_matrix, Y_actual, rcond=None)

        # 计算标准误（基于原始的处理变量
        X_matrix_original = np.column_stack([np.ones(len(df)), T_actual, df[X_cols].values])
        n = len(Y_actual)
        k = X_matrix.shape[1]
        sigma2 = np.sum((Y_actual - X_matrix @ beta) ** 2) / (n - k)
        cov_matrix = np.linalg.inv(X_matrix.T @ X_matrix) * sigma2
        se = np.sqrt(np.diag(cov_matrix))

        # 提取处理效应
        tau = beta[1]
        tau_se = se[1]
        t_stat = tau / tau_se
        p_value = 2 * stats.norm.sf(abs(t_stat))

        is_significant = p_value < 0.05

        ci_lower = tau - 1.96 * tau_se
        ci_upper = tau + 1.96 * tau_se

        # 诊断图表
        diagnostic_plots = self._generate_diagnostic_plots(df, T, Z, Y)

        self._result = AnalysisResult(
            method=CausalMethod.IV,
            effect_estimate=float(tau),
            confidence_interval=(float(ci_lower), float(ci_upper)),
            p_value=float(p_value),
            standard_error=float(tau_se),
            sample_size=len(df),
            treatment_size=int(df[T].sum()),
            control_size=int((1 - df[T]).sum()),
            is_significant=is_significant,
            diagnostic_plots=diagnostic_plots,
            metadata={
                "tau": float(tau),
                "first_stage_coef": float(pi_hat[1]),
                "instrument_relevance": self._check_instrument_relevance(df),
                "covariates": X_cols,
            },
        )
        self._is_fitted = True

    def _check_instrument_relevance(self, df: pd.DataFrame) -> float:
        """检查工具变量相关性（第一阶段 F 统计量。

        参数:
            df: 数据

        返回:
            float: F 统计量
        """
        Z = self.config.instrument_col
        T = self.config.treatment_col
        X_cols = self.config.covariates

        # 计算第一阶段的 F 统计量
        Z_matrix = np.column_stack([np.ones(len(df)), df[Z].values, df[X_cols].values])
        T_actual = df[T].values

        # OLS
        beta, residuals, _, _ = np.linalg.lstsq(Z_matrix, T_actual, rcond=None)
        T_pred = Z_matrix @ beta

        # F = (R^2 / k) / ((1 - R^2) / (n - k - 1))
        n = len(df)
        k = Z_matrix.shape[1] - 1
        ss_res = np.sum((T_actual - T_pred) ** 2)
        ss_tot = np.sum((T_actual - T_actual.mean()) ** 2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0

        f_stat = (r_squared / k) / ((1 - r_squared) / (n - k - 1)) if (1 - r_squared) > 0 else 0.0

        return float(f_stat)

    def _generate_diagnostic_plots(
        self,
        df: pd.DataFrame,
        T: str,
        Z: str,
        Y: str,
    ) -> List[DiagnosticPlot]:
        """生成IV诊断图表。

        返回:
            List[DiagnosticPlot]: 诊断图表列表
        """
        plots = []

        # 1. 工具变量 vs 处理变量散点图
        scatter_data = {
            "title": {"text": "工具变量 vs 处理变量"},
            "xAxis": {"type": "value", "name": Z},
            "yAxis": {"type": "value", "name": T},
            "series": [
                {
                    "type": "scatter",
                    "data": [
                        [float(x), float(y)]
                        for x, y in zip(df[Z], df[T])
                    ],
                    "itemStyle": {"color": "#3b82f6"},
                },
            ],
        }
        plots.append(DiagnosticPlot(
            name="工具变量 vs 处理变量",
            chart_type="scatter",
            data=scatter_data,
            title="工具变量相关性",
            description="展示工具变量与处理变量的相关性。工具变量与处理变量必须相关（相关性条件）。",
        ))

        # 2. 工具变量分布
        distribution_data = {
            "title": {"text": "工具变量分布"},
            "xAxis": {"type": "category", "data": ["Z=0", "Z=1"]},
            "yAxis": {"type": "value", "name": "样本数"},
            "series": [
                {
                    "type": "bar",
                    "data": [
                        int((df[Z] == 0).sum()),
                        int((df[Z] == 1).sum()),
                    ],
                    "itemStyle": {"color": "#10b981"},
                    "label": {"show": True, "position": "top"},
                },
            ],
        }
        plots.append(DiagnosticPlot(
            name="工具变量分布",
            chart_type="bar",
            data=distribution_data,
            title="工具变量分布",
            description="展示工具变量的分布情况。",
        ))

        return plots
