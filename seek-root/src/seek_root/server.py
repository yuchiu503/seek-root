"""Seek Root 服务启动模块。

本模块负责启动 Dash 应用服务。

函数:
    run_server: 启动 Web 服务的入口函数
"""

import os
import sys
from typing import Optional

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入应用（会触发所有页面的回调注册）
from seek_root.components.layout import app  # noqa: E402


def run_server(
    host: str = "0.0.0.0",
    port: int = 8050,
    debug: bool = False,
) -> None:
    """启动 Seek Root Web 服务。

    参数:
        host: 服务监听地址
        port: 服务监听端口
        debug: 是否开启调试模式
    """
    print(f"🌱 Seek Root 启动中...")
    print(f"   地址: http://{host}:{port}")
    print(f"   调试模式: {'开启' if debug else '关闭'}")
    print()
    print("   支持的因果推断方法:")
    print("   • DID 双差分法")
    print("   • PSM 倾向得分匹配")
    print("   • RD 断点回归")
    print("   • IV 工具变量法")
    print("   • CF 因果森林")
    print()

    # 设置应用标题
    app.title = "Seek Root - 因果推断分析平台"

    # 启动服务
    app.run(
        host=host,
        port=port,
        debug=debug,
    )


if __name__ == "__main__":
    # 命令行参数解析
    import argparse

    parser = argparse.ArgumentParser(description="Seek Root - 因果推断分析平台")
    parser.add_argument("--host", default="0.0.0.0", help="监听地址")
    parser.add_argument("--port", type=int, default=8050, help="监听端口")
    parser.add_argument("--debug", action="store_true", help="开启调试模式")

    args = parser.parse_args()
    run_server(host=args.host, port=args.port, debug=args.debug)
