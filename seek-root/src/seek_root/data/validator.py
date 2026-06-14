"""数据验证器模块。

本模块负责验证加载的数据是否满足各种因果推断方法的要求，
在分析前进行完整性检查，提前发现潜在问题。

类:
    DataValidator: 数据验证器
"""

from typing import Any, Dict, List, Optional, Tuple
import polars as pl

from seek_root.core.base import CausalMethod
from seek_root.utils.errors import ValidationError


class DataValidator:
    """数据验证器类。

    在执行因果推断分析前，验证数据是否满足方法要求。
    支持验证多种因果推断方法的数据要求。

    参数:
        data (pl.DataFrame): 要验证的数据

    示例:
        >>> validator = DataValidator(df)
        >>> valid, errors = validator.validate_for_did(
        ...     treatment_col="is_treated",
        ...     time_col="is_post",
        ...     outcome_col="revenue"
        ... )
        >>> if not valid:
        ...     print(f"数据不满足要求: {errors}")
    """

    def __init__(self, data: pl.DataFrame) -> None:
        """初始化数据验证器。

        参数:
            data: 要验证的Polars DataFrame
        """
        self.data = data

    def validate_for_did(
        self,
        treatment_col: str,
        time_col: str,
        outcome_col: str,
        covariates: Optional[List[str]] = None,
    ) -> Tuple[bool, List[str]]:
        """验证数据是否满足DID方法要求。

        DID方法要求：
        1. 必须有处理组标识列（二元变量）
        2. 必须有时间标识列（二元变量）
        3. 必须有结果变量列（数值型）
        4. 处理组和对照组在处理前必须有相似的趋势（平行趋势假设）

        参数:
            treatment_col: 处理组标识列名
            time_col: 时间标识列名
            outcome_col: 结果变量列名
            covariates: 协变量列名列表（可选）

        返回:
            tuple: (是否通过验证, 错误消息列表)
        """
        errors = []

        # 检查必需列是否存在
        required_cols = [treatment_col, time_col, outcome_col]
        if covariates:
            required_cols.extend(covariates)

        for col in required_cols:
            if col not in self.data.columns:
                errors.append(f"缺少必需的列: {col}")

        if errors:
            return False, errors

        # 检查treatment_col是否为二元变量
        unique_treatment = self.data[treatment_col].unique().to_list()
        if len(unique_treatment) != 2:
            errors.append(
                f"处理组标识列 '{treatment_col}' 必须是二元变量，"
                f"当前有 {len(unique_treatment)} 个唯一值"
            )

        # 检查time_col是否为二元变量
        unique_time = self.data[time_col].unique().to_list()
        if len(unique_time) != 2:
            errors.append(
                f"时间标识列 '{time_col}' 必须是二元变量，"
                f"当前有 {len(unique_time)} 个唯一值"
            )

        # 检查outcome_col是否为数值型
        outcome_dtype = self.data[outcome_col].dtype
        if not self._is_numeric_dtype(outcome_dtype):
            errors.append(f"结果变量列 '{outcome_col}' 必须是数值类型，当前为 {outcome_dtype}")

        # 检查各组样本量
        treatment_n = self.data.filter(pl.col(treatment_col) == 1).height
        control_n = self.data.filter(pl.col(treatment_col) == 0).height

        if treatment_n < 10:
            errors.append(f"处理组样本量不足（当前{treatment_n}，建议至少10个）")
        if control_n < 10:
            errors.append(f"对照组样本量不足（当前{control_n}，建议至少10个）")

        # 检查时间点样本量
        pre_n = self.data.filter(pl.col(time_col) == 0).height
        post_n = self.data.filter(pl.col(time_col) == 1).height

        if pre_n < 10:
            errors.append(f"处理前样本量不足（当前{pre_n}，建议至少10个）")
        if post_n < 10:
            errors.append(f"处理后样本量不足（当前{post_n}，建议至少10个）")

        return len(errors) == 0, errors

    def validate_for_psm(
        self,
        treatment_col: str,
        outcome_col: str,
        covariates: List[str],
    ) -> Tuple[bool, List[str]]:
        """验证数据是否满足PSM方法要求。

        PSM方法要求：
        1. 必须有处理组标识列（二元变量）
        2. 必须有结果变量列（数值型）
        3. 必须有协变量列（用于估计倾向得分）
        4. 协变量在处理组和对照组之间应有足够的重叠

        参数:
            treatment_col: 处理组标识列名
            outcome_col: 结果变量列名
            covariates: 协变量列名列表

        返回:
            tuple: (是否通过验证, 错误消息列表)
        """
        errors = []

        # 检查必需列
        required_cols = [treatment_col, outcome_col] + covariates
        for col in required_cols:
            if col not in self.data.columns:
                errors.append(f"缺少必需的列: {col}")

        if errors:
            return False, errors

        # 检查treatment_col是否为二元变量
        unique_treatment = self.data[treatment_col].unique().to_list()
        if len(unique_treatment) != 2:
            errors.append(
                f"处理组标识列 '{treatment_col}' 必须是二元变量"
            )

        # 检查outcome_col是否为数值型
        outcome_dtype = self.data[outcome_col].dtype
        if not self._is_numeric_dtype(outcome_dtype):
            errors.append(f"结果变量列 '{outcome_col}' 必须是数值类型")

        # 检查各组样本量
        treatment_n = self.data.filter(pl.col(treatment_col) == 1).height
        control_n = self.data.filter(pl.col(treatment_col) == 0).height

        if treatment_n < 10:
            errors.append(f"处理组样本量不足（当前{treatment_n}）")
        if control_n < 10:
            errors.append(f"对照组样本量不足（当前{control_n}）")

        # 检查协变量变异
        for cov in covariates:
            cov_dtype = self.data[cov].dtype
            if not self._is_numeric_dtype(cov_dtype) and cov_dtype != pl.Categorical:
                # 尝试转换为数值
                try:
                    temp = self.data[cov].cast(pl.Float64)
                except Exception:
                    errors.append(f"协变量 '{cov}' 必须是数值类型或类别类型")

        return len(errors) == 0, errors

    def validate_for_rd(
        self,
        running_col: str,
        treatment_col: str,
        outcome_col: str,
        cutoff: float,
    ) -> Tuple[bool, List[str]]:
        """验证数据是否满足RD方法要求。

        RD方法要求：
        1. 必须有运行变量列（连续变量）
        2. 必须有处理组标识列（二元变量）
        3. 必须有结果变量列（数值型）
        4. 断点应在运行变量的范围内

        参数:
            running_col: 运行变量列名
            treatment_col: 处理组标识列名
            outcome_col: 结果变量列名
            cutoff: 断点位置

        返回:
            tuple: (是否通过验证, 错误消息列表)
        """
        errors = []

        # 检查必需列
        required_cols = [running_col, treatment_col, outcome_col]
        for col in required_cols:
            if col not in self.data.columns:
                errors.append(f"缺少必需的列: {col}")

        if errors:
            return False, errors

        # 检查running_col是否为连续变量
        running_n_unique = self.data[running_col].n_unique()
        if running_n_unique < 10:
            errors.append(
                f"运行变量 '{running_col}' 应为连续变量，"
                f"当前只有 {running_n_unique} 个唯一值"
            )

        # 检查断点是否在运行变量范围内
        running_min = self.data[running_col].min()
        running_max = self.data[running_col].max()

        if cutoff < running_min or cutoff > running_max:
            errors.append(
                f"断点 {cutoff} 不在运行变量范围内 [{running_min}, {running_max}]"
            )

        # 检查两侧样本量
        below_n = self.data.filter(pl.col(running_col) < cutoff).height
        above_n = self.data.filter(pl.col(running_col) >= cutoff).height

        if below_n < 10:
            errors.append(f"断点以下样本量不足（当前{below_n}）")
        if above_n < 10:
            errors.append(f"断点以上样本量不足（当前{above_n}）")

        return len(errors) == 0, errors

    def validate_for_iv(
        self,
        instrument_col: str,
        treatment_col: str,
        outcome_col: str,
    ) -> Tuple[bool, List[str]]:
        """验证数据是否满足IV方法要求。

        IV方法要求：
        1. 必须有工具变量列
        2. 必须有内生处理变量列
        3. 必须有结果变量列
        4. 工具变量与处理变量应有一定相关性

        参数:
            instrument_col: 工具变量列名
            treatment_col: 处理变量列名
            outcome_col: 结果变量列名

        返回:
            tuple: (是否通过验证, 错误消息列表)
        """
        errors = []

        required_cols = [instrument_col, treatment_col, outcome_col]
        for col in required_cols:
            if col not in self.data.columns:
                errors.append(f"缺少必需的列: {col}")

        if errors:
            return False, errors

        # 检查各变量的变异
        for col, name in [(instrument_col, "工具变量"), (treatment_col, "处理变量")]:
            n_unique = self.data[col].n_unique()
            if n_unique < 2:
                errors.append(f"{name} '{col}' 缺乏变异")

        # 检查outcome是否为数值型
        outcome_dtype = self.data[outcome_col].dtype
        if not self._is_numeric_dtype(outcome_dtype):
            errors.append(f"结果变量 '{outcome_col}' 必须是数值类型")

        return len(errors) == 0, errors

    def validate_for_causal_forest(
        self,
        treatment_col: str,
        outcome_col: str,
        covariates: List[str],
    ) -> Tuple[bool, List[str]]:
        """验证数据是否满足因果森林方法要求。

        因果森林要求：
        1. 必须有处理组标识列（二元变量）
        2. 必须有结果变量列（数值型）
        3. 必须有协变量列
        4. 总样本量应足够（建议>=100）

        参数:
            treatment_col: 处理组标识列名
            outcome_col: 结果变量列名
            covariates: 协变量列名列表

        返回:
            tuple: (是否通过验证, 错误消息列表)
        """
        errors = []

        required_cols = [treatment_col, outcome_col] + covariates
        for col in required_cols:
            if col not in self.data.columns:
                errors.append(f"缺少必需的列: {col}")

        if errors:
            return False, errors

        # 检查样本量
        n = self.data.height
        if n < 50:
            errors.append(f"样本量不足（当前{n}，建议至少50个）")

        # 检查处理组和对照组样本量
        treatment_n = self.data.filter(pl.col(treatment_col) == 1).height
        control_n = self.data.filter(pl.col(treatment_col) == 0).height

        if treatment_n < 10:
            errors.append(f"处理组样本量不足（当前{treatment_n}）")
        if control_n < 10:
            errors.append(f"对照组样本量不足（当前{control_n}）")

        return len(errors) == 0, errors

    @staticmethod
    def _is_numeric_dtype(dtype: pl.DataType) -> bool:
        """检查Polars数据类型是否为数值类型。

        参数:
            dtype: Polars数据类型

        返回:
            bool: 是否为数值类型
        """
        numeric_dtypes = [
            pl.Int8, pl.Int16, pl.Int32, pl.Int64,
            pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64,
            pl.Float32, pl.Float64,
        ]
        return dtype in numeric_dtypes

    def get_data_summary(self) -> Dict[str, Any]:
        """获取数据摘要信息。

        返回数据的基本统计信息，用于快速了解数据概况。

        返回:
            dict: 数据摘要，包含行数、列数、内存占用等
        """
        return {
            "row_count": self.data.height,
            "column_count": len(self.data.columns),
            "column_names": self.data.columns,
            "dtypes": {col: str(self.data[col].dtype) for col in self.data.columns},
            "memory_usage_bytes": self.data.estimated_size(),
            "null_counts": {col: self.data[col].null_count() for col in self.data.columns},
        }
