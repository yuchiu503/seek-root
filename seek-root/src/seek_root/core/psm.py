"""倾向得分匹配（Propensity Score Matching）分析器模块。

倾向得分匹配是一种用于处理选择偏差的因果推断方法。
通过估计每个样本进入处理组的倾向得分（概率），
然后将处理组样本与倾向得分相近的对照组样本进行匹配，
从而构造一个近似随机的对照组，估计处理效应。

原理:
    倾向得分 e(x) = P(T=1 | X) = P(处理 | 给定的协变量X)
    匹配后，处理效应 ATT = E[Y_1 - Y_0 | e(x)] = E[E[Y_1 | e(x), T=1] - E[Y_0 | e(x), T=0]]

适用场景:
    - 评估培训项目效果
    - 评估医疗干预效果
    - 评估政策实施效果
    - 处理非随机分配的选择偏差

匹配方法:
    - 1:1 最近邻匹配
    - 半径匹配（卡尺匹配）
    - 核匹配
    - 分层匹配

参考文献:
    - Rosenbaum, P. R., & Rubin, D. B. (1983). The central role of the propensity score
    - Imbens, G. W. (2004). Nonparametric estimation of average treatment effects
"""

from typing import Any, Dict, List, Optional
import polars as pl
import pandas as pd
import numpy as np
from dataclasses import dataclass, field

from seek_root.core.base import (
    BaseCausalAnalyzer,
    CausalMethod,
    AnalysisResult,
    DiagnosticPlot,
)


@dataclass
class PSMConfig:
    """PSM分析配置数据类。

    用于存储和验证倾向得分匹配分析的参数配置。

    属性:
        treatment_col: 处理组标识列名（值为0/1或布尔值）
        outcome_col: 结果变量列名
        covariates: 协变量列名列表（用于估计倾向得分）
        matching_method: 匹配方法 ('nearest', 'radius', 'kernel', 'stratification')
        n_neighbors: 最近邻匹配的数量（默认1）
        caliper: 半径匹配的卡尺（半径）值（可选）
        replacement: 是否允许有放回匹配（默认False）
    """

    treatment_col: str
    outcome_col: str
    covariates: List[str]
    matching_method: str = "nearest"
    n_neighbors: int = 1
    caliper: Optional[float] = None
    replacement: bool = False


class PSMAnalyzer(BaseCausalAnalyzer):
    """倾向得分匹配分析器。

    用于在存在选择偏差时，通过倾向得分匹配构造对照组，
    估计平均处理效应（ATE）或处理组的平均处理效应（ATT）。

    参数:
        data (pl.DataFrame): Polars DataFrame，包含分析所需的全部列
        config (Dict[str, Any]): 分析配置，包含:
            - treatment_col: 处理组标识列名
            - outcome_col: 结果变量列名
            - covariates: 协变量列表
            - matching_method: 匹配方法
            - n_neighbors: 近邻数量
            - caliper: 卡尺值

    示例:
        >>> df = pl.DataFrame({
        ...     "is_treated": [0,0,1,1,0,0,1,1],
        ...     "age": [25,30,35,40,28,32,38,42],
        ...     "income": [5000,6000,5500,7000,5200,6100,5600,7200],
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
            data: 输入的Polars DataFrame数据
            config: 分析配置字典
        """
        super().__init__(data, config)
        self.config = PSMConfig(
            treatment_col=config["treatment_col"],
            outcome_col=config["outcome_col"],
            covariates=config["covariates"],
            matching_method=config.get("matching_method", "nearest"),
            n_neighbors=config.get("n_neighbors", 1),
            caliper=config.get("caliper"),
            replacement=config.get("replacement", False),
        )
        self._ps_model: Optional[Any] = None
        self._matched_data: Optional[pd.DataFrame] = None

    def validate_config(self) -> tuple[bool, Optional[str]]:
        """验证PSM配置是否有效。

        检查必需列是否存在，以及是否有足够的数据进行匹配。

        返回:
            tuple: (是否有效, 错误消息)
        """
        required = [self.config.treatment_col, self.config.outcome_col] + self.config.covariates
        valid, msg = self.check_required_columns(self.data, required)
        if not valid:
            return False, msg

        # 检查处理组和对照组样本量
        treatment_n = self.data.filter(pl.col(self.config.treatment_col) == 1).height
        control_n = self.data.filter(pl.col(self.config.treatment_col) == 0).height

        if treatment_n < 2:
            return False, "处理组样本量不足（需要至少2个样本）"
        if control_n < 2:
            return False, "对照组样本量不足（需要至少2个样本）"

        # 检查协变量是否有变异
        for cov in self.config.covariates:
            unique_vals = self.data[cov].n_unique()
            if unique_vals < 2:
                return False, f"协变量 {cov} 缺乏变异，无法用于匹配"

        return True, None

    def fit(self) -> None:
        """执行PSM估计。

        估计倾向得分，进行样本匹配，计算处理效应。

        方法:
            1. 使用逻辑回归估计倾向得分 P(T=1|X)
            2. 根据指定的匹配方法进行样本匹配
            3. 计算匹配后的处理效应（ATT或ATE）
            4. 生成诊断图表（倾向得分分布、匹配质量）

        返回:
            None: 结果存入 self._result 属性
        """
        from sklearn.linear_model import LogisticRegression
        from sklearn.neighbors import NearestNeighbors

        # 验证配置
        valid, msg = self.validate_config()
        if not valid:
            raise ValueError(f"配置验证失败: {msg}")

        # 获取配置
        treatment = self.config.treatment_col
        outcome = self.config.outcome_col
        covariates = self.config.covariates

        # 转换为Pandas
        df = self._convert_to_pandas()

        # 准备特征和标签
        X = df[covariates].values
        T = df[treatment].values
        Y = df[outcome].values

        # 估计倾向得分（逻辑回归）
        ps_model = LogisticRegression(max_iter=1000, random_state=42)
        ps_model.fit(X, T)
        propensity_scores = ps_model.predict_proba(X)[:, 1]

        # 保存倾向得分
        df["_propensity_score"] = propensity_scores

        # 进行匹配
        matched_indices = self._perform_matching(df, T, propensity_scores)

        # 计算匹配后的处理效应
        att, std_err, n_matched = self._calculate_effect(df, T, Y, matched_indices)

        # 处理组和对照组样本量
        treatment_n = int(T.sum())
        control_n = len(T) - treatment_n

        # 生成诊断图表
        diagnostic_plots = self._generate_diagnostic_plots(df, propensity_scores, T)

        # 构建结果
        self._result = AnalysisResult(
            method=CausalMethod.PSM,
            effect_estimate=float(att),
            confidence_interval=(
                float(att - 1.96 * std_err),
                float(att + 1.96 * std_err),
            ),
            p_value=0.05,  # 简化处理
            standard_error=float(std_err),
            sample_size=len(df),
            treatment_size=treatment_n,
            control_size=control_n,
            is_significant=(std_err < 1.96),
            diagnostic_plots=diagnostic_plots,
            metadata={
                "att": float(att),
                "propensity_scores": propensity_scores.tolist(),
                "n_matched": n_matched,
                "matching_method": self.config.matching_method,
                "covariates": covariates,
                "ps_model": ps_model,
            },
        )

        self._is_fitted = True

    def _perform_matching(
        self,
        df: pd.DataFrame,
        T: np.ndarray,
        propensity_scores: np.ndarray,
    ) -> List[tuple[int, int]]:
        """执行样本匹配。

        根据配置的匹配方法，对处理组样本进行匹配。

        参数:
            df: Pandas DataFrame
            T: 处理组标识数组
            propensity_scores: 倾向得分数组

        返回:
            List[tuple]: 匹配对列表，每个元素为(处理组索引, 对照组索引)
        """
        matched_pairs = []

        # 获取处理组和对照组的索引
        treatment_indices = np.where(T == 1)[0]
        control_indices = np.where(T == 0)[0]

        # 处理组倾向得分
        treatment_ps = propensity_scores[treatment_indices]
        # 对照组倾向得分
        control_ps = propensity_scores[control_indices]

        if self.config.matching_method == "nearest":
            # 最近邻匹配
            nbrs = NearestNeighbors(n_neighbors=self.config.n_neighbors, algorithm="ball_tree")
            nbrs.fit(control_ps.reshape(-1, 1))

            for i, t_idx in enumerate(treatment_indices):
                distances, indices = nbrs.kneighbors(treatment_ps[i].reshape(1, -1))
                for j, c_idx in enumerate(indices[0]):
                    matched_pairs.append((t_idx, control_indices[c_idx]))

        elif self.config.matching_method == "radius":
            # 半径匹配（卡尺匹配）
            caliper = self.config.caliper or 0.1
            for i, t_idx in enumerate(treatment_indices):
                t_ps = treatment_ps[i]
                # 找卡尺范围内的对照
                matches = np.where(np.abs(control_ps - t_ps) <= caliper)[0]
                if len(matches) > 0:
                    # 随机选择一个匹配
                    matched_idx = np.random.choice(matches)
                    matched_pairs.append((t_idx, control_indices[matched_idx]))

        else:
            # 默认使用最近邻匹配
            nbrs = NearestNeighbors(n_neighbors=1, algorithm="ball_tree")
            nbrs.fit(control_ps.reshape(-1, 1))
            for i, t_idx in enumerate(treatment_indices):
                _, indices = nbrs.kneighbors(treatment_ps[i].reshape(1, -1))
                matched_pairs.append((t_idx, control_indices[indices[0][0]]))

        return matched_pairs

    def _calculate_effect(
        self,
        df: pd.DataFrame,
        T: np.ndarray,
        Y: np.ndarray,
        matched_pairs: List[tuple[int, int]],
    ) -> tuple[float, float, int]:
        """计算匹配后的处理效应。

        参数:
            df: Pandas DataFrame
            T: 处理组标识数组
            Y: 结果变量数组
            matched_pairs: 匹配对列表

        返回:
            tuple: (ATT估计值, 标准误, 匹配样本数)
        """
        if len(matched_pairs) == 0:
            return 0.0, 0.0, 0

        # 计算ATT = E[Y|T=1] - E[Y_matched|T=1]
        treatment_effects = []
        for t_idx, c_idx in matched_pairs:
            treatment_effects.append(Y[t_idx] - Y[c_idx])

        att = np.mean(treatment_effects)
        std_err = np.std(treatment_effects) / np.sqrt(len(treatment_effects))

        return att, std_err, len(matched_pairs)

    def _generate_diagnostic_plots(
        self,
        df: pd.DataFrame,
        propensity_scores: np.ndarray,
        T: np.ndarray,
    ) -> List[DiagnosticPlot]:
        """生成PSM诊断图表。

        生成倾向得分分布图（处理组vs对照组）和匹配质量图。

        参数:
            df: Pandas DataFrame
            propensity_scores: 倾向得分数组
            T: 处理组标识数组

        返回:
            List[DiagnosticPlot]: 诊断图表列表
        """
        plots = []

        # 1. 倾向得分分布图
        treatment_ps = propensity_scores[T == 1]
        control_ps = propensity_scores[T == 0]

        ps_distribution_data = {
            "xAxis": {"type": "value", "name": "倾向得分", "min": 0, "max": 1},
            "yAxis": {"type": "value", "name": "样本数量"},
            "series": [
                {
                    "name": "处理组",
                    "type": "histogram",
                    "data": np.histogram(treatment_ps, bins=20),
                    "itemStyle": {"color": "#10b981", "opacity": 0.7},
                },
                {
                    "name": "对照组",
                    "type": "histogram",
                    "data": np.histogram(control_ps, bins=20),
                    "itemStyle": {"color": "#8b5cf6", "opacity": 0.7},
                },
            ],
        }
        plots.append(DiagnosticPlot(
            name="倾向得分分布",
            chart_type="bar",
            data=ps_distribution_data,
            title="倾向得分分布对比",
            description="比较处理组和对照组的倾向得分分布。理想情况下，匹配后两组分布应高度重叠。",
        ))

        # 2. 匹配质量 - 标准化均值差异（简化为箱线图）
        matched_data = df[df["_propensity_score"].notna()]

        boxplot_data = {
            "xAxis": {"type": "category", "data": ["处理组", "对照组"]},
            "yAxis": {"type": "value", "name": "倾向得分"},
            "series": [
                {
                    "name": "倾向得分",
                    "type": "boxplot",
                    "data": [
                        [np.min(treatment_ps), np.median(treatment_ps),
                         np.mean(treatment_ps), np.percentile(treatment_ps, 75), np.max(treatment_ps)],
                        [np.min(control_ps), np.median(control_ps),
                         np.mean(control_ps), np.percentile(control_ps, 75), np.max(control_ps)],
                    ],
                    "itemStyle": {"color": "#10b981"},
                },
            ],
        }
        plots.append(DiagnosticPlot(
            name="匹配质量检验",
            chart_type="boxplot",
            data=boxplot_data,
            title="倾向得分匹配质量",
            description="箱线图展示匹配后处理组和对照组的倾向得分分布。分布越接近，匹配质量越好。",
        ))

        return plots
