"""数据清洗器模块。

本模块负责对数据进行清洗和预处理，
包括处理缺失值、异常值、类型转换等操作，
确保数据满足因果推断分析的要求。

类:
    DataCleaner: 数据清洗器
"""

from typing import Any, Dict, List, Optional, Union
import polars as pl


class DataCleaner:
    """数据清洗器类。

    负责对原始数据进行清洗和预处理，
    为因果推断分析做好准备。

    参数:
        data (pl.DataFrame): 要清洗的数据

    示例:
        >>> cleaner = DataCleaner(df)
        >>> df_clean = cleaner.clean()
    """

    def __init__(self, data: pl.DataFrame) -> None:
        """初始化数据清洗器。

        参数:
            data: 要清洗的Polars DataFrame
        """
        self.data = data.copy()

    def clean(
        self,
        drop_duplicates: bool = True,
        handle_missing: str = "warn",
        outlier_threshold: Optional[float] = None,
    ) -> pl.DataFrame:
        """执行数据清洗。

        依次执行：去重、缺失值处理、异常值处理。

        参数:
            drop_duplicates: 是否删除重复行
            handle_missing: 缺失值处理策略 ('warn', 'drop', 'fill_mean', 'fill_median')
            outlier_threshold: 异常值阈值（Z-score），超过此值视为异常（可选）

        返回:
            pl.DataFrame: 清洗后的数据
        """
        if drop_duplicates:
            self.data = self._drop_duplicates()

        if handle_missing != "warn":
            self.data = self._handle_missing(handle_missing)

        if outlier_threshold:
            self.data = self._handle_outliers(outlier_threshold)

        return self.data

    def _drop_duplicates(self) -> pl.DataFrame:
        """删除重复行。

        返回:
            pl.DataFrame: 去重后的数据
        """
        before_count = len(self.data)
        df = self.data.unique()
        after_count = len(df)

        if before_count > after_count:
            print(f"删除了 {before_count - after_count} 行重复数据")

        return df

    def _handle_missing(self, strategy: str) -> pl.DataFrame:
        """处理缺失值。

        参数:
            strategy: 处理策略
                - 'warn': 仅警告，不处理
                - 'drop': 删除包含缺失值的行
                - 'fill_mean': 用均值填充数值列
                - 'fill_median': 用中位数填充数值列

        返回:
            pl.DataFrame: 处理后的数据
        """
        null_counts = {col: self.data[col].null_count() for col in self.data.columns}
        total_nulls = sum(null_counts.values())

        if total_nulls == 0:
            return self.data

        print(f"发现 {total_nulls} 个缺失值")

        if strategy == "warn":
            for col, count in null_counts.items():
                if count > 0:
                    print(f"  列 '{col}': {count} 个缺失值")
            return self.data

        elif strategy == "drop":
            df = self.data.drop_nulls()
            print(f"删除了 {len(self.data) - len(df)} 行包含缺失值的数据")
            return df

        elif strategy == "fill_mean":
            for col in self.data.columns:
                if null_counts[col] > 0 and self._is_numeric_col(col):
                    mean_val = self.data[col].mean()
                    self.data = self.data.with_columns(
                        pl.col(col).fill_null(mean_val)
                    )
                    print(f"  列 '{col}': 用均值 {mean_val:.2f} 填充")
            return self.data

        elif strategy == "fill_median":
            for col in self.data.columns:
                if null_counts[col] > 0 and self._is_numeric_col(col):
                    median_val = self.data[col].median()
                    self.data = self.data.with_columns(
                        pl.col(col).fill_null(median_val)
                    )
                    print(f"  列 '{col}': 用中位数 {median_val:.2f} 填充")
            return self.data

        return self.data

    def _handle_outliers(
        self,
        threshold: float = 3.0,
        strategy: str = "clip",
    ) -> pl.DataFrame:
        """处理异常值。

        使用Z-score方法识别异常值，并用指定策略处理。

        参数:
            threshold: Z-score阈值，超过此值视为异常
            strategy: 处理策略 ('clip', 'drop', 'warn')

        返回:
            pl.DataFrame: 处理后的数据
        """
        numeric_cols = [col for col in self.data.columns if self._is_numeric_col(col)]
        outlier_info = {}

        for col in numeric_cols:
            col_data = self.data[col]
            mean_val = col_data.mean()
            std_val = col_data.std()

            if std_val == 0:
                continue

            z_scores = ((col_data - mean_val) / std_val).abs()
            n_outliers = (z_scores > threshold).sum()

            if n_outliers > 0:
                outlier_info[col] = {
                    "count": n_outliers,
                    "mean": mean_val,
                    "std": std_val,
                }

        if not outlier_info:
            return self.data

        if strategy == "warn":
            for col, info in outlier_info.items():
                print(f"列 '{col}': 发现 {info['count']} 个异常值")
            return self.data

        elif strategy == "drop":
            mask = pl.ones(len(self.data), dtype=pl.Boolean)
            for col in numeric_cols:
                col_data = self.data[col]
                mean_val = outlier_info[col]["mean"]
                std_val = outlier_info[col]["std"]
                z_scores = ((col_data - mean_val) / std_val).abs()
                mask = mask & (z_scores <= threshold)

            before = len(self.data)
            self.data = self.data.filter(mask)
            print(f"删除了 {before - len(self.data)} 行包含异常值的数据")
            return self.data

        elif strategy == "clip":
            for col in numeric_cols:
                if col in outlier_info:
                    mean_val = outlier_info[col]["mean"]
                    std_val = outlier_info[col]["std"]
                    lower = mean_val - threshold * std_val
                    upper = mean_val + threshold * std_val
                    self.data = self.data.with_columns(
                        pl.col(col).clip(lower, upper)
                    )
                    print(f"列 '{col}': 将异常值裁剪到 [{lower:.2f}, {upper:.2f}]")
            return self.data

        return self.data

    def _is_numeric_col(self, col_name: str) -> bool:
        """检查列是否为数值类型。

        参数:
            col_name: 列名

        返回:
            bool: 是否为数值类型
        """
        dtype = self.data[col_name].dtype
        return dtype in [
            pl.Int8, pl.Int16, pl.Int32, pl.Int64,
            pl.UInt8, pl.UInt16, pl.UInt32, pl.UInt64,
            pl.Float32, pl.Float64,
        ]

    def standardize_columns(
        self,
        columns: Optional[List[str]] = None,
    ) -> pl.DataFrame:
        """标准化数值列。

        将指定数值列标准化（均值=0，标准差=1）。

        参数:
            columns: 要标准化的列名列表，默认为所有数值列

        返回:
            pl.DataFrame: 标准化后的数据
        """
        if columns is None:
            columns = [col for col in self.data.columns if self._is_numeric_col(col)]

        df = self.data.clone()
        for col in columns:
            if col in df.columns and self._is_numeric_col(col):
                mean_val = df[col].mean()
                std_val = df[col].std()
                if std_val > 0:
                    df = df.with_columns(
                        ((pl.col(col) - mean_val) / std_val).alias(col)
                    )

        return df

    def create_discrete_bins(
        self,
        column: str,
        n_bins: int = 5,
        labels: Optional[List[str]] = None,
        new_column_name: Optional[str] = None,
    ) -> pl.DataFrame:
        """将连续变量离散化。

        将数值列分箱为离散类别。

        参数:
            column: 要离散化的列名
            n_bins: 分箱数量
            labels: 分箱标签列表
            new_column_name: 新列名，默认为原列名加上后缀 '_binned'

        返回:
            pl.DataFrame: 添加了离散化列的数据
        """
        if new_column_name is None:
            new_column_name = f"{column}_binned"

        col_data = self.data[column]
        min_val = col_data.min()
        max_val = col_data.max()

        bins = [min_val + (max_val - min_val) * i / n_bins for i in range(n_bins + 1)]
        bins[0] = float("-inf")
        bins[-1] = float("inf")

        if labels is None:
            labels = [f"Q{i+1}" for i in range(n_bins)]

        df = self.data.with_columns(
            pl.col(column).cut(bins[1:-1], labels=labels).alias(new_column_name)
        )

        return df

    def encode_categorical(
        self,
        columns: Optional[List[str]] = None,
        method: str = "onehot",
    ) -> pl.DataFrame:
        """编码类别变量。

        将类别变量转换为数值形式。

        参数:
            columns: 要编码的列名列表，默认为所有类别列
            method: 编码方法 ('onehot' 或 'label')

        返回:
            pl.DataFrame: 编码后的数据
        """
        if columns is None:
            columns = [
                col for col in self.data.columns
                if self.data[col].dtype == pl.Categorical
                or (self.data[col].dtype == pl.Utf8 and self.data[col].n_unique() < 20)
            ]

        if method == "label":
            # 标签编码
            df = self.data.clone()
            for col in columns:
                if col in df.columns:
                    unique_vals = df[col].unique()
                    mapping = {val: i for i, val in enumerate(unique_vals)}
                    df = df.with_columns(
                        pl.col(col).map_dict(mapping).alias(col)
                    )
            return df

        elif method == "onehot":
            # One-hot编码（返回多个列）
            df = self.data.clone()
            for col in columns:
                if col in df.columns:
                    unique_vals = df[col].unique()
                    for val in unique_vals:
                        new_col = f"{col}_{val}"
                        df = df.with_columns(
                            (pl.col(col) == val).cast(pl.Int8).alias(new_col)
                        )
                    df = df.drop(col)
            return df

        return self.data
