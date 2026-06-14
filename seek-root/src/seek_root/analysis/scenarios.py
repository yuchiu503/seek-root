"""预定义分析场景模块。

本模块包含各种常见的因果分析场景模板。

类:
    PromotionEffectScenario: 促销活动效果评估场景
    ChannelAttributionScenario: 渠道效果归因场景
    ABTestScenario: A/B测试验证场景
    PricingImpactScenario: 价格策略影响场景
"""

from typing import Any, Dict, List, Optional

from seek_root.analysis.base import BaseScenario, ScenarioConfig
from seek_root.core.base import CausalMethod


class PromotionEffectScenario(BaseScenario):
    """促销活动效果评估场景。

    用于评估满减、优惠券、折扣等促销活动对销售额、转化率等指标的影响。

    典型数据格式:
    - 处理标识: 是否参与活动 (is_promotion)
    - 时间标识: 活动前/后 (is_post)
    - 结果变量: 销售额、订单数、转化率等 (revenue, orders, conversion)
    - 协变量: 用户特征、商品类别等 (可选)
    """

    def __init__(self) -> None:
        """初始化促销活动效果评估场景。"""
        config = ScenarioConfig(
            name="促销活动效果评估",
            description="评估满减、优惠券等促销活动对销售额/转化率的影响",
            recommended_methods=[CausalMethod.DID, CausalMethod.PSM],
            required_columns=["处理标识", "时间标识", "结果变量"],
            optional_columns=["协变量", "用户ID", "商品ID"],
        )
        super().__init__(config)

    def get_column_requirements(self) -> Dict[str, Any]:
        """获取列配置要求。

        返回:
            dict: 列配置字典
        """
        return {
            "required": [
                {
                    "name": "is_treated",
                    "label": "处理标识",
                    "type": "boolean",
                    "description": "是否属于处理组（参与了促销活动）",
                    "keywords": ["is_treated", "is_promotion", "treated", "promotion"],
                },
                {
                    "name": "is_post",
                    "label": "时间标识",
                    "type": "boolean",
                    "description": "是否在活动之后",
                    "keywords": ["is_post", "post", "after", "period"],
                },
                {
                    "name": "outcome",
                    "label": "结果变量",
                    "type": "numeric",
                    "description": "要评估的指标，如销售额、订单数等",
                    "keywords": ["revenue", "sales", "orders", "conversion", "outcome"],
                },
            ],
            "optional": [
                {
                    "name": "covariates",
                    "label": "协变量",
                    "type": "numeric",
                    "description": "用于控制的其他变量",
                    "keywords": ["age", "gender", "city", "category"],
                    "multi": True,
                },
                {
                    "name": "user_id",
                    "label": "用户ID",
                    "type": "string",
                    "description": "用户唯一标识（用于匹配）",
                    "keywords": ["user_id", "userid", "customer_id"],
                },
            ],
            "auto_detect": True,
        }

    def get_method_recommendations(
        self,
        data_shape: tuple,
        column_types: Dict[str, str],
    ) -> List[CausalMethod]:
        """根据数据特征推荐方法。

        参数:
            data_shape: 数据形状
            column_types: 列类型

        返回:
            list: 推荐的方法列表
        """
        rows, cols = data_shape

        # 数据量大且有面板结构
        if rows > 1000 and "boolean" in column_types.values():
            return [CausalMethod.DID, CausalMethod.PSM]

        # 小数据集
        return [CausalMethod.PSM, CausalMethod.DID]

    def interpret_results(
        self,
        method: CausalMethod,
        results: Dict[str, Any],
    ) -> Dict[str, str]:
        """解读分析结果。

        参数:
            method: 使用的方法
            results: 分析结果

        返回:
            dict: 解读结果
        """
        effect = results.get("effect_estimate", 0)
        p_value = results.get("p_value", 1)

        if method == CausalMethod.DID:
            summary = f"促销活动带来了{'显著' if p_value < 0.05 else '不显著'}的效果"
            details = (
                f"通过双差分法分析，促销活动对目标指标的净效应为 {effect:.2f}。"
                f"{'该效应在统计上显著（p < 0.05），可以排除随机因素的影响。' if p_value < 0.05 else '该效应在统计上不显著，可能需要更多数据或重新评估活动设计。'}"
            )
        else:
            summary = f"倾向得分匹配分析显示处理效应为 {effect:.2f}"
            details = f"通过为处理组匹配特征相似的对照组，估计出促销活动的净效应为 {effect:.2f}。"

        recommendation = (
            f"建议{'继续' if p_value < 0.05 and effect > 0 else '重新评估'}促销活动策略。"
            f"{'活动效果显著，可以考虑扩大规模。' if effect > 0 else '活动效果不明显或为负，建议优化活动设计。'}"
        )

        return {
            "summary": summary,
            "details": details,
            "recommendation": recommendation,
        }


class ChannelAttributionScenario(BaseScenario):
    """渠道效果归因场景。

    用于分析不同营销渠道（广告投放、SEO、社交媒体等）对最终转化的贡献度。

    典型数据格式:
    - 渠道标识: 渠道名称 (channel)
    - 处理标识: 是否触达 (exposed)
    - 结果变量: 转化、购买等 (conversion, revenue)
    - 协变量: 用户特征、渠道投入等 (可选)
    """

    def __init__(self) -> None:
        """初始化渠道效果归因场景。"""
        config = ScenarioConfig(
            name="渠道效果归因",
            description="分析不同营销渠道对最终转化的贡献度",
            recommended_methods=[CausalMethod.IV, CausalMethod.CAUSAL_FOREST],
            required_columns=["渠道标识", "处理标识", "结果变量"],
            optional_columns=["渠道投入", "用户特征"],
        )
        super().__init__(config)

    def get_column_requirements(self) -> Dict[str, Any]:
        """获取列配置要求。"""
        return {
            "required": [
                {
                    "name": "channel",
                    "label": "渠道标识",
                    "type": "string",
                    "description": "营销渠道名称",
                    "keywords": ["channel", "source", "medium"],
                },
                {
                    "name": "is_exposed",
                    "label": "处理标识",
                    "type": "boolean",
                    "description": "是否触达该渠道",
                    "keywords": ["exposed", "treated", "is_touched"],
                },
                {
                    "name": "outcome",
                    "label": "结果变量",
                    "type": "numeric",
                    "description": "转化指标，如购买、注册等",
                    "keywords": ["conversion", "purchase", "signup", "outcome"],
                },
            ],
            "optional": [
                {
                    "name": "cost",
                    "label": "渠道投入",
                    "type": "numeric",
                    "description": "渠道花费",
                    "keywords": ["cost", "spend", "budget"],
                },
                {
                    "name": "covariates",
                    "label": "用户特征",
                    "type": "mixed",
                    "description": "用户或渠道特征",
                    "multi": True,
                },
            ],
            "auto_detect": True,
        }

    def get_method_recommendations(
        self,
        data_shape: tuple,
        column_types: Dict[str, str],
    ) -> List[CausalMethod]:
        """推荐方法。"""
        return [CausalMethod.IV, CausalMethod.CAUSAL_FOREST]

    def interpret_results(
        self,
        method: CausalMethod,
        results: Dict[str, Any],
    ) -> Dict[str, str]:
        """解读结果。"""
        effect = results.get("effect_estimate", 0)
        return {
            "summary": f"渠道分析完成，效应值为 {effect:.2f}",
            "details": "通过工具变量法或因果森林分析了渠道对转化的贡献。",
            "recommendation": "建议根据效应大小调整渠道投入分配。",
        }


class ABTestScenario(BaseScenario):
    """A/B测试验证场景。

    用于验证A/B测试结果的因果效应，确认实验组和对照组的差异是否具有因果意义。

    典型数据格式:
    - 组别标识: 实验组/对照组 (group)
    - 结果变量: 目标指标 (metric)
    - 协变量: 用户特征 (可选)
    """

    def __init__(self) -> None:
        """初始化A/B测试场景。"""
        config = ScenarioConfig(
            name="A/B测试因果验证",
            description="验证A/B测试结果的因果效应",
            recommended_methods=[CausalMethod.DID, CausalMethod.PSM],
            required_columns=["组别标识", "结果变量"],
            optional_columns=["协变量", "时间标识"],
        )
        super().__init__(config)

    def get_column_requirements(self) -> Dict[str, Any]:
        """获取列配置要求。"""
        return {
            "required": [
                {
                    "name": "group",
                    "label": "组别标识",
                    "type": "string",
                    "description": "实验组或对照组",
                    "keywords": ["group", "variant", "ab_group"],
                },
                {
                    "name": "outcome",
                    "label": "结果变量",
                    "type": "numeric",
                    "description": "测试指标",
                    "keywords": ["metric", "outcome", "conversion", "revenue"],
                },
            ],
            "optional": [
                {
                    "name": "time",
                    "label": "时间标识",
                    "type": "datetime",
                    "description": "记录时间",
                    "keywords": ["time", "date", "created_at"],
                },
                {
                    "name": "covariates",
                    "label": "协变量",
                    "type": "mixed",
                    "description": "用户特征",
                    "multi": True,
                },
            ],
            "auto_detect": True,
        }

    def get_method_recommendations(
        self,
        data_shape: tuple,
        column_types: Dict[str, str],
    ) -> List[CausalMethod]:
        """推荐方法。"""
        return [CausalMethod.DID, CausalMethod.PSM]

    def interpret_results(
        self,
        method: CausalMethod,
        results: Dict[str, Any],
    ) -> Dict[str, str]:
        """解读结果。"""
        effect = results.get("effect_estimate", 0)
        p_value = results.get("p_value", 1)
        significant = p_value < 0.05

        summary = f"A/B测试验证{'显著' if significant else '不显著'}"
        details = (
            f"实验组相对于对照组的变化为 {effect:.2f}，"
            f"{'具有统计显著性' if significant else '不具有统计显著性'}。"
        )
        recommendation = (
            "可以{'发布新方案' if significant and effect > 0 else '保持原方案' if significant else '增加样本量或调整方案'}。"
        )

        return {
            "summary": summary,
            "details": details,
            "recommendation": recommendation,
        }


class PricingImpactScenario(BaseScenario):
    """价格策略影响场景。

    用于分析价格变动对销量和收入的影响，特别适用于存在价格阈值或促销的场景。

    典型数据格式:
    - 运行变量: 价格或价格区间 (price)
    - 断点: 价格阈值 (threshold)
    - 结果变量: 销量、收入 (sales, revenue)
    """

    def __init__(self) -> None:
        """初始化价格策略影响场景。"""
        config = ScenarioConfig(
            name="价格策略影响",
            description="分析价格变动对销量和收入的影响",
            recommended_methods=[CausalMethod.RD, CausalMethod.CAUSAL_FOREST],
            required_columns=["价格/运行变量", "结果变量"],
            optional_columns=["断点阈值", "商品特征"],
        )
        super().__init__(config)

    def get_column_requirements(self) -> Dict[str, Any]:
        """获取列配置要求。"""
        return {
            "required": [
                {
                    "name": "price",
                    "label": "价格/运行变量",
                    "type": "numeric",
                    "description": "商品价格或价格区间",
                    "keywords": ["price", "cost", "amount"],
                },
                {
                    "name": "outcome",
                    "label": "结果变量",
                    "type": "numeric",
                    "description": "销量或收入",
                    "keywords": ["sales", "revenue", "quantity", "orders"],
                },
            ],
            "optional": [
                {
                    "name": "threshold",
                    "label": "断点阈值",
                    "type": "numeric",
                    "description": "价格阈值（如最低价格）",
                    "keywords": ["threshold", "cutoff", "boundary"],
                },
                {
                    "name": "category",
                    "label": "商品特征",
                    "type": "string",
                    "description": "商品类别或特征",
                    "keywords": ["category", "type", "segment"],
                },
            ],
            "auto_detect": True,
        }

    def get_method_recommendations(
        self,
        data_shape: tuple,
        column_types: Dict[str, str],
    ) -> List[CausalMethod]:
        """推荐方法。"""
        return [CausalMethod.RD, CausalMethod.CAUSAL_FOREST]

    def interpret_results(
        self,
        method: CausalMethod,
        results: Dict[str, Any],
    ) -> Dict[str, str]:
        """解读结果。"""
        effect = results.get("effect_estimate", 0)
        return {
            "summary": f"价格效应分析完成，效应值为 {effect:.2f}",
            "details": "分析了价格变动对销量的影响。",
            "recommendation": "建议根据价格弹性调整定价策略。",
        }
