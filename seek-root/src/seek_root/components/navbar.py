"""导航栏组件模块。

提供侧边栏和顶部导航栏组件。
"""

import dash_mantine_components as dmc
from dash import html, dcc


class Navbar:
    """导航栏组件类。

    提供应用导航栏的构建方法。

    参数:
        current_path: 当前页面路径
    """

    @staticmethod
    def create_sidebar(current_path: str = "/") -> dmc.AppShellNavbar:
        """创建侧边导航栏。

        参数:
            current_path: 当前页面路径，用于高亮当前项

        返回:
            dmc.AppShellNavbar: 侧边导航栏组件
        """
        nav_items = [
            {"label": "首页", "icon": "🏠", "href": "/"},
            {"label": "上传数据", "icon": "📁", "href": "/data"},
            {"label": "分析", "icon": "🔬", "href": "/analysis"},
            {"label": "结果报告", "icon": "📝", "href": "/results"},
            {"label": "关于", "icon": "ℹ️", "href": "/about"},
        ]

        nav_links = []
        for item in nav_items:
            is_active = current_path == item["href"]
            nav_links.append(
                dmc.NavLink(
                    label=item["label"],
                    leftSection=item["icon"],
                    href=item["href"],
                    active=is_active,
                    style={
                        "borderRadius": "8px",
                        "margin": "4px 8px",
                        "fontWeight": 600 if is_active else 400,
                    },
                )
            )

        return dmc.AppShellNavbar(
            width=200,
            children=nav_links,
        )

    @staticmethod
    def create_header() -> dmc.AppShellHeader:
        """创建顶部导航栏。

        返回:
            dmc.AppShellHeader: 顶部导航栏组件
        """
        return dmc.AppShellHeader(
            height=60,
            children=[
                dmc.Group(
                    children=[
                        # Logo
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
                        dmc.Group(
                            children=[
                                # 主题切换
                                dmc.ActionIcon(
                                    id="theme-toggle",
                                    variant="subtle",
                                    size="lg",
                                    children=[
                                        html.Span("☀️", id="theme-icon")
                                    ],
                                ),
                                # 用户菜单
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
