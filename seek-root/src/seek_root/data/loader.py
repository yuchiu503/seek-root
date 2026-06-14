"""数据加载器模块。

本模块负责从多种数据源加载数据，
支持Excel(.xlsx/.xls)和CSV(.csv)格式，
使用Polars作为主要数据处理引擎。

类:
    DataLoader: 数据加载器，支持多种文件格式
"""

import io
from pathlib import Path
from typing import Optional, Dict, Any, Union
import polars as pl

from seek_root.utils.errors import DataLoadError


class DataLoader:
    """数据加载器类。

    负责从文件或内存中加载数据，
    自动识别文件格式并转换为Polars DataFrame。

    参数:
        file_path (str | Path, optional): 文件路径
        content (bytes, optional): 文件内容（用于Web上传场景）

    属性:
        data (pl.DataFrame): 加载后的数据
        file_name (str): 原始文件名
        file_type (str): 文件类型（csv/excel）
        row_count (int): 数据行数
        column_count (int): 数据列数

    示例:
        >>> loader = DataLoader(file_path="data.csv")
        >>> df = loader.load()
        >>> print(f"加载了 {loader.row_count} 行数据")
    """

    def __init__(
        self,
        file_path: Optional[Union[str, Path]] = None,
        content: Optional[bytes] = None,
    ) -> None:
        """初始化数据加载器。

        参数:
            file_path: 文件路径（与content二选一）
            content: 文件字节内容（与file_path二选一）
        """
        self._file_path: Optional[Path] = None
        self._content: Optional[bytes] = None
        self._file_name: str = ""
        self._file_type: str = ""

        if file_path:
            self._file_path = Path(file_path)
            self._file_name = self._file_path.name
            self._file_type = self._file_path.suffix.lower().lstrip(".")
        elif content:
            self._content = content
            self._file_type = self._detect_type_from_content(content)
        else:
            raise DataLoadError("必须提供 file_path 或 content 参数")

    @staticmethod
    def _detect_type_from_content(content: bytes) -> str:
        """从文件内容检测文件类型。

        通过检查文件头字节来识别CSV或Excel格式。

        参数:
            content: 文件字节内容

        返回:
            str: 文件类型 ('csv' 或 'excel')

        异常:
            DataLoadError: 无法识别的文件类型
        """
        # 检查BOM或文件头
        if content[:4] == b"PK\x03\x04":
            # ZIP-based format (xlsx)
            return "xlsx"
        elif content[:8] == b"\xd0\xcf\x11\xe0\xa1\xb1":
            # OLE format (xls)
            return "xls"

        # 尝试UTF-8解码检查是否为CSV
        try:
            content[:100].decode("utf-8")
            return "csv"
        except UnicodeDecodeError:
            pass

        raise DataLoadError("无法识别的文件格式，请上传CSV或Excel文件")

    def load(self) -> pl.DataFrame:
        """加载数据文件。

        根据文件类型自动选择合适的加载方式，
        将数据加载为Polars DataFrame。

        返回:
            pl.DataFrame: 加载后的数据

        异常:
            DataLoadError: 加载失败时抛出
        """
        try:
            if self._content:
                # 从内存加载
                return self._load_from_content()
            elif self._file_path:
                # 从文件加载
                return self._load_from_file()
            else:
                raise DataLoadError("未提供数据源")
        except Exception as e:
            raise DataLoadError(f"数据加载失败: {str(e)}")

    def _load_from_content(self) -> pl.DataFrame:
        """从内存内容加载数据。

        将上传的文件内容加载为DataFrame。

        返回:
            pl.DataFrame: 加载后的数据
        """
        if self._file_type in ("xlsx", "xls"):
            # Excel文件
            df = pl.read_excel(
                io.BytesIO(self._content),
                engine="openpyxl" if self._file_type == "xlsx" else "xlrd",
            )
        else:
            # CSV文件
            # 尝试自动检测分隔符和编码
            try:
                df = pl.read_csv(io.BytesIO(self._content))
            except Exception:
                # 尝试其他常见编码
                for encoding in ["utf-8", "gbk", "gb2312", "latin1"]:
                    try:
                        df = pl.read_csv(
                            io.BytesIO(self._content),
                            encoding=encoding,
                        )
                        break
                    except Exception:
                        continue
                else:
                    raise DataLoadError("无法解析CSV文件，请检查文件编码")

        return df

    def _load_from_file(self) -> pl.DataFrame:
        """从文件路径加载数据。

        读取本地文件并加载为DataFrame。

        返回:
            pl.DataFrame: 加载后的数据
        """
        if not self._file_path.exists():
            raise DataLoadError(f"文件不存在: {self._file_path}")

        if self._file_type == "csv":
            df = pl.read_csv(self._file_path)
        elif self._file_type in ("xlsx", "xls"):
            df = pl.read_excel(
                self._file_path,
                engine="openpyxl" if self._file_type == "xlsx" else "xlrd",
            )
        else:
            raise DataLoadError(f"不支持的文件格式: {self._file_type}")

        return df

    @property
    def file_name(self) -> str:
        """获取原始文件名。

        返回:
            str: 文件名
        """
        if self._file_name:
            return self._file_name
        elif self._file_path:
            return self._file_path.name
        return "unknown"

    @property
    def file_type(self) -> str:
        """获取文件类型。

        返回:
            str: 文件类型 (csv/excel)
        """
        return self._file_type

    @property
    def row_count(self) -> int:
        """获取数据行数。

        返回:
            int: 行数（加载后才能使用）
        """
        if hasattr(self, "_data") and self._data is not None:
            return self._data.height
        return 0

    @property
    def column_count(self) -> int:
        """获取数据列数。

        返回:
            int: 列数（加载后才能使用）
        """
        if hasattr(self, "_data") and self._data is not None:
            return len(self._data.columns)
        return 0

    def preview(
        self,
        n_rows: int = 10,
        n_cols: Optional[int] = None,
    ) -> pl.DataFrame:
        """预览数据。

        返回数据的前N行，用于快速查看数据结构和内容。

        参数:
            n_rows: 预览行数，默认10
            n_cols: 预览列数，默认全部

        返回:
            pl.DataFrame: 预览数据
        """
        if not hasattr(self, "_data") or self._data is None:
            raise DataLoadError("请先调用 load() 方法加载数据")

        df = self._data.head(n_rows)
        if n_cols:
            df = df.select(df.columns[:n_cols])

        return df

    def get_column_info(self) -> list[Dict[str, Any]]:
        """获取列信息。

        返回数据中每个列的名称、类型、缺失值统计等信息。

        返回:
            list[Dict]: 列信息列表，每个元素包含:
                - name: 列名
                - dtype: 数据类型
                - null_count: 缺失值数量
                - null_ratio: 缺失值比例
                - unique_count: 唯一值数量
                - sample_values: 示例值（最多5个）
        """
        if not hasattr(self, "_data") or self._data is None:
            raise DataLoadError("请先调用 load() 方法加载数据")

        columns_info = []
        for col_name in self._data.columns:
            col = self._data[col_name]
            info = {
                "name": col_name,
                "dtype": str(col.dtype),
                "null_count": col.null_count(),
                "null_ratio": col.null_count() / len(col) if len(col) > 0 else 0,
                "unique_count": col.n_unique(),
                "sample_values": col.drop_nulls().unique().head(5).to_list(),
            }
            columns_info.append(info)

        return columns_info
