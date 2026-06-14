"""断点回归（Regression Discontinuity）分析器模块。

断点回归是一种利用"不连续点"来估计处理效应的准实验方法。
当处理的分配基于某个变量（运行变量）的阈值时，
阈值附近的样本可以被视为近似随机分配。

原理:
    设 R 为运行变量（running variable），c 为断点，
    当 R >= c 时，个体接受处理（T=1），否则不接受（T=0）。

    处理效应估计:
    τ = lim_{R->c+} E[Y|R] - lim_{R->c-} E[Y|R]

    使用多项式回归在断点两侧估计条件期望，
    或者使用局部线性回归。

适用场景:
    - 基于考试分数的奖学金效果评估
    - 基于年龄的政策效果评估
    - 基于销售额的补贴效果评估
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
class RDConfig:
    """RD分析配置数据类。

    参数:
        running_var_col: 运行变量列名
        outcome_col: 结果变量列名
        cutoff: 断点值
        covariates: 协变量列表（可选）
        bandwidth: 带宽参数（可选，默认自动选择）
        order: 多项式阶数（默认1，即线性）
    """

    running_var_col: str
    outcome_col: str
    cutoff: float
    covariates: List[str] = None
    bandwidth: Optional[float] = None
    order: int = 1

    def __post_init__(self) -> None:
        """初始化后处理。"""
        if self.covariates is None:
            self.covariates = []


class RDAnalyzer(BaseCausalAnalyzer):
    """断点回归分析器。

    使用局部线性回归估计断点处的处理效应。

    参数:
        data (pl.DataFrame): Polars DataFrame
        config (Dict[str, Any]): 配置字典

    示例:
        >>> df = pl.DataFrame({
        ...     "score": [45,50,55,60,65,70,75,80,85,90],
        ...     "outcome": [100,105,110,115,120,150,155,160,165,170]
        ... })
        >>> analyzer = RDAnalyzer(data=df, config={
        ...     "running_var_col": "score",
        ...     "outcome_col": "outcome",
        ...     "cutoff": 60
        ... })
        >>> analyzer.fit()
    """

    def __init__(self, data: pl.DataFrame, config: Dict[str, Any]) -> None:
        """初始化RD分析器。

        参数:
            data: 输入数据
            config: 配置字典
        """
        super().__init__(data, config)
        self.config = RDConfig(
            running_var_col=config["running_var_col"],
            outcome_col=config["outcome_col"],
            cutoff=float(config["cutoff"]),
            covariates=config.get("covariates", []),
            bandwidth=config.get("bandwidth"),
            order=config.get("order", 1),
        )

    def validate_config(self) -> Tuple[bool, Optional[str]]:
        """验证RD配置是否有效。

        返回:
            tuple: (是否有效, 错误消息)
        """
        required = [self.config.running_var_col, self.config.outcome_col]
        valid, msg = self.check_required_columns(self.data, required)
        if not valid:
            return False, msg

        cutoff = self.config.cutoff
        running_var = self.data[self.config.running_var_col].to_numpy()

        n_left = np.sum(running_var < cutoff)
        n_right = np.sum(running_var >= cutoff)

        if n_left < 3:
            return False, f"断点左侧样本量不足（当前{n_left}）"
        if n_right < 3:
            return False, f"断点右侧样本量不足（当前{n_right}）"

        return True, None

    def fit(self) -> None:
        """执行RD估计。

        使用局部线性回归在断点两侧估计处理效应。

        返回:
            None: 结果存入 self._result 属性
        """
        from scipy import stats

        valid, msg = self.validate_config()
        if not valid:
            raise ValueError(f"配置验证失败: {msg}")

        R = self.config.running_var_col
        Y = self.config.outcome_col
        cutoff = self.config.cutoff

        df = self.data.to_pandas()

        # 1. 构造运行变量的中心化版本
        df["_R_centered"] = df[R] - cutoff
        df["_treated"] = (df["_R_centered"] >= 0).astype(int)
        df["_treated_R"] = df["_treated"] * df["_R_centered"]

        # 2. 选择带宽（如果未指定，使用整个数据范围）
        if self.config.bandwidth is not None:
            bw = self.config.bandwidth
            df = df[abs(df["_R_centered"]) <= bw].copy()

        # 3. 局部线性回归
        # Y = β0 + β1*Treated + β2*R_centered + β3*(Treated*R_centered) + ε
        X_cols = ["_treated", "_R_centered", "_treated_R"]
        X = df[X_cols].values
        y = df[Y].values

        # 最小二乘估计
        X_with_const = np.column_stack([np.ones(len(X)), X])
        beta, residuals, rank, s = np.linalg.lstsq(X_with_const, y, rcond=None)

        # 计算标准误
        n = len(y)
        k = X_with_const.shape[1]
        sigma2 = residuals.sum() / (n - k)
        cov_matrix = np.linalg.inv(X_with_const.T @ X_with_const) * sigma2
        se = np.sqrt(np.diag(cov_matrix))

        # 提取处理效应（_treated 系数）
        tau = beta[1]  # _treated 是第二个系数（索引1）
        tau_se = se[1]
        t_stat = tau / tau_se
        p_value = 2 * stats.t.sf(abs(t_stat), n - k)

        is_significant = p_value < 0.05

        ci_lower = tau - 1.96 * tau_se
        ci_upper = tau + 1.96 * tau_se

        # 诊断图表
        diagnostic_plots = self._generate_diagnostic_plots(df, R, Y, cutoff)

        self._result = AnalysisResult(
            method=CausalMethod.RD,
            effect_estimate=float(tau),
            confidence_interval=(float(ci_lower), float(ci_upper)),
            p_value=float(p_value),
            standard_error=float(tau_se),
            sample_size=len(df),
            treatment_size=int(df["_treated"].sum()),
            control_size=int((1 - df["_treated"]).sum()),
            is_significant=is_significant,
            diagnostic_plots=diagnostic_plots,
            metadata={
                "cutoff": cutoff,
                "bandwidth": self.config.bandwidth,
                "order": self.config.order,
                "running_var": R,
            },
        )
        self._is_fitted = True

    def _generate_diagnostic_plots(
        self,
        df: pd.DataFrame,
        running_var_col: str,
        outcome_col: str,
        cutoff: float,
    ) -> List[DiagnosticPlot]:
        """生成RD诊断图表。

        参数:
            df: 数据
            running_var_col: 运行变量
            outcome_col: 结果变量
            cutoff: 断点值

        返回:
            List[DiagnosticPlot]: 诊断图表列表
        """
        plots = []

        # 1. 散点图 + 拟合线
        left_df = df[df[running_var_col] < cutoff].sort_values(running_var_col)
        right_df = df[df[running_var_col] >= cutoff].sort_values(running_var_col)

        scatter_data = {
            "title": {"text": "断点回归散点图"},
            "xAxis": {"type": "value", "name": running_var_col},
            "yAxis": {"type": "value", "name": outcome_col},
            "series": [
                {
                    "name": "左侧（未处理）",
                    "type": "scatter",
                    "data": [
                        [float(x), float(y)]
                        for x, y in zip(left_df[running_var_col], left_df[outcome_col])
                    ],
                    "itemStyle": {"color": "#8b5cf6"},
                },
                {
                    "name": "右侧（处理）",
                    "type": "scatter",
                    "data": [
                        [float(x), float(y)]
                        for x, y in zip(right_df[running_var_col], right_df[outcome_col])
                    ],
                    "itemStyle": {"color": "#10b981"},
                },
                {
                    "name": "断点",
                    "type": "line",
                    "data": [
                        [cutoff, df[outcome_col].min()],
                        [cutoff, df[outcome_col].max()],
                    ],
                    "lineStyle": {"color": "#ef4444", "type": "dashed", "width": 3},
                },
            ],
            "legend": {"top": "0%"},
        }
        plots.append(DiagnosticPlot(
            name="断点散点图",
            chart_type="scatter",
            data=scatter_data,
            title="断点散点图",
            description="展示运行变量与结果变量的关系，断点处的跳跃即为处理效应。",
        ))

        # 2. 运行变量分布（检查是否存在堆聚）
        bins = 20
        min_val = df[running_var_col].min()
        max_val = df[running_var_col].max()
        bin_edges = np.linspace(min_val, max_val, bins + 1)
        counts, _ = np.histogram(df[running_var_col], bins=bin_edges)

        distribution_data = {
            "title": {"text": "运行变量分布"},
            "xAxis": {
                "type": "category",
                "data": [f"{bin_edges[i]:.1f}-{bin_edges[i+1]:.1f}" for i in range(bins)],
                "name": running_var_col,
            },
            "yAxis": {"type": "value", "name": "样本数"},
            "series": [
                {
                    "name": "样本数",
                    "type": "bar",
                    "data": [int(c) for c in counts],
                    "itemStyle": {"color": "#3b82f6"},
                    "label": {"show": True, "position": "top"},
                    "markLine": {
                        "data": [{"xAxis": int(np.where(bin_edges >= cutoff)[0][0])}],
                        "lineStyle": {"color": "#ef4444", "type": "dashed"},
                    },
                },
            ],
        }
        plots.append(DiagnosticPlot(
            name="运行变量分布",
            chart_type="bar",
            data=distribution_data,
            title="运行变量分布",
            description="检查运行变量是否存在异常堆聚（manipulation test）。",
        ))

        return plots
