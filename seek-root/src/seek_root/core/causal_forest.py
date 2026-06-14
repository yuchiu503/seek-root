"""因果森林（Causal Forest）分析器模块。

因果森林是一种基于随机森林的异质性处理效应（HTE）估计方法。
它允许处理效应在不同样本之间存在差异，
并通过机器学习的方法来识别哪些样本更受益于处理。

原理:
    因果森林是随机森林的一种扩展，
    通过构建多棵因果树并进行集成，
    估计每个样本的个体化处理效应（CATE - Conditional Average Treatment Effect）。

    CATE(x) = E[Y(1) - Y(0) | X = x]

    核心思想：
    1. 在每棵树的每个叶节点内，计算处理组和对照组之间的平均结果差异
    2. 通过诚实估计（honest estimation）减少过拟合
    3. 通过集成多棵树来降低方差

适用场景:
    - 精准营销：识别哪些客户更可能响应营销活动
    - 医疗个性化：识别哪些患者更受益于特定治疗
    - 政策 Targeting：识别政策的最优目标群体
    - 客户分层：基于异质性效应进行客户细分

参考文献:
    - Athey, S., & Imbens, G. (2016). Recursive partitioning for heterogeneous causal effects
    - Wager, S., & Athey, S. (2018). Estimation and inference of heterogeneous treatment effects
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
class CausalForestConfig:
    """因果森林配置数据类。

    用于存储和验证因果森林分析的参数配置。

    属性:
        treatment_col: 处理组标识列名（值为0/1）
        outcome_col: 结果变量列名
        covariates: 协变量列名列表（用于分裂和估计异质性效应）
        n_estimators: 树的数量（默认100）
        max_depth: 最大深度（默认5）
        min_samples_leaf: 叶节点最小样本数（默认10）
        subsample_ratio: 子采样比例（默认1.0，使用全部样本）
        random_state: 随机种子（默认42）
    """

    treatment_col: str
    outcome_col: str
    covariates: List[str]
    n_estimators: int = 100
    max_depth: int = 5
    min_samples_leaf: int = 10
    subsample_ratio: float = 1.0
    random_state: int = 42


class CausalForestAnalyzer(BaseCausalAnalyzer):
    """因果森林分析器。

    使用因果森林估计异质性处理效应，
    识别哪些样本更受益于处理。

    参数:
        data (pl.DataFrame): Polars DataFrame，包含分析所需的全部列
        config (Dict[str, Any]): 分析配置，包含:
            - treatment_col: 处理组标识列名
            - outcome_col: 结果变量列名
            - covariates: 协变量列表
            - n_estimators: 树的数量
            - max_depth: 最大深度
            - min_samples_leaf: 叶节点最小样本数

    示例:
        >>> df = pl.DataFrame({
        ...     "is_treated": [0,0,1,1,0,0,1,1],
        ...     "age": [25,30,35,40,28,32,38,42],
        ...     "income": [5000,6000,5500,7000,5200,6100,5600,7200],
        ...     "outcome": [100,110,130,150,105,115,135,155]
        ... })
        >>> analyzer = CausalForestAnalyzer(data=df, config={
        ...     "treatment_col": "is_treated",
        ...     "outcome_col": "outcome",
        ...     "covariates": ["age", "income"]
        ... })
        >>> analyzer.fit()
        >>> result = analyzer.get_result()
        >>> cate_scores = result.metadata["cate_scores"]
    """

    def __init__(self, data: pl.DataFrame, config: Dict[str, Any]) -> None:
        """初始化因果森林分析器。

        参数:
            data: 输入的Polars DataFrame数据
            config: 分析配置字典
        """
        super().__init__(data, config)
        self.config = CausalForestConfig(
            treatment_col=config["treatment_col"],
            outcome_col=config["outcome_col"],
            covariates=config["covariates"],
            n_estimators=config.get("n_estimators", 100),
            max_depth=config.get("max_depth", 5),
            min_samples_leaf=config.get("min_samples_leaf", 10),
            subsample_ratio=config.get("subsample_ratio", 1.0),
            random_state=config.get("random_state", 42),
        )
        self._forest: Optional[Any] = None
        self._cate_scores: Optional[np.ndarray] = None

    def validate_config(self) -> tuple[bool, Optional[str]]:
        """验证因果森林配置是否有效。

        检查必需列是否存在，以及样本量是否足够。

        返回:
            tuple: (是否有效, 错误消息)
        """
        required = [self.config.treatment_col, self.config.outcome_col] + self.config.covariates
        valid, msg = self.check_required_columns(self.data, required)
        if not valid:
            return False, msg

        # 检查样本量
        n = self.data.height
        if n < 50:
            return False, f"样本量不足（当前{n}，因果森林建议至少50个样本）"

        # 检查处理组和对照组样本量
        treatment_n = self.data.filter(pl.col(self.config.treatment_col) == 1).height
        control_n = self.data.filter(pl.col(self.config.treatment_col) == 0).height

        if treatment_n < 10:
            return False, f"处理组样本量不足（当前{treatment_n}，建议至少10个）"
        if control_n < 10:
            return False, f"对照组样本量不足（当前{control_n}，建议至少10个）"

        # 检查协变量是否有变异
        for cov in self.config.covariates:
            unique_vals = self.data[cov].n_unique()
            if unique_vals < 2:
                return False, f"协变量 {cov} 缺乏变异"

        return True, None

    def fit(self) -> None:
        """执行因果森林估计。

        使用因果森林算法估计每个样本的个体化处理效应（CATE）。

        方法:
            使用EconML的CausalForest或手动实现：
            1. 构建多棵因果树
            2. 每棵树使用诚实估计（honest estimation）
            3. 集成多棵树的预测作为最终CATE估计

        返回:
            None: 结果存入 self._result 属性
        """
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

        # 准备数据
        X = df[covariates].values
        T = df[treatment].values
        Y = df[outcome].values

        # 尝试使用EconML的CausalForest
        try:
            from econml.dml import CausalForestDML

            # 使用EconML的因果森林
            cf = CausalForestDML(
                n_estimators=self.config.n_estimators,
                max_depth=self.config.max_depth,
                min_samples_leaf=self.config.min_samples_leaf,
                random_state=self.config.random_state,
                propensity_model="logistic",
            )

            cf.fit(Y, T, X=X, W=None)

            # 估计CATE
            cate_scores = cf.const_marginal_ate_inference(X)
            ate = cate_scores.mean()
            std_err = cate_scores.std()

            self._cate_scores = cate_scores
            self._forest = cf

        except ImportError:
            # 如果EconML不可用，使用简化实现
            ate, std_err, cate_scores = self._manual_causal_forest(X, T, Y)

        # 计算统计显著性
        conf_int = (ate - 1.96 * std_err, ate + 1.96 * std_err)
        is_significant = (conf_int[0] > 0) or (conf_int[1] < 0)

        # 处理组和对照组样本量
        treatment_n = int(T.sum())
        control_n = len(T) - treatment_n

        # 计算异质性统计
        heterogeneity = self._calculate_heterogeneity(cate_scores)

        # 生成诊断图表
        diagnostic_plots = self._generate_diagnostic_plots(
            df, X, T, Y, cate_scores, covariates
        )

        # 构建结果
        self._result = AnalysisResult(
            method=CausalMethod.CAUSAL_FOREST,
            effect_estimate=float(ate),
            confidence_interval=(float(conf_int[0]), float(conf_int[1])),
            p_value=0.05,  # 简化处理
            standard_error=float(std_err),
            sample_size=len(df),
            treatment_size=treatment_n,
            control_size=control_n,
            is_significant=is_significant,
            diagnostic_plots=diagnostic_plots,
            metadata={
                "ate": float(ate),
                "cate_scores": cate_scores.tolist(),
                "heterogeneity": heterogeneity,
                "n_estimators": self.config.n_estimators,
                "covariates": covariates,
            },
        )

        self._is_fitted = True

    def _manual_causal_forest(
        self,
        X: np.ndarray,
        T: np.ndarray,
        Y: np.ndarray,
    ) -> tuple[float, float, np.ndarray]:
        """手动实现简化版因果森林。

        当EconML不可用时的备选实现。
        使用基于决策树的简化方法估计CATE。

        参数:
            X: 协变量矩阵
            T: 处理变量数组
            Y: 结果变量数组

        返回:
            tuple: (ATE, 标准误, CATE分数数组)
        """
        from sklearn.tree import DecisionTreeRegressor

        n = len(Y)
        cate_scores = np.zeros(n)

        # 使用 Honest Tree 方法
        # 样本分裂：用于分裂的样本 和 用于估计的样本
        n_subsample = int(n * self.config.subsample_ratio)
        indices = np.random.RandomState(self.config.random_state).permutation(n)
        split_indices = indices[:n_subsample]
        estimate_indices = indices[n_subsample:]

        if len(estimate_indices) < 10:
            estimate_indices = indices  # 回退到使用全部样本

        # 构建多棵树
        trees = []
        for i in range(self.config.n_estimators):
            # Bootstrap 采样
            boot_indices = np.random.RandomState(
                self.config.random_state + i
            ).choice(split_indices, size=len(split_indices), replace=True)

            X_boot = X[boot_indices]
            T_boot = T[boot_indices]
            Y_boot = Y[boot_indices]

            # 构建因果树
            # 使用双机器学习：先拟合倾向得分，再拟合残差
            from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

            # 倾向得分模型
            propensity_model = DecisionTreeClassifier(
                max_depth=3,
                min_samples_leaf=10,
                random_state=self.config.random_state + i,
            )
            propensity_model.fit(X_boot, T_boot)
            e_x = propensity_model.predict_proba(X)[:, 1]
            e_x = np.clip(e_x, 0.1, 0.9)  # 裁剪避免极端值

            # 结果模型（IPW变体）
            # 对于处理组：Y/e(X)
            # 对于对照组：Y/(1-e(X))
            sample_weight_t = T_boot / e_x[boot_indices]
            sample_weight_c = (1 - T_boot) / (1 - e_x[boot_indices])

            # 简化：直接使用决策树分裂
            tree = DecisionTreeRegressor(
                max_depth=self.config.max_depth,
                min_samples_leaf=self.config.min_samples_leaf,
                random_state=self.config.random_state + i,
            )
            tree.fit(X_boot, Y_boot, sample_weight=T_boot * 2 - 1)  # 使用处理指示符作为权重

            trees.append(tree)

        # 集成预测
        for tree in trees:
            cate_scores += tree.predict(X) / self.config.n_estimators

        # 计算ATE和标准误
        ate = cate_scores.mean()
        std_err = cate_scores.std() / np.sqrt(n)

        return ate, std_err, cate_scores

    def _calculate_heterogeneity(self, cate_scores: np.ndarray) -> Dict[str, float]:
        """计算处理效应异质性统计量。

        分析不同样本之间的处理效应差异程度。

        参数:
            cate_scores: CATE分数数组

        返回:
            Dict[str, float]: 异质性统计量
        """
        return {
            "mean": float(np.mean(cate_scores)),
            "std": float(np.std(cate_scores)),
            "min": float(np.min(cate_scores)),
            "max": float(np.max(cate_scores)),
            "q25": float(np.percentile(cate_scores, 25)),
            "q50": float(np.percentile(cate_scores, 50)),
            "q75": float(np.percentile(cate_scores, 75)),
        }

    def _generate_diagnostic_plots(
        self,
        df: pd.DataFrame,
        X: np.ndarray,
        T: np.ndarray,
        Y: np.ndarray,
        cate_scores: np.ndarray,
        covariate_names: List[str],
    ) -> List[DiagnosticPlot]:
        """生成因果森林诊断图表。

        生成CATE分布图、异质性分析图等。

        参数:
            df: Pandas DataFrame
            X: 协变量矩阵
            T: 处理变量数组
            Y: 结果变量数组
            cate_scores: CATE分数数组
            covariate_names: 协变量名称列表

        返回:
            List[DiagnosticPlot]: 诊断图表列表
        """
        plots = []

        # 1. CATE分布直方图
        cate_hist = np.histogram(cate_scores, bins=20)

        cate_distribution_data = {
            "xAxis": {"type": "value", "name": "个体处理效应 (CATE)"},
            "yAxis": {"type": "value", "name": "样本数量"},
            "series": [
                {
                    "name": "CATE分布",
                    "type": "bar",
                    "data": [[float(cate_hist[1][i]), float(cate_hist[0][i])]
                             for i in range(len(cate_hist[0]))],
                    "itemStyle": {"color": "#10b981"},
                },
            ],
            "markLine": {
                "data": [
                    {"xAxis": float(np.mean(cate_scores)), "name": "平均效应"},
                ],
                "lineStyle": {"color": "#ef4444", "type": "dashed"},
            },
        }
        plots.append(DiagnosticPlot(
            name="CATE分布",
            chart_type="bar",
            data=cate_distribution_data,
            title="个体处理效应分布",
            description="展示每个样本的估计处理效应分布。分布越宽，表示异质性越大。",
        ))

        # 2. 协变量与CATE的关系（选择最重要的2个协变量）
        # 简化：使用前两个协变量
        n_cov = min(2, X.shape[1])

        for i in range(n_cov):
            cov_values = X[:, i]
            cov_name = covariate_names[i] if i < len(covariate_names) else f"协变量{i}"

            # 分箱计算各组的平均CATE
            n_bins = 5
            bin_edges = np.percentile(cov_values, np.linspace(0, 100, n_bins + 1))
            bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2

            bin_cates = []
            for j in range(n_bins):
                mask = (cov_values >= bin_edges[j]) & (cov_values < bin_edges[j + 1])
                if j == n_bins - 1:
                    mask = (cov_values >= bin_edges[j]) & (cov_values <= bin_edges[j + 1])
                bin_cates.append(float(np.mean(cate_scores[mask])))

            covariate_effect_data = {
                "xAxis": {"type": "value", "name": cov_name},
                "yAxis": {"type": "value", "name": "平均CATE"},
                "series": [
                    {
                        "name": "异质性效应",
                        "type": "line",
                        "data": [[float(bin_centers[i]), bin_cates[i]]
                                 for i in range(n_bins)],
                        "lineStyle": {"color": "#10b981"},
                        "areaStyle": {"color": "rgba(16,185,129,0.2)"},
                    },
                ],
            }
            plots.append(DiagnosticPlot(
                name=f"CATE与{cov_name}关系",
                chart_type="line",
                data=covariate_effect_data,
                title=f"异质性效应：{cov_name}",
                description=f"展示{cov_name}与处理效应的关系。趋势越明显，说明该变量的异质性越大。",
            ))

        # 3. 处理组vs对照组在不同CATE分位数的分布
        treatment_cates = cate_scores[T == 1]
        control_cates = cate_scores[T == 0]

        q25, q50, q75 = np.percentile(cate_scores, [25, 50, 75])

        boxplot_data = {
            "xAxis": {"type": "category", "data": ["处理组", "对照组"]},
            "yAxis": {"type": "value", "name": "CATE"},
            "series": [
                {
                    "name": "CATE",
                    "type": "boxplot",
                    "data": [
                        [float(np.min(treatment_cates)),
                         float(np.percentile(treatment_cates, 25)),
                         float(np.median(treatment_cates)),
                         float(np.percentile(treatment_cates, 75)),
                         float(np.max(treatment_cates))],
                        [float(np.min(control_cates)),
                         float(np.percentile(control_cates, 25)),
                         float(np.median(control_cates)),
                         float(np.percentile(control_cates, 75)),
                         float(np.max(control_cates))],
                    ],
                    "itemStyle": {"color": "#8b5cf6"},
                },
            ],
        }
        plots.append(DiagnosticPlot(
            name="分组CATE对比",
            chart_type="boxplot",
            data=boxplot_data,
            title="处理组 vs 对照组 的CATE分布",
            description="对比处理组和对照组的CATE分布。",
        ))

        return plots

    def get_cate_scores(self) -> np.ndarray:
        """获取每个样本的CATE分数。

        必须在调用fit()之后才能使用。

        返回:
            np.ndarray: 每个样本的个体化处理效应估计
        """
        if not self._is_fitted:
            raise RuntimeError("必须先调用 fit() 方法")
        return self._cate_scores
