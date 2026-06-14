"""存储模块初始化文件。

导出用户存储和分析结果存储功能。
"""

from seek_root.storage.database import Database, get_db

__all__ = ["Database", "get_db"]
