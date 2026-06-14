"""分析场景基类模块。

定义所有分析场景的抽象基类，
确保各场景对外API的一致性。

类:
    BaseScenario: 分析场景抽象基类
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from seek_root.core.base import CausalMethod


@dataclass
class ScenarioConfig:
    """场景配置数据类。

    存储分析场景的配置参数。

    属性:
        name: 场景名称
        description: 场景描述
        recommended_methods: 推荐的分析方法列表
        required_columns: 必需的列名描述
        optional_columns: 可选的列名描述
    """

    name: str
    description: str
    recommended_methods: List[CausalMethod]
    required_columns: List[str]
    optional_columns: List[str]


class BaseScenario(ABC):
    """分析场景抽象基类。

    所有具体的分析场景都应继承此类，
    并实现相应的配置获取和结果解读方法。

    参数:
        config (ScenarioConfig): 场景配置对象
    """

    def __init__(self, config: ScenarioConfig) -> None:
        """初始化分析场景。

        参数:
            config: 场景配置对象
        """
        self.config = config

    @abstractmethod
    def get_column_requirements(self) -> Dict[str, Any]:
        """获取场景所需的列配置。

        返回一个描述各列用途和类型的字典。

        返回:
            dict: 列配置字典，包含:
                - required: 必需列的配置
                - optional: 可选列的配置
                - auto_detect: 是否自动检测这些列
        """
        pass

    @abstractmethod
    def get_method_recommendations(
        self,
        data_shape: tuple,
        column_types: Dict[str, str],
    ) -> List[CausalMethod]:
        """根据数据特征推荐分析方法。

        参数:
            data_shape: 数据形状 (行数, 列数)
            column_types: 各列的数据类型

        返回:
            list: 推荐的分析方法列表，按推荐程度排序
        """
        pass

    @abstractmethod
    def interpret_results(
        self,
        method: CausalMethod,
        results: Dict[str, Any],
    ) -> Dict[str, str]:
        """解读分析结果。

        根据具体场景和方法，生成业务友好的解读。

        参数:
            method: 使用的分析方法
            results: 分析结果字典

        返回:
            dict: 解读结果，包含:
                - summary: 一句话总结
                - details: 详细解读
                - recommendation: 业务建议
        """
        pass

    @classmethod
    def get_scenario_by_id(cls, scenario_id: str) -> Optional["BaseScenario"]:
        """根据ID获取场景实例。

        参数:
            scenario_id: 场景标识符

        返回:
            BaseScenario: 场景实例，不存在返回None
        """
        scenarios = {
            "promotion": "PromotionEffectScenario",
            "channel": "ChannelAttributionScenario",
            "ab_test": "ABTestScenario",
            "pricing": "PricingImpactScenario",
            "custom": None,  # 自定义场景不需要预定义
        }

        scenario_name = scenarios.get(scenario_id)
        if not scenario_name:
            return None

        # 动态导入并返回实例
        from seek_root.analysis import scenarios

        scenario_class = getattr(scenarios, scenario_name, None)
        if not scenario_class:
            return None

        return scenario_class()

    def validate_data_columns(
        self,
        available_columns: List[str],
    ) -> tuple[bool, List[str]]:
        """验证数据是否包含场景所需的列。

        参数:
            available_columns: 可用的列名列表

        返回:
            tuple: (是否通过验证, 缺失列列表)
        """
        missing = []
        for req_col in self.config.required_columns:
            # 简单匹配：检查列名是否包含关键词
            found = any(
                keyword.lower() in col.lower()
                for col in available_columns
                for keyword in req_col.split()
            )
            if not found:
                missing.append(req_col)

        return len(missing) == 0, missing
