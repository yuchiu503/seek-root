"""Seek Root CLI命令行入口模块。

提供命令行界面，支持启动服务、管理配置等操作。

命令:
    serve: 启动Web服务
    version: 显示版本信息
"""

import click
import sys
from pathlib import Path

from seek_root import __version__


@click.group()
@click.version_option(version=__version__)
def main() -> None:
    """Seek Root - 面向业务人员的因果推断Web应用。

    让每个人都能找到数据背后的因果关系。
    """
    pass


@main.command()
@click.option(
    "--host",
    default="0.0.0.0",
    help="服务监听地址 (默认: 0.0.0.0)",
)
@click.option(
    "--port",
    default=8050,
    help="服务监听端口 (默认: 8050)",
)
@click.option(
    "--debug",
    is_flag=True,
    default=False,
    help="是否开启调试模式",
)
@click.option(
    "--theme",
    default="light",
    type=click.Choice(["light", "dark"]),
    help="默认主题 (默认: light)",
)
def serve(host: str, port: int, debug: bool, theme: str) -> None:
    """启动Seek Root Web服务。

    示例:
        $ seek-root serve
        $ seek-root serve --port 8080
        $ seek-root serve --debug
    """
    from seek_root.server import run_server

    click.echo(f"启动 Seek Root 服务...")
    click.echo(f"地址: http://{host}:{port}")
    click.echo(f"主题: {theme}")
    click.echo(f"调试: {'开启' if debug else '关闭'}")

    run_server(host=host, port=port, debug=debug, default_theme=theme)


@main.command()
def info() -> None:
    """显示Seek Root版本和配置信息。"""
    click.echo(f"Seek Root 版本: {__version__}")
    click.echo(f"Python 版本: {sys.version}")
    click.echo(f"工作目录: {Path.cwd()}")


if __name__ == "__main__":
    main()
