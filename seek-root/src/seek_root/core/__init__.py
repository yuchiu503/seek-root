"""因果推断核心引擎模块。

本模块实现了各类因果推断方法的统一接口，所有分析器继承自
BaseCausalAnalyzer 基类，确保了对外API的一致性和可扩展性。

支持的因果推断方法:
- DID: 双差分法 (Difference-in-Differences)
- PSM: 倾向得分匹配 (Propensity Score Matching)
- RD: 断点回归 (Regression Discontinuity)
- IV: 工具变量法 (Instrumental Variables)
- CausalForest: 因果森林 (Causal Forest)
"""

from seek_root.core.base import (
    BaseCausalAnalyzer,
    CausalMethod,
    AnalysisResult,
    DiagnosticPlot,
)

__all__ = [
    "BaseCausalAnalyzer",
    "CausalMethod",
    "AnalysisResult",
    "DiagnosticPlot",
]
