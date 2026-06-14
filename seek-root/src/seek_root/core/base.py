"""因果推断分析器基类模块。

定义所有因果推断分析器的抽象基类和通用数据结构，
确保各方法对外API的一致性。

类:
    BaseCausalAnalyzer: 所有分析器的基类
    CausalMethod: 因果方法枚举
    AnalysisResult: 分析结果数据类
    DiagnosticPlot: 诊断图表数据类
"""

from abc import ABC, abstractmethod
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Optional, Dict, List
import polars as pl


class CausalMethod(Enum):
    """支持的因果推断方法枚举。

    每个枚举值对应一种具体的因果推断方法，
    包含方法的中英文名称和适用场景描述。
    """

    DID = "did"
    PSM = "psm"
    RD = "rd"
    IV = "iv"
    CAUSAL_FOREST = "causal_forest"

    @property
    def name_cn(self) -> str:
        """获取方法的中文名称。

        返回:
            str: 方法的中文名称
        """
        names = {
            CausalMethod.DID: "双差分法",
            CausalMethod.PSM: "倾向得分匹配",
            CausalMethod.RD: "断点回归",
            CausalMethod.IV: "工具变量法",
            CausalMethod.CAUSAL_FOREST: "因果森林",
        }
        return names[self]

    @property
    def description(self) -> str:
        """获取方法的适用场景描述。

        返回:
            str: 方法的适用场景描述
        """
        descs = {
            CausalMethod.DID: "评估政策/活动效果，需要处理组和控制组，以及前后时间点的观测数据",
            CausalMethod.PSM: "在存在选择偏差时，通过倾向得分匹配构造对照组，估计因果效应",
            CausalMethod.RD: "分析在某个断点/阈值附近的局部处理效应",
            CausalMethod.IV: "处理内生性问题，使用工具变量分离外生变异",
            CausalMethod.CAUSAL_FOREST: "估计异质性处理效应，识别哪些样本更受益于处理",
        }
        return descs[self]

    @property
    def required_columns(self) -> List[str]:
        """获取方法的必需列名提示。

        返回:
            List[str]: 必需列名的中文描述列表
        """
        cols = {
            CausalMethod.DID: ["处理组标识", "时间/时期标识", "结果变量", "协变量(可选)"],
            CausalMethod.PSM: ["处理组标识", "协变量", "结果变量"],
            CausalMethod.RD: ["运行变量(连续)", "处理标识", "结果变量"],
            CausalMethod.IV: ["工具变量", "处理变量", "结果变量", "协变量(可选)"],
            CausalMethod.CAUSAL_FOREST: ["处理标识", "协变量", "结果变量"],
        }
        return cols[self]


@dataclass
class DiagnosticPlot:
    """诊断图表数据类。

    用于存储因果推断过程中的诊断图表数据，
    可被序列化为JSON或传递给前端ECharts进行渲染。

    属性:
        name: 图表名称（如 '平行趋势图'、'平衡性检验图'）
        chart_type: 图表类型（如 'line', 'bar', 'scatter'）
        data: 图表数据，结构化字典
        title: 图表标题
        description: 图表的业务解读说明
    """

    name: str
    chart_type: str
    data: Dict[str, Any]
    title: str = ""
    description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。

        返回:
            Dict[str, Any]: 包含图表所有信息的字典
        """
        return {
            "name": self.name,
            "chart_type": self.chart_type,
            "data": self.data,
            "title": self.title,
            "description": self.description,
        }


@dataclass
class AnalysisResult:
    """因果推断分析结果数据类。

    存储分析完成后返回的所有结果信息，
    包括统计指标、诊断图表、业务解读等。

    属性:
        method: 所使用的因果推断方法
        effect_estimate: 处理效应点估计值
        confidence_interval: 置信区间 (下限, 上限)
        p_value: p值
        standard_error: 标准误
        sample_size: 样本量
        treatment_size: 处理组样本量
        control_size: 对照组样本量
        is_significant: 效应是否统计显著（通常 p < 0.05）
        conclusion: LLM生成的业务结论
        interpretation: LLM生成的详细业务解读
        diagnostic_plots: 诊断图表列表
        metadata: 其他元数据（如R方、ATT等）
    """

    method: CausalMethod
    effect_estimate: float
    confidence_interval: tuple[float, float]
    p_value: float
    standard_error: float
    sample_size: int
    treatment_size: int
    control_size: int
    is_significant: bool
    conclusion: str = ""
    interpretation: str = ""
    diagnostic_plots: List[DiagnosticPlot] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式，便于序列化和传递给前端。

        返回:
            Dict[str, Any]: 包含所有结果信息的字典
        """
        return {
            "method": self.method.value,
            "method_name_cn": self.method.name_cn,
            "effect_estimate": self.effect_estimate,
            "confidence_interval": {
                "lower": self.confidence_interval[0],
                "upper": self.confidence_interval[1],
            },
            "p_value": self.p_value,
            "standard_error": self.standard_error,
            "sample_size": self.sample_size,
            "treatment_size": self.treatment_size,
            "control_size": self.control_size,
            "is_significant": self.is_significant,
            "conclusion": self.conclusion,
            "interpretation": self.interpretation,
            "diagnostic_plots": [p.to_dict() for p in self.diagnostic_plots],
            "metadata": self.metadata,
        }


class BaseCausalAnalyzer(ABC):
    """因果推断分析器抽象基类。

    所有具体的因果推断方法分析器都应继承此类，
    并实现 fit() 和 get_result() 方法。

    参数:
        data (pl.DataFrame): Polars DataFrame，包含分析所需的全部列
        config (Dict[str, Any]): 分析配置字典，包含列名等参数

    示例:
        >>> analyzer = DIDAnalyzer(data=df, config={
        ...     "treatment_col": "is_treated",
        ...     "time_col": "is_post",
        ...     "outcome_col": "revenue"
        ... })
        >>> analyzer.fit()
        >>> result = analyzer.get_result()
    """

    def __init__(self, data: pl.DataFrame, config: Dict[str, Any]) -> None:
        """初始化分析器。

        参数:
            data: 输入的Polars DataFrame数据
            config: 分析配置，包含列名等参数
        """
        self.data = data
        self.config = config
        self._result: Optional[AnalysisResult] = None
        self._is_fitted: bool = False

    @abstractmethod
    def fit(self) -> None:
        """执行因果推断估计。

        子类必须实现此方法，执行具体的因果效应估计。
        估计完成后，结果应存储在 self._result 中。

        返回:
            None: 结果存入 self._result 属性

        异常:
            ValueError: 缺少必需列或参数无效时抛出
            RuntimeError: 估计过程发生错误时抛出
        """
        pass

    @abstractmethod
    def validate_config(self) -> tuple[bool, Optional[str]]:
        """验证配置是否有效。

        子类应实现配置验证逻辑，检查必需的配置项是否存在。

        返回:
            tuple: (是否有效, 错误消息)
        """
        pass

    def get_result(self) -> AnalysisResult:
        """获取分析结果。

        在调用此方法之前，必须先调用 fit() 方法。

        返回:
            AnalysisResult: 分析结果对象

        异常:
            RuntimeError: 未调用 fit() 时抛出
        """
        if not self._is_fitted:
            raise RuntimeError("必须先调用 fit() 方法才能获取结果")
        return self._result

    def is_fitted(self) -> bool:
        """检查分析器是否已完成拟合。

        返回:
            bool: 是否已完成拟合
        """
        return self._is_fitted

    @staticmethod
    def check_required_columns(
        df: pl.DataFrame,
        required_cols: List[str],
    ) -> tuple[bool, Optional[str]]:
        """检查DataFrame是否包含必需的列。

        参数:
            df: 要检查的Polars DataFrame
            required_cols: 必需的列名列表

        返回:
            tuple: (是否包含所有必需列, 缺失列的错误消息)
        """
        df_columns = set(df.columns)
        missing = [col for col in required_cols if col not in df_columns]
        if missing:
            return False, f"数据中缺少必需的列: {', '.join(missing)}"
        return True, None

    def _convert_to_pandas(self) -> Any:
        """将Polars DataFrame转换为Pandas DataFrame。

        DoWhy/EconML等库主要使用pandas，此方法用于兼容。

        返回:
            pd.DataFrame: 转换后的Pandas DataFrame
        """
        return self.data.to_pandas()
