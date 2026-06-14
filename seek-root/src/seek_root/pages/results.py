"""结果页面模块。

展示因果分析的结果和报告。
"""

import dash
import dash_mantine_components as dmc
from dash import html, dcc, register_page

dash.register_page(__name__, path="/results", title="分析结果")


def layout():
    """结果页面布局。

    返回:
        html.Div: 结果页面组件
    """
    return html.Div(
        style={"maxWidth": "1200px", "margin": "0 auto", "padding": "20px"},
        children=[
            # 页面标题
            dmc.Title("分析结果", order=1, mb="md"),
            dmc.Text(
                "查看因果推断分析的详细结果和业务解读。",
                c="dimmed",
                mb="xl",
            ),
            # 暂无结果提示
            dmc.Paper(
                shadow="md",
                p="xl",
                radius="md",
                style={"textAlign": "center"},
                children=[
                    dmc.ThemeIcon(
                        "📊",
                        size=80,
                        variant="transparent",
                    ),
                    dmc.Title("暂无分析结果", order=3, mt="md"),
                    dmc.Text(
                        "请先上传数据并执行分析",
                        c="dimmed",
                        mt="sm",
                    ),
                    dmc.Button(
                        "去分析",
                        variant="filled",
                        color="green",
                        mt="lg",
                        href="/analysis",
                    ),
                ],
            ),
        ],
    )
