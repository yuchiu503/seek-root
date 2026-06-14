"""Seek Root 服务启动模块。

本模块负责启动Dash应用服务。

函数:
    run_server: 启动Web服务的入口函数
"""

import os
from typing import Optional

from seek_root.config.settings import settings


def run_server(
    host: str = "0.0.0.0",
    port: int = 8050,
    debug: bool = False,
    default_theme: str = "light",
) -> None:
    """启动Seek Root Web服务。

    参数:
        host: 服务监听地址
        port: 服务监听端口
        debug: 是否开启调试模式
        default_theme: 默认主题 ('light' 或 'dark')
    """
    # 设置环境变量
    os.environ.setdefault("FLASK_ENV", "development" if debug else "production")

    # 导入Dash应用（避免循环导入）
    from seek_root.server import app

    # 更新主题设置
    app.title = "Seek Root - 因果推断分析平台"

    # 启动服务
    app.run(
        host=host,
        port=port,
        debug=debug,
        threaded=True,
    )


if __name__ == "__main__":
    run_server()
