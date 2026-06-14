"""工具变量法（Instrumental Variables）分析器模块。

工具变量法用于处理内生性问题（处理变量与误差项相关）的情况。
当存在内生性时，普通的回归估计会产生偏误，
工具变量法通过找到与内生处理变量相关、但与误差项无关的变量（工具变量），
来获得处理效应的一致估计。

原理:
    两阶段最小二乘法（2SLS）：
    第一阶段：T = α + βZ + X*γ + ε （将处理变量对工具变量回归）
    第二阶段：Y = α + β*T_hat + X*γ + ε （用T_hat替代T进行回归）

    有效工具变量需要满足：
    1. 相关性：工具变量与内生处理变量相关（相关性检验）
    2. 排他性：工具变量只通过处理变量影响结果（排除限制）
    3. 外生性：工具变量与误差项无关

适用场景:
    - 处理遗漏变量偏误
    - 处理测量误差
    - 处理选择偏差
    - 政策评估（如使用距离作为工具变量）

参考文献:
    - Angrist, J. D., & Pischke, J. S. (2009). Mostly Harmless Econometrics
    - Wooldridge, J. M. (2010). Econometric Analysis of Cross Section and Panel Data
"""

from typing import Any, Dict, List, Optional
import polars as pl
import pandas as pd
import numpy as np
from dataclasses import dataclass

from seek_root.core.base import (
    BaseCausalAnalyzer,
    CausalMethod,
    AnalysisResult,
    DiagnosticPlot,
)


@dataclass
class IVConfig:
    """工具变量法配置数据类。

    用于存储和验证工具变量分析的参数配置。

    属性:
        instrument_col: 工具变量列名
        treatment_col: 内生处理变量列名
        outcome_col: 结果变量列名
        covariates: 外生协变量列名列表（可选）
        method: 估计方法 ('2sls', 'liml', 'gmm')
    """

    instrument_col: str
    treatment_col: str
    outcome_col: str
    covariates: List[str] = None
    method: str = "2sls"

    def __post_init__(self) -> None:
        """初始化后处理，确保covariates不为None。"""
        if self.covariates is None:
            self.covariates = []


class IVAnalyzer(BaseCausalAnalyzer):
    """工具变量法分析器。

    使用两阶段最小二乘法（2SLS）或其他方法，
    通过工具变量估计内生处理变量的因果效应。

    参数:
        data (pl.DataFrame): Polars DataFrame，包含分析所需的全部列
        config (Dict[str, Any]): 分析配置，包含:
            - instrument_col: 工具变量列名
            - treatment_col: 内生处理变量列名
            - outcome_col: 结果变量列名
            - covariates: 协变量列表（可选）
            - method: 估计方法

    示例:
        >>> df = pl.DataFrame({
        ...     "distance": [1,2,3,4,5,6,7,8],
        ...     "education": [10,12,14,16,12,14,16,18],
        ...     "income": [30,40,50,60,45,55,65,75]
        ... })
        >>> analyzer = IVAnalyzer(data=df, config={
        ...     "instrument_col": "distance",
        ...     "treatment_col": "education",
        ...     "outcome_col": "income"
        ... })
        >>> analyzer.fit()
        >>> result = analyzer.get_result()
    """

    def __init__(self, data: pl.DataFrame, config: Dict[str, Any]) -> None:
        """初始化工具变量分析器。

        参数:
            data: 输入的Polars DataFrame数据
            config: 分析配置字典
        """
        super().__init__(data, config)
        self.config = IVConfig(
            instrument_col=config["instrument_col"],
            treatment_col=config["treatment_col"],
            outcome_col=config["outcome_col"],
            covariates=config.get("covariates", []),
            method=config.get("method", "2sls"),
        )

    def validate_config(self) -> tuple[bool, Optional[str]]:
        """验证工具变量配置是否有效。

        检查必需列是否存在。

        返回:
            tuple: (是否有效, 错误消息)
        """
        required = [
            self.config.instrument_col,
            self.config.treatment_col,
            self.config.outcome_col,
        ]
        valid, msg = self.check_required_columns(self.data, required)
        if not valid:
            return False, msg

        # 检查协变量列
        if self.config.covariates:
            valid, msg = self.check_required_columns(self.data, self.config.covariates)
            if not valid:
                return False, msg

        # 检查工具变量和处理变量是否有足够变异
        for col in [self.config.instrument_col, self.config.treatment_col]:
            n_unique = self.data[col].n_unique()
            if n_unique < 2:
                return False, f"变量 {col} 缺乏变异，无法进行IV估计"

        return True, None

    def fit(self) -> None:
        """执行工具变量估计。

        使用两阶段最小二乘法（2SLS）估计因果效应。

        方法:
            第一阶段：将内生处理变量对工具变量和外生协变量回归
            第二阶段：将结果变量对工具变量估计值和外生协变量回归

        返回:
            None: 结果存入 self._result 属性
        """
        import statsmodels.api as sm
        from statsmodels.sandbox.regression.gmm import IV2SLS

        # 验证配置
        valid, msg = self.validate_config()
        if not valid:
            raise ValueError(f"配置验证失败: {msg}")

        # 获取配置
        Z = self.config.instrument_col  # 工具变量
        T = self.config.treatment_col  # 内生处理变量
        Y = self.config.outcome_col   # 结果变量
        X = self.config.covariates     # 外生协变量

        # 转换为Pandas
        df = self._convert_to_pandas()

        # 准备变量
        y = df[Y].values
        t = df[T].values
        z = df[Z].values.reshape(-1, 1)

        if X:
            x_exog = df[X].values
            # 添加常数项
            x_exog = sm.add_constant(x_exog)
        else:
            x_exog = None

        # =====================
        # 第一阶段回归
        # =====================
        if x_exog is not None:
            X_first = np.column_stack([z, x_exog])
        else:
            X_first = z
        X_first = sm.add_constant(X_first)

        first_stage = sm.OLS(t, X_first).fit()

        # 获取第一阶段拟合值
        t_hat = first_stage.predict(X_first)

        # 计算第一阶段F统计量（弱工具变量检验）
        f_stat = first_stage.fvalue
        r_squared = first_stage.rsquared

        # =====================
        # 第二阶段回归
        # =====================
        if x_exog is not None:
            X_second = np.column_stack([t_hat, x_exog])
        else:
            X_second = t_hat.reshape(-1, 1)
        X_second = sm.add_constant(X_second)

        second_stage = sm.OLS(y, X_second).fit()

        # 提取结果
        iv_coef = second_stage.params[1]  # 处理变量的系数
        iv_std_err = second_stage.bse[1]
        iv_pvalue = second_stage.pvalues[1]
        conf_int = (second_stage.conf_int()[1, 0], second_stage.conf_int()[1, 1])

        # 处理组样本量（使用工具变量的样本）
        n_samples = len(df)
        treatment_n = len(df[df[T] > df[T].median()])  # 简化：大于中位数视为处理组
        control_n = n_samples - treatment_n

        # 生成诊断图表
        diagnostic_plots = self._generate_diagnostic_plots(
            df, T, Y, Z, t, y, z, t_hat, first_stage, second_stage
        )

        # 构建结果
        self._result = AnalysisResult(
            method=CausalMethod.IV,
            effect_estimate=float(iv_coef),
            confidence_interval=(float(conf_int[0]), float(conf_int[1])),
            p_value=float(iv_pvalue),
            standard_error=float(iv_std_err),
            sample_size=n_samples,
            treatment_size=treatment_n,
            control_size=control_n,
            is_significant=(iv_pvalue < 0.05),
            diagnostic_plots=diagnostic_plots,
            metadata={
                "iv_estimate": float(iv_coef),
                "first_stage_f_stat": float(f_stat),
                "first_stage_r_squared": float(r_squared),
                "instrument": Z,
                "treatment": T,
                "outcome": Y,
                "covariates": X,
            },
        )

        self._is_fitted = True

    def _generate_diagnostic_plots(
        self,
        df: pd.DataFrame,
        treatment_col: str,
        outcome_col: str,
        instrument_col: str,
        t: np.ndarray,
        y: np.ndarray,
        z: np.ndarray,
        t_hat: np.ndarray,
        first_stage: Any,
        second_stage: Any,
    ) -> List[DiagnosticPlot]:
        """生成工具变量诊断图表。

        生成第一阶段拟合图、Reduced Form图等。

        参数:
            df: Pandas DataFrame
            treatment_col: 处理变量列名
            outcome_col: 结果变量列名
            instrument_col: 工具变量列名
            t: 处理变量数组
            y: 结果变量数组
            z: 工具变量数组
            t_hat: 第一阶段预测值
            first_stage: 第一阶段回归结果
            second_stage: 第二阶段回归结果

        返回:
            List[DiagnosticPlot]: 诊断图表列表
        """
        plots = []

        # 1. 第一阶段：工具变量 vs 处理变量（带拟合线）
        # 简化：用分箱均值展示
        n_bins = 10
        df_temp = pd.DataFrame({instrument_col: z, treatment_col: t})
        df_temp["_bin"] = pd.cut(df_temp[instrument_col], bins=n_bins)
        binned = df_temp.groupby("_bin")[treatment_col].mean().reset_index()
        binned["bin_center"] = binned["_bin"].apply(lambda x: x.mid)

        first_stage_data = {
            "xAxis": {"type": "value", "name": instrument_col},
            "yAxis": {"type": "value", "name": treatment_col},
            "series": [
                {
                    "name": "实际值（分箱均值）",
                    "type": "scatter",
                    "data": [[row["bin_center"], row[treatment_col]] for _, row in binned.iterrows()],
                    "symbolSize": 10,
                    "itemStyle": {"color": "#10b981"},
                },
                {
                    "name": "拟合线",
                    "type": "line",
                    "data": sorted([[z.min(), first_stage.params[0] + first_stage.params[1] * z.min()],
                                   [z.max(), first_stage.params[0] + first_stage.params[1] * z.max()]], key=lambda x: x[0]),
                    "lineStyle": {"color": "#ef4444"},
                },
            ],
        }
        plots.append(DiagnosticPlot(
            name="第一阶段关系",
            chart_type="line",
            data=first_stage_data,
            title="第一阶段：工具变量与处理变量关系",
            description=f"检验工具变量与处理变量的相关性。第一阶段F统计量={first_stage.fvalue:.2f}",
        ))

        # 2. Reduced Form：工具变量 vs 结果变量
        df_temp2 = pd.DataFrame({instrument_col: z, outcome_col: y})
        df_temp2["_bin"] = pd.cut(df_temp2[instrument_col], bins=n_bins)
        binned2 = df_temp2.groupby("_bin")[outcome_col].mean().reset_index()
        binned2["bin_center"] = binned2["_bin"].apply(lambda x: x.mid)

        # Reduced form回归
        from sklearn.linear_model import LinearRegression
        lr_rf = LinearRegression()
        lr_rf.fit(z.reshape(-1, 1), y)

        reduced_form_data = {
            "xAxis": {"type": "value", "name": instrument_col},
            "yAxis": {"type": "value", "name": outcome_col},
            "series": [
                {
                    "name": "实际值（分箱均值）",
                    "type": "scatter",
                    "data": [[row["bin_center"], row[outcome_col]] for _, row in binned2.iterrows()],
                    "symbolSize": 10,
                    "itemStyle": {"color": "#8b5cf6"},
                },
                {
                    "name": "拟合线",
                    "type": "line",
                    "data": sorted([[z.min(), lr_rf.intercept_ + lr_rf.coef_[0] * z.min()],
                                   [z.max(), lr_rf.intercept_ + lr_rf.coef_[0] * z.max()]], key=lambda x: x[0]),
                    "lineStyle": {"color": "#ef4444"},
                },
            ],
        }
        plots.append(DiagnosticPlot(
            name="Reduced Form关系",
            chart_type="line",
            data=reduced_form_data,
            title="Reduced Form：工具变量与结果变量关系",
            description="展示工具变量对结果变量的总效应（等于工具变量×处理效应的乘积）。",
        ))

        # 3. 仪器强度检验
        strength_data = {
            "xAxis": {"type": "category", "data": ["F统计量", "R²"]},
            "yAxis": {"type": "value", "name": "值"},
            "series": [
                {
                    "name": "统计量",
                    "type": "bar",
                    "data": [
                        {"value": float(first_stage.fvalue), "itemStyle": {"color": "#10b981"}},
                        {"value": float(first_stage.rsquared), "itemStyle": {"color": "#8b5cf6"}},
                    ],
                },
            ],
            "markLine": {
                "data": [{"yAxis": 10, "name": "弱工具变量阈值（F=10）"}],
                "lineStyle": {"color": "#ef4444", "type": "dashed"},
            },
        }
        plots.append(DiagnosticPlot(
            name="工具变量强度检验",
            chart_type="bar",
            data=strength_data,
            title="工具变量强度检验",
            description=f"第一阶段F统计量={first_stage.fvalue:.2f}。F>10表示工具变量足够强。",
        ))

        return plots
