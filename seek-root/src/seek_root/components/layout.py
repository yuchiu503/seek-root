"""Dash 应用布局和创建模块。

本模块负责创建 Dash 应用实例、配置布局和主题，注册全局导航回调。

函数:
    create_app: 创建并配置 Dash 应用
    get_theme: 获取 Mantine 主题配置

全局变量:
    app: 模块级 Dash 应用实例
"""

import dash
from dash import Dash, html, dcc, Output, Input, State
import dash_mantine_components as dmc

# 全局主题配置
LIGHT_THEME = {
    "primaryColor": "green",
    "fontFamily": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    "defaultRadius": "md",
    "colors": {
        "green": [
            "#ecfdf5", "#d1fae5", "#a7f3d0", "#6ee7b7", "#34d399",
            "#10b981", "#059669", "#047857", "#065f46", "#064e3b",
        ],
        "violet": [
            "#f5f3ff", "#ede9fe", "#ddd6fe", "#c4b5fd", "#a78bfa",
            "#8b5cf6", "#7c3aed", "#6d28d9", "#5b21b6", "#4c1d95",
        ],
    },
}

DARK_THEME = {
    "primaryColor": "green",
    "fontFamily": "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
    "defaultRadius": "md",
    "colors": {
        "green": [
            "#1a1a2e", "#164a3d", "#1a5f4a", "#228c6a", "#34d399",
            "#4ade80", "#6ee7b7", "#a7f3d0", "#d1fae5", "#ecfdf5",
        ],
        "violet": [
            "#1e1b4b", "#2e1f5c", "#3f2a6e", "#533a82", "#6d4f9e",
            "#8b6fbc", "#a78bfa", "#c4b5fd", "#ddd6fe", "#ede9fe",
        ],
    },
    "dark": True,
}


def get_theme(theme_name: str = "light") -> dict:
    """获取 Mantine 主题配置。

    参数:
        theme_name: 主题名称 ('light' 或 'dark')

    返回:
        dict: Mantine 主题配置字典
    """
    return LIGHT_THEME if theme_name == "light" else DARK_THEME


def create_app() -> Dash:
    """创建并配置 Dash 应用。

    创建 Seek Root Dash 应用实例，配置布局、主题和全局组件。

    返回:
        Dash: 配置完成的 Dash 应用实例
    """
    app = Dash(
        __name__,
        use_pages=False,
        pages_folder="",
        suppress_callback_exceptions=True,
        title="Seek Root - 因果推断分析平台",
    )

    # 存储组件
    theme_storage = dcc.Store(id="theme-storage", data="light")
    page_storage = dcc.Store(id="current-page", data="home")
    data_store = dcc.Store(id="app-data-store", storage_type="session")

    # 顶部导航栏
    header = dmc.AppShellHeader(
        h=60,
        children=[
            dmc.Group(
                children=[
                    dmc.Stack(
                        children=[
                            dmc.Text("Seek Root", size="xl", fw=700, style={"color": "#10b981"}),
                            dmc.Text("让每个人都能找到数据背后的因果", size="xs", style={"color": "#6b7280"}),
                        ],
                        gap=0, ml=20,
                    ),
                    dmc.Group(
                        children=[
                            dmc.ActionIcon(
                                id="theme-toggle", variant="subtle", size="lg",
                                children=[dmc.Text(id="theme-icon", children="🌙")],
                            ),
                        ],
                        mr=20,
                    ),
                ],
                justify="space-between", align="center", h="100%",
            ),
        ],
    )

    # 侧边导航
    sidebar = dmc.AppShellNavbar(
        w=220,
        children=[
            dmc.NavLink(label="🏠  首页", id="nav-home", style={"borderRadius": "8px", "margin": "4px 8px"}),
            dmc.NavLink(label="📁  上传数据", id="nav-data", style={"borderRadius": "8px", "margin": "4px 8px"}),
            dmc.NavLink(label="🔬  分析", id="nav-analysis", style={"borderRadius": "8px", "margin": "4px 8px"}),
            dmc.NavLink(label="📝  结果报告", id="nav-results", style={"borderRadius": "8px", "margin": "4px 8px"}),
            dmc.NavLink(label="ℹ️  关于", id="nav-about", style={"borderRadius": "8px", "margin": "4px 8px"}),
        ],
    )

    # 主内容区域
    main_content = dmc.AppShellMain(
        id="main-content-area",
        children=[html.Div(id="page-content")],
        style={"backgroundColor": "#f8fafc"},
    )

    # 完整布局
    app.layout = dmc.MantineProvider(
        id="mantine-provider",
        theme=get_theme("light"),
        children=[
            theme_storage, page_storage, data_store,
            dmc.AppShell(
                children=[header, sidebar, main_content],
                navbar={"width": 220},
                header={"height": 60},
                padding="md",
            ),
        ],
    )

    return app


# ============ 创建应用实例 ============
app = create_app()


# ============ 全局导航回调 ============
@app.callback(
    Output("mantine-provider", "theme"),
    Output("theme-icon", "children"),
    Output("theme-storage", "data"),
    Input("theme-toggle", "n_clicks"),
    State("theme-storage", "data"),
)
def toggle_theme(n_clicks, current_theme):
    """主题切换回调。"""
    if n_clicks is None:
        return get_theme("light"), "🌙", "light"
    new_theme = "dark" if current_theme == "light" else "light"
    icon = "☀️" if new_theme == "dark" else "🌙"
    return get_theme(new_theme), icon, new_theme


@app.callback(
    Output("page-content", "children"),
    Input("nav-home", "n_clicks"),
    Input("nav-data", "n_clicks"),
    Input("nav-analysis", "n_clicks"),
    Input("nav-results", "n_clicks"),
    Input("nav-about", "n_clicks"),
    Input("current-page", "data"),
)
def render_current_page(home_clicks, data_clicks, analysis_clicks, results_clicks, about_clicks, page):
    """根据导航状态渲染当前页面。"""
    ctx = dash.callback_context
    page_name = page or "home"

    if ctx.triggered:
        trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
        if trigger_id in ["nav-home", "nav-data", "nav-analysis", "nav-results", "nav-about"]:
            page_name = trigger_id.replace("nav-", "")

    # 根据页面名称渲染内容
    if page_name == "home":
        from seek_root.pages.home import render_home_page
        return render_home_page()
    elif page_name == "data":
        from seek_root.pages.data_upload import render_data_page
        return render_data_page()
    elif page_name == "analysis":
        from seek_root.pages.analysis import render_analysis_page
        return render_analysis_page()
    elif page_name == "results":
        from seek_root.pages.results import render_results_page
        return render_results_page()
    elif page_name == "about":
        from seek_root.pages.about import render_about_page
        return render_about_page()
    else:
        from seek_root.pages.home import render_home_page
        return render_home_page()


@app.callback(
    Output("current-page", "data", allow_duplicate=True),
    Input("nav-home", "n_clicks"),
    Input("nav-data", "n_clicks"),
    Input("nav-analysis", "n_clicks"),
    Input("nav-results", "n_clicks"),
    Input("nav-about", "n_clicks"),
    State("current-page", "data"),
    prevent_initial_call=True,
)
def update_page_from_nav(home_clicks, data_clicks, analysis_clicks, results_clicks, about_clicks, current_page):
    """根据导航点击更新 current-page 状态。"""
    ctx = dash.callback_context
    if not ctx.triggered:
        return current_page
    trigger_id = ctx.triggered[0]["prop_id"].split(".")[0]
    mapping = {
        "nav-home": "home", "nav-data": "data", "nav-analysis": "analysis",
        "nav-results": "results", "nav-about": "about",
    }
    return mapping.get(trigger_id, current_page)
