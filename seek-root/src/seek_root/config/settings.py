"""Seek Root 配置模块。

本模块负责加载和管理应用程序的配置参数，
支持从环境变量和 .env 文件中读取配置。
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv

# 加载 .env 文件
load_dotenv()


@dataclass
class Settings:
    """应用程序配置类。

    该类使用 dataclass 模式管理所有配置项，
    支持从环境变量读取，并提供合理的默认值。

    属性:
        debug: 是否开启调试模式
        host: 服务绑定的主机地址
        port: 服务绑定的端口号
        database_url: 数据库连接URL
        data_dir: 数据存储目录路径
        llm_api_key: 大模型API密钥
        llm_api_base: 大模型API地址（OpenAI兼容）
        llm_model: 大模型名称
        default_theme: 默认主题 (light/dark)
    """

    # 服务配置
    debug: bool = field(default_factory=lambda: os.getenv("DEBUG", "false").lower() == "true")
    host: str = field(default_factory=lambda: os.getenv("HOST", "0.0.0.0"))
    port: int = field(default_factory=lambda: int(os.getenv("PORT", "8050")))

    # 数据库配置
    database_url: str = field(
        default_factory=lambda: os.getenv(
            "DATABASE_URL",
            "sqlite:///./data/seek_root.db"
        )
    )

    # 数据目录
    data_dir: Path = field(
        default_factory=lambda: Path(os.getenv("DATA_DIR", "./data"))
    )

    # LLM配置
    llm_api_key: str = field(
        default_factory=lambda: os.getenv("LLM_API_KEY", "")
    )
    llm_api_base: str = field(
        default_factory=lambda: os.getenv(
            "LLM_API_BASE",
            "https://api.openai.com/v1"
        )
    )
    llm_model: str = field(
        default_factory=lambda: os.getenv("LLM_MODEL", "gpt-3.5-turbo")
    )

    # 主题配置
    default_theme: str = field(
        default_factory=lambda: os.getenv("DEFAULT_THEME", "light")
    )

    # 数据限制（免费版）
    free_max_rows: int = 1000  # 免费版最大数据行数
    free_max_methods: int = 2   # 免费版可用方法数

    # 付费版限制
    pro_max_rows: int = 100000  # Pro版最大数据行数

    def __post_init__(self) -> None:
        """初始化后处理。

        确保数据目录存在。
        """
        # 确保数据目录存在
        self.data_dir = Path(self.data_dir)
        if not self.data_dir.exists():
            self.data_dir.mkdir(parents=True, exist_ok=True)

    def get_database_path(self) -> Path:
        """获取数据库文件路径。

        从 database_url 中解析出 SQLite 数据库文件路径。

        返回:
            Path: 数据库文件的绝对路径
        """
        if self.database_url.startswith("sqlite:///"):
            db_path = self.database_url.replace("sqlite:///", "")
            if db_path.startswith("./"):
                db_path = db_path[2:]
            return Path(db_path).resolve()
        return self.data_dir / "seek_root.db"

    def validate(self) -> tuple[bool, Optional[str]]:
        """验证配置是否有效。

        检查必需的配置项是否已正确设置。

        返回:
            tuple: (是否有效, 错误消息)
        """
        if not self.llm_api_key:
            return False, "LLM API密钥未设置，请在 .env 文件中配置 LLM_API_KEY"
        return True, None


# 创建全局配置实例
settings = Settings()
