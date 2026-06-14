"""双差分法（Difference-in-Differences）分析器模块。

双差分法是一种准实验方法，用于评估政策或处理效应。
通过比较处理组和控制组在处理前后的变化差异，
来估计处理效应（ATT - Average Treatment effect on the Treated）。

原理:
    DID的核心思想是将处理效应分解为两个部分：
    1. 时间效应：控制组随时间的变化
    2. 组别×时间交互效应：处理组相对于控制组的额外变化

    ATT = (Y_treatment_post - Y_treatment_pre) - (Y_control_post - Y_control_pre)

实现方式:
    使用双向固定效应模型（Two-way Fixed Effects）：
    Y = β0 + β1*Treated + β2*Post + β3*(Treated*Post) + X*γ + ε

    其中 β3 就是我们要估计的 ATT。

适用场景:
    - 促销活动效果评估
    - 政策实施效果评估
    - A/B测试的因果验证
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
class DIDConfig:
    """DID分析配置数据类。

    参数:
        treatment_col: 处理组标识列名（值为0/1或布尔值）
        time_col: 时间标识列名（值为0/1，0=处理前，1=处理后）
        outcome_col: 结果变量列名
        covariates: 协变量列名列表（可选，用于控制变量）
    """

    treatment_col: str
    time_col: str
    outcome_col: str
    covariates: List[str] = None

    def __post_init__(self) -> None:
        """初始化后处理，确保covariates不为None。"""
        if self.covariates is None:
            self.covariates = []


class DIDAnalyzer(BaseCausalAnalyzer):
    """双差分法分析器。

    用于评估有处理组和控制组、有前后时间点的政策/活动效果。

    参数:
        data (pl.DataFrame): Polars DataFrame，包含分析所需的全部列
        config (Dict[str, Any]): 分析配置字典

    属性:
        config: DIDConfig配置对象
        fitted_result: 拟合结果

    示例:
        >>> df = pl.DataFrame({
        ...     "is_treated": [0,0,1,1],
        ...     "is_post": [0,1,0,1],
        ...     "revenue": [100,110,100,130]
        ... })
        >>> analyzer = DIDAnalyzer(data=df, config={
        ...     "treatment_col": "is_treated",
        ...     "time_col": "is_post",
        ...     "outcome_col": "revenue"
        ... })
        >>> analyzer.fit()
        >>> result = analyzer.get_result()
        >>> print(f"ATT: {result.effect_estimate:.2f}")
    """

    def __init__(self, data: pl.DataFrame, config: Dict[str, Any]) -> None:
        """初始化DID分析器。

        参数:
            data: 输入的Polars DataFrame数据
            config: 分析配置字典
        """
        super().__init__(data, config)
        self.config = DIDConfig(
            treatment_col=config["treatment_col"],
            time_col=config["time_col"],
            outcome_col=config["outcome_col"],
            covariates=config.get("covariates", []),
        )

    def validate_config(self) -> Tuple[bool, Optional[str]]:
        """验证DID配置是否有效。

        检查必需列是否存在，以及数据类型是否正确。

        返回:
            tuple: (是否有效, 错误消息)
        """
        required = [self.config.treatment_col, self.config.time_col, self.config.outcome_col]
        valid, msg = self.check_required_columns(self.data, required)
        if not valid:
            return False, msg

        # 检查样本量
        treatment_n = self.data.filter(pl.col(self.config.treatment_col) == 1).height
        control_n = self.data.filter(pl.col(self.config.treatment_col) == 0).height

        if treatment_n < 2:
            return False, f"处理组样本量不足（当前{treatment_n}，建议至少2个）"
        if control_n < 2:
            return False, f"对照组样本量不足（当前{control_n}，建议至少2个）"

        return True, None

    def fit(self) -> None:
        """执行DID估计。

        使用双向固定效应模型估计处理效应。

        方法:
            使用 statsmodels OLS 估计：
            Y = β0 + β1*T + β2*P + β3*(T*P) + X*γ + ε

            其中:
            - T: 处理组标识
            - P: 处理后时间标识
            - T*P: 交互项（处理效应）
            - X: 协变量

        返回:
            None: 结果存入 self._result 属性

        异常:
            ValueError: 配置无效时抛出
            RuntimeError: 估计失败时抛出
        """
        import statsmodels.api as sm
        from scipy import stats

        # 验证配置
        valid, msg = self.validate_config()
        if not valid:
            raise ValueError(f"配置验证失败: {msg}")

        # 获取配置
        T = self.config.treatment_col  # 处理组
        P = self.config.time_col        # 时间
        Y = self.config.outcome_col     # 结果
        X_cols = self.config.covariates  # 协变量

        # 转换为Pandas DataFrame
        df = self.data.to_pandas()

        # 创建交互项
        df["_interaction"] = df[T] * df[P]

        # 准备特征矩阵
        feature_cols = [T, P, "_interaction"] + X_cols
        X = df[feature_cols].values
        y = df[Y].values

        # 添加截距项
        X_sm = sm.add_constant(X)

        # OLS估计
        model = sm.OLS(y, X_sm)
        fitted_model = model.fit(cov_type='HC3')  # 稳健标准误

        # 提取处理效应（交互项的系数）
        # 系数顺序: const, T, P, T*P, 协变量...
        effect_idx = 3  # 交互项是第4个系数（索引3）
        att = fitted_model.params[effect_idx]
        std_err = fitted_model.bse[effect_idx]
        t_stat = att / std_err
        p_value = 2 * stats.norm.sf(abs(t_stat))  # 双侧p值

        # 95%置信区间
        ci_lower = att - 1.96 * std_err
        ci_upper = att + 1.96 * std_err

        # 统计显著性
        is_significant = p_value < 0.05

        # 处理组和对照组样本量
        treatment_n = int(df[T].sum())
        control_n = len(df) - treatment_n

        # 生成诊断图表
        diagnostic_plots = self._generate_diagnostic_plots(df, T, P, Y)

        # 构建结果
        self._result = AnalysisResult(
            method=CausalMethod.DID,
            effect_estimate=float(att),
            confidence_interval=(float(ci_lower), float(ci_upper)),
            p_value=float(p_value),
            standard_error=float(std_err),
            sample_size=len(df),
            treatment_size=treatment_n,
            control_size=control_n,
            is_significant=is_significant,
            diagnostic_plots=diagnostic_plots,
            metadata={
                "att": float(att),
                "t_stat": float(t_stat),
                "model_r2": float(fitted_model.rsquared),
                "treatment_col": T,
                "time_col": P,
                "outcome_col": Y,
                "covariates": X_cols,
            },
        )

        self._is_fitted = True

    def _generate_diagnostic_plots(
        self,
        df: pd.DataFrame,
        treatment_col: str,
        time_col: str,
        outcome_col: str,
    ) -> List[DiagnosticPlot]:
        """生成DID诊断图表。

        生成平行趋势检验图和各组均值对比图。

        参数:
            df: Pandas DataFrame
            treatment_col: 处理组列名
            time_col: 时间列名
            outcome_col: 结果变量列名

        返回:
            List[DiagnosticPlot]: 诊断图表列表
        """
        plots = []

        # 1. 平行趋势图 - 处理组和对照组随时间的均值变化
        t_pre_mean = df[(df[treatment_col] == 1) & (df[time_col] == 0)][outcome_col].mean()
        t_post_mean = df[(df[treatment_col] == 1) & (df[time_col] == 1)][outcome_col].mean()
        c_pre_mean = df[(df[treatment_col] == 0) & (df[time_col] == 0)][outcome_col].mean()
        c_post_mean = df[(df[treatment_col] == 0) & (df[time_col] == 1)][outcome_col].mean()

        parallel_trend_data = {
            "xAxis": {"type": "category", "data": ["处理前", "处理后"]},
            "yAxis": {"type": "value", "name": outcome_col},
            "series": [
                {
                    "name": "处理组",
                    "type": "line",
                    "data": [
                        [0, float(t_pre_mean) if not np.isnan(t_pre_mean) else 0],
                        [1, float(t_post_mean) if not np.isnan(t_post_mean) else 0],
                    ],
                    "itemStyle": {"color": "#10b981"},
                    "lineStyle": {"width": 3},
                    "symbol": "circle",
                    "symbolSize": 10,
                },
                {
                    "name": "控制组",
                    "type": "line",
                    "data": [
                        [0, float(c_pre_mean) if not np.isnan(c_pre_mean) else 0],
                        [1, float(c_post_mean) if not np.isnan(c_post_mean) else 0],
                    ],
                    "itemStyle": {"color": "#8b5cf6"},
                    "lineStyle": {"width": 3},
                    "symbol": "circle",
                    "symbolSize": 10,
                },
            ],
            "tooltip": {
                "trigger": "axis",
                "formatter": "{b}<br/>处理组: {c0}<br/>控制组: {c1}"
            },
            "legend": {"top": "0%"},
        }
        plots.append(DiagnosticPlot(
            name="平行趋势检验",
            chart_type="line",
            data=parallel_trend_data,
            title="平行趋势检验",
            description="比较处理组和控制组在处理前后的结果变化。如果处理前两组趋势平行，则DID估计可靠。",
        ))

        # 2. DID效应分解柱状图 - 展示各组变化量
        t_change = t_post_mean - t_pre_mean if not np.isnan(t_post_mean) and not np.isnan(t_pre_mean) else 0
        c_change = c_post_mean - c_pre_mean if not np.isnan(c_post_mean) and not np.isnan(c_pre_mean) else 0
        did_effect = t_change - c_change

        effect_data = {
            "xAxis": {"type": "category", "data": ["处理组变化", "控制组变化", "DID效应"]},
            "yAxis": {"type": "value", "name": "变化量"},
            "series": [
                {
                    "name": "效应值",
                    "type": "bar",
                    "data": [
                        {"value": float(t_change), "itemStyle": {"color": "#10b981"}},
                        {"value": float(c_change), "itemStyle": {"color": "#8b5cf6"}},
                        {"value": float(did_effect), "itemStyle": {"color": "#ef4444"}},
                    ],
                    "label": {"show": True, "position": "top"},
                },
            ],
            "tooltip": {"trigger": "axis"},
        }
        plots.append(DiagnosticPlot(
            name="DID效应分解",
            chart_type="bar",
            data=effect_data,
            title="DID效应分解",
            description="展示处理组和对照组的变化量，以及净处理效应（DID = 处理组变化 - 对照组变化）。",
        ))

        # 3. 各组样本量分布
        sample_size_data = {
            "xAxis": {"type": "category", "data": ["处理组-前", "处理组-后", "对照组-前", "对照组-后"]},
            "yAxis": {"type": "value", "name": "样本数"},
            "series": [
                {
                    "name": "样本量",
                    "type": "bar",
                    "data": [
                        int(df[(df[treatment_col] == 1) & (df[time_col] == 0)].shape[0]),
                        int(df[(df[treatment_col] == 1) & (df[time_col] == 1)].shape[0]),
                        int(df[(df[treatment_col] == 0) & (df[time_col] == 0)].shape[0]),
                        int(df[(df[treatment_col] == 0) & (df[time_col] == 1)].shape[0]),
                    ],
                    "itemStyle": {"color": "#3b82f6"},
                    "label": {"show": True, "position": "top"},
                },
            ],
            "tooltip": {"trigger": "axis"},
        }
        plots.append(DiagnosticPlot(
            name="样本量分布",
            chart_type="bar",
            data=sample_size_data,
            title="各组样本量分布",
            description="展示各组的样本数量，确保各组样本量足够进行统计推断。",
        ))

        return plots
