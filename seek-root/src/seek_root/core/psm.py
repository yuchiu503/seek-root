"""倾向得分匹配（Propensity Score Matching）分析器模块。

倾向得分匹配是一种用于处理选择偏差的因果推断方法。
通过估计每个样本进入处理组的概率（倾向得分），
然后为每个处理组样本匹配相似的对照组样本，
从而构造近似随机的对照组，估计处理效应。

原理:
    倾向得分 e(X) = P(T=1 | X) = P(处理 | 给定协变量X)

    匹配后:
    ATT = E[Y(1) | T=1)] - E[Y(0) | T=1]

    使用最近邻匹配:
    对每个处理组样本 i，找到对照组样本 j，使 |e(X_i) - e(X_j)| 最小。

适用场景:
    - 评估培训项目效果
    - 评估医疗干预效果
    - 处理非随机分配的选择偏差
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
class PSMConfig:
    """PSM分析配置数据类。

    参数:
        treatment_col: 处理组标识列名（值为0/1或布尔值）
        outcome_col: 结果变量列名
        covariates: 协变量列名列表
        n_neighbors: 最近邻匹配数量（默认1）
        caliper: 卡尺值（可选，用于半径匹配）
        replace: 是否允许有放回匹配（默认False）
    """

    treatment_col: str
    outcome_col: str
    covariates: List[str]
    n_neighbors: int = 1
    caliper: Optional[float] = None
    replace: bool = False


class PSMAnalyzer(BaseCausalAnalyzer):
    """倾向得分匹配分析器。

    通过逻辑回归估计倾向得分，执行最近邻匹配，
    并计算匹配后的处理效应。

    参数:
        data (pl.DataFrame): Polars DataFrame
        config (Dict[str, Any]): 分析配置

    示例:
        >>> df = pl.DataFrame({
        ...     "is_treated": [0,0,1,1,0,0,1,1],
        ...     "age": [25,30,35,40,28,32,38,42],
        ...     "income": [50,60,55,70,52,61,56,72],
        ...     "outcome": [100,110,130,150,105,115,135,155]
        ... })
        >>> analyzer = PSMAnalyzer(data=df, config={
        ...     "treatment_col": "is_treated",
        ...     "outcome_col": "outcome",
        ...     "covariates": ["age", "income"]
        ... })
        >>> analyzer.fit()
        >>> result = analyzer.get_result()
    """

    def __init__(self, data: pl.DataFrame, config: Dict[str, Any]) -> None:
        """初始化PSM分析器。

        参数:
            data: 输入的Polars DataFrame
            config: 配置字典
        """
        super().__init__(data, config)
        self.config = PSMConfig(
            treatment_col=config["treatment_col"],
            outcome_col=config["outcome_col"],
            covariates=config["covariates"],
            n_neighbors=config.get("n_neighbors", 1),
            caliper=config.get("caliper"),
            replace=config.get("replace", False),
        )
        self._propensity_scores = None

    def validate_config(self) -> Tuple[bool, Optional[str]]:
        """验证PSM配置是否有效。

        返回:
            tuple: (是否有效, 错误消息)
        """
        required = [self.config.treatment_col, self.config.outcome_col] + self.config.covariates
        valid, msg = self.check_required_columns(self.data, required)
        if not valid:
            return False, msg

        treatment_n = self.data.filter(pl.col(self.config.treatment_col) == 1).height
        control_n = self.data.filter(pl.col(self.config.treatment_col) == 0).height

        if treatment_n < 2:
            return False, f"处理组样本量不足（当前{treatment_n}）"
        if control_n < 2:
            return False, f"对照组样本量不足（当前{control_n}）"

        return True, None

    def fit(self) -> None:
        """执行PSM估计。

        估计倾向得分，进行最近邻匹配，计算处理效应。

        返回:
            None: 结果存入 self._result 属性
        """
        from sklearn.linear_model import LogisticRegression
        from sklearn.neighbors import NearestNeighbors
        from scipy import stats

        valid, msg = self.validate_config()
        if not valid:
            raise ValueError(f"配置验证失败: {msg}")

        T = self.config.treatment_col
        Y = self.config.outcome_col
        X_cols = self.config.covariates

        df = self.data.to_pandas()

        # 1. 估计倾向得分（逻辑回归）
        X = df[X_cols].values
        treatment = df[T].values
        outcome = df[Y].values

        ps_model = LogisticRegression(max_iter=1000, random_state=42)
        ps_model.fit(X, treatment)
        propensity_scores = ps_model.predict_proba(X)[:, 1]
        self._propensity_scores = propensity_scores

        # 2. 执行匹配
        treatment_idx = np.where(treatment == 1)[0]
        control_idx = np.where(treatment == 0)[0]

        # 为每个处理组样本匹配最近邻
        nbrs = NearestNeighbors(n_neighbors=self.config.n_neighbors, algorithm='ball_tree')
        nbrs.fit(propensity_scores[control_idx].reshape(-1, 1))

        matched_pairs = []
        matched_control_indices = []

        for t_idx in treatment_idx:
            t_ps = propensity_scores[t_idx]
            distances, indices = nbrs.kneighbors([[t_ps]])
            for j in range(self.config.n_neighbors):
                # indices[0][j] 是拟合数组中的位置，需要转换回原始数据索引
                c_idx = int(control_idx[indices[0][j]])
                if not self.config.caliper or distances[0][j] <= self.config.caliper:
                    matched_pairs.append((int(t_idx), c_idx))
                    matched_control_indices.append(c_idx)

        # 3. 计算匹配后的处理效应
        if not matched_pairs:
            raise RuntimeError("没有找到有效匹配")

        treatment_effects = []
        for t_idx, c_idx in matched_pairs:
            treatment_effects.append(outcome[t_idx] - outcome[c_idx])

        att = np.mean(treatment_effects)
        std_err = np.std(treatment_effects) / np.sqrt(len(treatment_effects))

        # 4. 计算p值
        t_stat = att / std_err
        p_value = 2 * stats.norm.sf(abs(t_stat))

        is_significant = p_value < 0.05

        ci_lower = att - 1.96 * std_err
        ci_upper = att + 1.96 * std_err

        # 5. 生成诊断图表
        diagnostic_plots = self._generate_diagnostic_plots(df, propensity_scores, treatment)

        self._result = AnalysisResult(
            method=CausalMethod.PSM,
            effect_estimate=float(att),
            confidence_interval=(float(ci_lower), float(ci_upper)),
            p_value=float(p_value),
            standard_error=float(std_err),
            sample_size=len(df),
            treatment_size=int(treatment.sum()),
            control_size=int((1 - treatment).sum()),
            is_significant=is_significant,
            diagnostic_plots=diagnostic_plots,
            metadata={
                "att": float(att),
                "n_matched_pairs": len(matched_pairs),
                "propensity_scores": propensity_scores.tolist(),
                "covariates_balance": self._check_covariate_balance(df, propensity_scores, treatment),
                "covariates": X_cols,
            },
        )
        self._is_fitted = True

    def _check_covariate_balance(
        self,
        df: pd.DataFrame,
        propensity_scores: np.ndarray,
        treatment: np.ndarray,
    ) -> Dict[str, float]:
        """检查匹配后协变量的平衡性。

        计算标准化均值差异（Standardized Mean Difference），
        |SMD| < 0.1 表示平衡性良好。

        参数:
            df: 数据框
            propensity_scores: 倾向得分
            treatment: 处理指示

        返回:
            dict: 各协变量的 SMD 值
        """
        balance = {}
        for cov in self.config.covariates:
            cov_values = df[cov].values
            treat_mean = cov_values[treatment == 1].mean()
            control_mean = cov_values[treatment == 0].mean()
            pooled_std = np.sqrt(
                (cov_values[treatment == 1].var() + cov_values[treatment == 0].var()) / 2)
            if pooled_std > 0:
                smd = (treat_mean - control_mean) / pooled_std
            else:
                smd = 0
            balance[cov] = float(smd)

        return balance

    def _generate_diagnostic_plots(
        self,
        df: pd.DataFrame,
        propensity_scores: np.ndarray,
        treatment: np.ndarray,
    ) -> List[DiagnosticPlot]:
        """生成PSM诊断图表。

        返回:
            List[DiagnosticPlot]: 诊断图表列表
        """
        plots = []

        # 1. 倾向得分分布图
        treatment_ps = propensity_scores[treatment == 1]
        control_ps = propensity_scores[treatment == 0]

        ps_distribution_data = {
            "title": {"text": "倾向得分分布对比"},
            "xAxis": {"type": "value", "name": "倾向得分", "min": 0, "max": 1},
            "yAxis": {"type": "value", "name": "样本密度"},
            "series": [
                {
                    "name": "处理组",
                    "type": "bar",
                    "data": [{"value": float(x)} for x in treatment_ps],
                    "itemStyle": {"color": "#10b981"},
                },
                {
                    "name": "控制组",
                    "type": "bar",
                    "data": [{"value": float(x)} for x in control_ps],
                    "itemStyle": {"color": "#8b5cf6"},
                },
            ],
        }
        plots.append(DiagnosticPlot(
            name="倾向得分分布",
            chart_type="bar",
            data=ps_distribution_data,
            title="倾向得分分布",
            description="处理组和对照组的倾向得分分布。匹配后两组分布应更接近。",
        ))

        # 2. 协变量平衡性检验
        balance_data = self._check_covariate_balance(df, propensity_scores, treatment)
        covariate_balance_data = {
            "title": {"text": "协变量平衡性检验"},
            "xAxis": {"type": "category", "data": list(balance_data.keys())},
            "yAxis": {"type": "value", "name": "标准化均值差异 (SMD)"},
            "series": [
                {
                    "name": "SMD值",
                    "type": "bar",
                    "data": [float(v) for v in balance_data.values()],
                    "itemStyle": {"color": "#3b82f6"},
                    "label": {"show": True, "position": "top"},
                    "markLine": {
                        "data": [
                            {"yAxis": 0.1, "name": "良好平衡阈值"},
                            {"yAxis": -0.1},
                        ],
                        "lineStyle": {"color": "#ef4444", "type": "dashed"},
                    },
                },
            ],
        }
        plots.append(DiagnosticPlot(
            name="协变量平衡性检验",
            chart_type="bar",
            data=covariate_balance_data,
            title="协变量平衡性",
            description="|SMD| < 0.1 表示协变量在匹配后平衡性良好。",
        ))

        return plots
