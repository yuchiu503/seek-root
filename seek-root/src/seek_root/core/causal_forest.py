"""因果森林（Causal Forest）分析器模块。

因果森林是一种基于机器学习的异质性处理效应估计方法。
它通过随机森林的方式估计每个样本的条件平均处理效应（CATE）。

原理:
    条件平均处理效应:
    CATE(x) = E[Y(1) - Y(0) | X = x]

    因果森林的核心思想:
    1. 对每个样本构建"伪结果"（pseudo-outcome）
    2. 使用随机森林在协变量空间上预测 CATE
    3. 通过分裂准则（如最大化处理效应的异质性）来构建树

    简化实现:
    1. 估计倾向得分 p(X) = P(T=1|X)
    2. 估计条件均值 m(X) = E[Y|X]
    3. 计算伪结果: Y_i^* = (T_i - p(X_i)) * (Y_i - m(X_i)) / (p(X_i) * (1 - p(X_i)))
    4. 使用回归树或随机森林预测 CATE(X) = E[Y*|X]

适用场景:
    - 个性化推荐和定价策略
    - 靶向营销和客户分层
    - 医疗决策的个体化治疗方案
    - 政策效果的异质性分析
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
class CausalForestConfig:
    """CausalForest分析配置数据类。

    参数:
        treatment_col: 处理变量列名
        outcome_col: 结果变量列名
        covariates: 协变量列名列表
        n_estimators: 树的数量（默认100）
        max_depth: 最大深度（默认6）
        min_samples_split: 最小分裂样本数（默认5）
        random_state: 随机种子
    """

    treatment_col: str
    outcome_col: str
    covariates: List[str]
    n_estimators: int = 100
    max_depth: int = 6
    min_samples_split: int = 5
    random_state: int = 42


class CausalForestAnalyzer(BaseCausalAnalyzer):
    """因果森林分析器。

    使用简化的因果森林实现，基于AIPW估计器。

    参数:
        data (pl.DataFrame): Polars DataFrame
        config (Dict[str, Any]): 配置字典

    示例:
        >>> df = pl.DataFrame({
        ...     "treated": [0,0,1,1,0,0,1,1],
        ...     "age": [25,30,35,40,28,32,38,42],
        ...     "income": [50,60,55,70,52,61,56,72],
        ...     "outcome": [100,110,130,150,105,115,135,155]
        ... })
        >>> analyzer = CausalForestAnalyzer(data=df, config={
        ...     "treatment_col": "treated",
        ...     "outcome_col": "outcome",
        ...     "covariates": ["age", "income"]
        ... })
        >>> analyzer.fit()
    """

    def __init__(self, data: pl.DataFrame, config: Dict[str, Any]) -> None:
        """初始化CausalForest分析器。

        参数:
            data: 输入数据
            config: 配置字典
        """
        super().__init__(data, config)
        self.config = CausalForestConfig(
            treatment_col=config["treatment_col"],
            outcome_col=config["outcome_col"],
            covariates=config["covariates"],
            n_estimators=config.get("n_estimators", 100),
            max_depth=config.get("max_depth", 6),
            min_samples_split=config.get("min_samples_split", 5),
            random_state=config.get("random_state", 42),
        )

    def validate_config(self) -> Tuple[bool, Optional[str]]:
        """验证CausalForest配置是否有效。

        返回:
            tuple: (是否有效, 错误消息)
        """
        required = [self.config.treatment_col, self.config.outcome_col] + self.config.covariates
        valid, msg = self.check_required_columns(self.data, required)
        if not valid:
            return False, msg

        T = self.data[self.config.treatment_col].to_numpy()
        n_treated = np.sum(T == 1)
        n_control = np.sum(T == 0)

        if n_treated < 5:
            return False, f"处理组样本量不足（当前{n_treated}，建议至少5个）"
        if n_control < 5:
            return False, f"对照组样本量不足（当前{n_control}，建议至少5个）"

        return True, None

    def fit(self) -> None:
        """执行CausalForest估计。

        使用简化的AIPW（Augmented Inverse Probability Weighting）方法，
        结合随机森林估计异质性处理效应。

        返回:
            None: 结果存入 self._result 属性
        """
        from sklearn.ensemble import RandomForestRegressor, RandomForestClassifier
        from scipy import stats

        valid, msg = self.validate_config()
        if not valid:
            raise ValueError(f"配置验证失败: {msg}")

        T = self.config.treatment_col
        Y = self.config.outcome_col
        X_cols = self.config.covariates

        df = self.data.to_pandas()

        X = df[X_cols].values
        treatment = df[T].values
        outcome = df[Y].values

        # 1. 估计倾向得分 p(X) = P(T=1|X)
        ps_model = RandomForestClassifier(
            n_estimators=self.config.n_estimators // 2,
            max_depth=self.config.max_depth,
            random_state=self.config.random_state,
            min_samples_split=self.config.min_samples_split,
        )
        ps_model.fit(X, treatment)
        propensity_scores = ps_model.predict_proba(X)[:, 1]

        # 确保倾向得分不过于接近0或1
        propensity_scores = np.clip(propensity_scores, 0.05, 0.95)

        # 2. 估计条件均值 m(X) = E[Y|X,T=t]
        # 对处理组和对照组分别建模
        treated_mask = treatment == 1
        control_mask = treatment == 0

        # 处理组模型
        if np.sum(treated_mask) > 5:
            m1_model = RandomForestRegressor(
                n_estimators=self.config.n_estimators // 2,
                max_depth=self.config.max_depth,
                random_state=self.config.random_state,
                min_samples_split=self.config.min_samples_split,
            )
            m1_model.fit(X[treated_mask], outcome[treated_mask])
            m1_hat = m1_model.predict(X)
        else:
            m1_hat = np.mean(outcome[treated_mask]) * np.ones(len(df))

        # 对照组模型
        if np.sum(control_mask) > 5:
            m0_model = RandomForestRegressor(
                n_estimators=self.config.n_estimators // 2,
                max_depth=self.config.max_depth,
                random_state=self.config.random_state,
                min_samples_split=self.config.min_samples_split,
            )
            m0_model.fit(X[control_mask], outcome[control_mask])
            m0_hat = m0_model.predict(X)
        else:
            m0_hat = np.mean(outcome[control_mask]) * np.ones(len(df))

        # 3. 计算伪结果（AIPW score）
        # 正确的个体处理效应估计:
        # τ_i(x) = m1(x) - m0(x) + T*(Y-m1)/p - (1-T)*(Y-m0)/(1-p)
        pseudo_outcomes = np.zeros(len(df))
        for i in range(len(df)):
            if treatment[i] == 1:
                # 处理组: 使用 p(X_i)
                pseudo_outcomes[i] = (m1_hat[i] - m0_hat[i]
                                    + (outcome[i] - m1_hat[i]) / propensity_scores[i])
            else:
                # 对照组: 使用 1-p(X_i)
                pseudo_outcomes[i] = (m1_hat[i] - m0_hat[i]
                                    - (outcome[i] - m0_hat[i]) / (1 - propensity_scores[i]))

        # 4. 使用随机森林预测 CATE(X) = E[Y*|X]
        cate_model = RandomForestRegressor(
            n_estimators=self.config.n_estimators,
            max_depth=self.config.max_depth,
            random_state=self.config.random_state,
            min_samples_split=self.config.min_samples_split,
        )
        cate_model.fit(X, pseudo_outcomes)
        cate_pred = cate_model.predict(X)

        # 5. 汇总统计
        tau = np.mean(cate_pred)
        tau_std = np.std(cate_pred)
        tau_se = tau_std / np.sqrt(len(df))

        t_stat = tau / tau_se
        p_value = 2 * stats.norm.sf(abs(t_stat))

        is_significant = p_value < 0.05

        ci_lower = tau - 1.96 * tau_se
        ci_upper = tau + 1.96 * tau_se

        # 6. 诊断图表
        diagnostic_plots = self._generate_diagnostic_plots(df, cate_pred, treatment, outcome, X_cols)

        self._result = AnalysisResult(
            method=CausalMethod.CAUSAL_FOREST,
            effect_estimate=float(tau),
            confidence_interval=(float(ci_lower), float(ci_upper)),
            p_value=float(p_value),
            standard_error=float(tau_se),
            sample_size=len(df),
            treatment_size=int(treatment.sum()),
            control_size=int((1 - treatment).sum()),
            is_significant=is_significant,
            diagnostic_plots=diagnostic_plots,
            metadata={
                "tau": float(tau),
                "tau_std": float(tau_std),
                "cate_distribution": self._get_cate_distribution(cate_pred),
                "covariates": X_cols,
                "individual_effects": cate_pred.tolist()[:50],  # 取前50个样本的个体效应
            },
        )
        self._is_fitted = True

    def _get_cate_distribution(self, cate_pred: np.ndarray) -> Dict[str, float]:
        """获取CATE分布统计量。

        参数:
            cate_pred: 条件平均处理效应预测值

        返回:
            dict: 分布统计量
        """
        return {
            "mean": float(np.mean(cate_pred)),
            "std": float(np.std(cate_pred)),
            "min": float(np.min(cate_pred)),
            "max": float(np.max(cate_pred)),
            "q25": float(np.percentile(cate_pred, 25)),
            "q50": float(np.percentile(cate_pred, 50)),
            "q75": float(np.percentile(cate_pred, 75)),
        }

    def _generate_diagnostic_plots(
        self,
        df: pd.DataFrame,
        cate_pred: np.ndarray,
        treatment: np.ndarray,
        outcome: np.ndarray,
        X_cols: List[str],
    ) -> List[DiagnosticPlot]:
        """生成CausalForest诊断图表。

        返回:
            List[DiagnosticPlot]: 诊断图表列表
        """
        plots = []

        # 1. CATE分布直方图
        n_bins = 15
        hist, bin_edges = np.histogram(cate_pred, bins=n_bins)

        cate_hist_data = {
            "title": {"text": "条件平均处理效应分布"},
            "xAxis": {
                "type": "category",
                "data": [f"{bin_edges[i]:.2f}" for i in range(n_bins)],
                "name": "CATE值",
            },
            "yAxis": {"type": "value", "name": "样本数"},
            "series": [
                {
                    "name": "样本数",
                    "type": "bar",
                    "data": [int(h) for h in hist],
                    "itemStyle": {"color": "#8b5cf6"},
                    "label": {"show": True, "position": "top"},
                },
            ],
        }
        plots.append(DiagnosticPlot(
            name="CATE分布",
            chart_type="bar",
            data=cate_hist_data,
            title="条件平均处理效应分布",
            description="展示每个样本的条件平均处理效应分布，反映处理效应的异质性。",
        ))

        # 2. 个体效应 vs 协变量（取第一个协变量）
        if len(X_cols) > 0:
            x_col = X_cols[0]
            scatter_data = {
                "title": {"text": f"CATE vs {x_col}"},
                "xAxis": {"type": "value", "name": x_col},
                "yAxis": {"type": "value", "name": "CATE"},
                "series": [
                    {
                        "type": "scatter",
                        "data": [
                            [float(x), float(y)]
                            for x, y in zip(df[x_col], cate_pred)
                        ],
                        "itemStyle": {"color": "#3b82f6"},
                    },
                ],
            }
            plots.append(DiagnosticPlot(
                name="CATE vs 协变量",
                chart_type="scatter",
                data=scatter_data,
                title="CATE vs 协变量",
                description=f"展示CATE随协变量{x_col}的变化，用于识别异质性来源。",
            ))

        # 3. 处理效应排序（top/bottom groups）
        sorted_idx = np.argsort(cate_pred)
        n_groups = 5
        group_size = len(cate_pred) // n_groups

        group_means = []
        for i in range(n_groups):
            start = i * group_size
            end = (i + 1) * group_size if i < n_groups - 1 else len(cate_pred)
            group_means.append(float(np.mean(cate_pred[sorted_idx[start:end]])))

        ranking_data = {
            "title": {"text": "CATE分组排序"},
            "xAxis": {"type": "category", "data": [f"第{i+1}组（低→高）" for i in range(n_groups)]},
            "yAxis": {"type": "value", "name": "平均CATE"},
            "series": [
                {
                    "type": "bar",
                    "data": [gm for gm in group_means],
                    "itemStyle": {"color": "#10b981"},
                    "label": {"show": True, "position": "top"},
                },
            ],
        }
        plots.append(DiagnosticPlot(
            name="CATE分组排序",
            chart_type="bar",
            data=ranking_data,
            title="CATE分组排序",
            description="将样本按CATE排序后分组，展示不同组的平均处理效应，用于识别受益群体。",
        ))

        return plots
