"""Dash应用布局和创建模块。

本模块负责创建Dash应用实例、配置布局和主题。

函数:
    create_app: 创建并配置Dash应用
    get_theme: 获取Mantine主题配置
"""

from dash import Dash
import dash_mantine_components as dmc
from dash import html, dcc, callback, Output, Input
from pathlib import Path
import os

# 探索绿配色方案
THEME_COLORS = {
    "primary": "#10b981",      # 绿色
    "secondary": "#8b5cf6",   # 紫色
    "gradient": ["#064e3b", "#10b981"],  # 渐变
}

# 主题配置
LIGHT_THEME = {
    "primaryColor": "green",
    "fontFamily": "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif",
    "defaultRadius": "md",
    "colors": {
        "green": [
            "#ecfdf5",
            "#d1fae5",
            "#a7f3d0",
            "#6ee7b7",
            "#34d399",
            "#10b981",
            "#059669",
            "#047857",
            "#065f46",
            "#064e3b",
        ],
        "violet": [
            "#f5f3ff",
            "#ede9fe",
            "#ddd6fe",
            "#c4b5fd",
            "#a78bfa",
            "#8b5cf6",
            "#7c3aed",
            "#6d28d9",
            "#5b21b6",
            "#4c1d95",
        ],
    },
}

DARK_THEME = {
    "primaryColor": "green",
    "fontFamily": "-apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif",
    "defaultRadius": "md",
    "colors": {
        "green": [
            "#1a1a2e",
            "#164a3d",
            "#1a5f4a",
            "#228c6a",
            "#34d399",
            "#4ade80",
            "#6ee7b7",
            "#a7f3d0",
            "#d1fae5",
            "#ecfdf5",
        ],
        "violet": [
            "#1e1b4b",
            "#2e1f5c",
            "#3f2a6e",
            "#533a82",
            "#6d4f9e",
            "#8b6fbc",
            "#a78bfa",
            "#c4b5fd",
            "#ddd6fe",
            "#ede9fe",
        ],
    },
    "dark": True,
}


def get_theme(theme_name: str = "light") -> dict:
    """获取Mantine主题配置。

    参数:
        theme_name: 主题名称 ('light' 或 'dark')

    返回:
        dict: Mantine主题配置字典
    """
    return LIGHT_THEME if theme_name == "light" else DARK_THEME


def create_app() -> Dash:
    """创建并配置Dash应用。

    创建Seek Root Dash应用实例，配置布局、主题和全局组件。

    返回:
        Dash: 配置完成的Dash应用实例
    """
    # 创建Dash应用
    app = Dash(
        __name__,
        use_pages=True,
        suppress_callback_exceptions=True,
        title="Seek Root - 因果推断分析平台",
    )

    # 读取自定义CSS
    assets_path = Path(__file__).parent.parent / "assets"
    if assets_path.exists():
        app.css.config.locate_files(assets_path)

    # 主题存储
    theme_storage = dcc.Store(id="theme-storage", data="light")

    # 顶部导航栏
    header = dmc.AppShellHeader(
        height=60,
        children=[
            dmc.Group(
                children=[
                    # Logo区域
                    dmc.Stack(
                        children=[
                            dmc.Text(
                                "Seek Root",
                                size="xl",
                                weight=700,
                                style={"color": "#10b981", "letterSpacing": "-0.5px"},
                            ),
                            dmc.Text(
                                "让每个人都能找到数据背后的因果",
                                size="xs",
                                style={"color": "#6b7280"},
                            ),
                        ],
                        spacing=0,
                        ml=20,
                    ),
                    # 右侧功能区
                    dmc.Group(
                        children=[
                            # 主题切换
                            dmc.ActionIcon(
                                id="theme-toggle",
                                variant="subtle",
                                size="lg",
                                children=[
                                    dmc.ThemeIcon(
                                        children="🌙" if True else "☀️",
                                        variant="transparent",
                                    ),
                                ],
                            ),
                            # 用户信息
                            dmc.Menu(
                                children=[
                                    dmc.MenuTarget(
                                        dmc.Avatar(
                                            "U",
                                            radius="xl",
                                            size="sm",
                                            style={"cursor": "pointer"},
                                        )
                                    ),
                                    dmc.MenuDropdown(
                                        children=[
                                            dmc.MenuItem("个人中心", leftSection="👤"),
                                            dmc.MenuItem("分析历史", leftSection="📊"),
                                            dmc.MenuDivider(),
                                            dmc.MenuItem("退出登录", leftSection="🚪"),
                                        ]
                                    ),
                                ],
                                width=200,
                            ),
                        ],
                        mr=20,
                    ),
                ],
                justify="space-between",
                align="center",
                h="100%",
            ),
        ],
    )

    # 侧边导航
    sidebar = dmc.AppShellNavbar(
        width=200,
        children=[
            dmc.NavLink(
                label="首页",
                leftSection="🏠",
                href="/",
                active=True,
                style={"borderRadius": "8px", "margin": "4px 8px"},
            ),
            dmc.NavLink(
                label="上传数据",
                leftSection="📁",
                href="/data",
                style={"borderRadius": "8px", "margin": "4px 8px"},
            ),
            dmc.NavLink(
                label="分析",
                leftSection="🔬",
                href="/analysis",
                style={"borderRadius": "8px", "margin": "4px 8px"},
            ),
            dmc.NavLink(
                label="结果报告",
                leftSection="📝",
                href="/results",
                style={"borderRadius": "8px", "margin": "4px 8px"},
            ),
            dmc.NavLink(
                label="关于",
                leftSection="ℹ️",
                href="/about",
                style={"borderRadius": "8px", "margin": "4px 8px"},
            ),
        ],
    )

    # 主内容区域
    main_content = dmc.AppShellMain(
        children=[
            dcc.Store(id="app-data-store", storage_type="session"),
            dash.page_container,
        ],
        style={"backgroundColor": "#f8fafc" if True else "#0f172a"},
    )

    # 完整布局
    app.layout = dmc.MantineProvider(
        id="mantine-provider",
        theme=get_theme("light"),
        children=[
            theme_storage,
            dmc.AppShell(
                children=[
                    header,
                    sidebar,
                    main_content,
                ],
                navbar={"width": 200, " breakpoint": "sm"},
                header={"height": 60},
                padding="md",
            ),
        ],
    )

    # 主题切换回调
    @callback(
        Output("mantine-provider", "theme"),
        Output("theme-storage", "data"),
        Input("theme-toggle", "n_clicks"),
        State("theme-storage", "data"),
    )
    def toggle_theme(n_clicks, current_theme):
        """切换深浅色主题。

        参数:
            n_clicks: 切换按钮点击次数
            current_theme: 当前主题

        返回:
            tuple: (新主题配置, 新主题名称)
        """
        if n_clicks and n_clicks > 0:
            new_theme = "dark" if current_theme == "light" else "light"
            return get_theme(new_theme), new_theme
        return get_theme(current_theme), current_theme

    return app


# 创建应用实例（模块级）
app = create_app()
