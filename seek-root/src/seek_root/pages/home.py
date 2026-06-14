"""首页模块。

提供Seek Root应用的首页/引导页面。
"""

import dash
import dash_mantine_components as dmc
from dash import html, dcc, callback, Output, Input
import polars as pl

# 假设数据存储
dash.register_page(__name__, path="/", title="首页")


def layout():
    """首页布局。

    展示产品介绍、三步分析流程和支持的方法。

    返回:
        html.Div: 首页布局组件
    """
    return html.Div(
        style={"maxWidth": "1200px", "margin": "0 auto", "padding": "20px"},
        children=[
            # Hero区域
            dmc.Paper(
                shadow="xl",
                p="xl",
                radius="md",
                style={
                    "background": "linear-gradient(135deg, #064e3b 0%, #10b981 100%)",
                    "color": "white",
                    "textAlign": "center",
                    "marginBottom": "30px",
                },
                children=[
                    dmc.Title(
                        "让每个人都能找到数据背后的因果关系",
                        order=1,
                        style={"color": "white", "marginBottom": "16px"},
                    ),
                    dmc.Text(
                        "问源（Seek Root）- 面向业务人员的因果推断分析平台。"
                        "无需编程，只需上传数据、选择场景、点击分析，即可获得专业的因果分析结果。",
                        size="lg",
                        style={"color": "rgba(255,255,255,0.9)", "marginBottom": "24px"},
                    ),
                    dmc.Group(
                        children=[
                            dmc.Button(
                                "开始分析",
                                size="lg",
                                variant="white",
                                color="dark-green",
                                leftSection="🚀",
                                href="/data",
                            ),
                            dmc.Button(
                                "查看示例",
                                size="lg",
                                variant="outline",
                                color="white",
                                style={"borderColor": "rgba(255,255,255,0.5)"},
                                leftSection="📊",
                            ),
                        ],
                        justify="center",
                    ),
                ],
            ),
            # 三步流程
            dmc.Title("三步完成因果分析", order=2, mb="md"),
            dmc.Grid(
                children=[
                    dmc.GridCol(
                        span=4,
                        children=[
                            dmc.Paper(
                                shadow="md",
                                p="lg",
                                radius="md",
                                children=[
                                    dmc.StepperStep(
                                        completedIcon=dmc.ThemeIcon(
                                            "1",
                                            radius="xl",
                                            size=40,
                                            variant="filled",
                                            color="green",
                                        ),
                                        label=dmc.Text("上传数据", weight=700),
                                        description=dmc.Text("拖拽Excel/CSV文件", size="sm", c="dimmed"),
                                        children=[
                                            html.Div(style={"padding": "10px"}),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                    dmc.GridCol(
                        span=4,
                        children=[
                            dmc.Paper(
                                shadow="md",
                                p="lg",
                                radius="md",
                                children=[
                                    dmc.StepperStep(
                                        completedIcon=dmc.ThemeIcon(
                                            "2",
                                            radius="xl",
                                            size=40,
                                            variant="filled",
                                            color="green",
                                        ),
                                        label=dmc.Text("选择场景", weight=700),
                                        description=dmc.Text("智能推荐分析方法", size="sm", c="dimmed"),
                                        children=[
                                            html.Div(style={"padding": "10px"}),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                    dmc.GridCol(
                        span=4,
                        children=[
                            dmc.Paper(
                                shadow="md",
                                p="lg",
                                radius="md",
                                children=[
                                    dmc.StepperStep(
                                        completedIcon=dmc.ThemeIcon(
                                            "3",
                                            radius="xl",
                                            size=40,
                                            variant="filled",
                                            color="green",
                                        ),
                                        label=dmc.Text("获取结果", weight=700),
                                        description=dmc.Text("可视化图表+业务解读", size="sm", c="dimmed"),
                                        children=[
                                            html.Div(style={"padding": "10px"}),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
                mb="xl",
            ),
            # 支持的方法
            dmc.Title("支持的因果推断方法", order=2, mb="md"),
            dmc.Grid(
                children=[
                    dmc.GridCol(
                        span=4,
                        children=[
                            dmc.Card(
                                shadow="md",
                                padding="lg",
                                radius="md",
                                children=[
                                    dmc.Group(
                                        children=[
                                            dmc.ThemeIcon(
                                                "DID",
                                                size=50,
                                                radius="md",
                                                variant="gradient",
                                                gradient={"from": "green", "to": "teal"},
                                            ),
                                            dmc.Stack(
                                                children=[
                                                    dmc.Text("双差分法", weight=700),
                                                    dmc.Text("DID", size="sm", c="dimmed"),
                                                ],
                                                gap=0,
                                            ),
                                        ],
                                        mb="md",
                                    ),
                                    dmc.Text(
                                        "评估政策/活动效果，适合有处理组和控制组、有前后时间点的数据分析。",
                                        size="sm",
                                        c="dimmed",
                                    ),
                                ],
                            ),
                        ],
                    ),
                    dmc.GridCol(
                        span=4,
                        children=[
                            dmc.Card(
                                shadow="md",
                                padding="lg",
                                radius="md",
                                children=[
                                    dmc.Group(
                                        children=[
                                            dmc.ThemeIcon(
                                                "PSM",
                                                size=50,
                                                radius="md",
                                                variant="gradient",
                                                gradient={"from": "violet", "to": "purple"},
                                            ),
                                            dmc.Stack(
                                                children=[
                                                    dmc.Text("倾向得分匹配", weight=700),
                                                    dmc.Text("PSM", size="sm", c="dimmed"),
                                                ],
                                                gap=0,
                                            ),
                                        ],
                                        mb="md",
                                    ),
                                    dmc.Text(
                                        "通过倾向得分匹配构造对照组，适合存在选择偏差的场景。",
                                        size="sm",
                                        c="dimmed",
                                    ),
                                ],
                            ),
                        ],
                    ),
                    dmc.GridCol(
                        span=4,
                        children=[
                            dmc.Card(
                                shadow="md",
                                padding="lg",
                                radius="md",
                                children=[
                                    dmc.Group(
                                        children=[
                                            dmc.ThemeIcon(
                                                "RD",
                                                size=50,
                                                radius="md",
                                                variant="gradient",
                                                gradient={"from": "orange", "to": "yellow"},
                                            ),
                                            dmc.Stack(
                                                children=[
                                                    dmc.Text("断点回归", weight=700),
                                                    dmc.Text("RD", size="sm", c="dimmed"),
                                                ],
                                                gap=0,
                                            ),
                                        ],
                                        mb="md",
                                    ),
                                    dmc.Text(
                                        "分析在某个阈值附近的局部处理效应，适合有明确断点的场景。",
                                        size="sm",
                                        c="dimmed",
                                    ),
                                ],
                            ),
                        ],
                    ),
                    dmc.GridCol(
                        span=4,
                        children=[
                            dmc.Card(
                                shadow="md",
                                padding="lg",
                                radius="md",
                                children=[
                                    dmc.Group(
                                        children=[
                                            dmc.ThemeIcon(
                                                "IV",
                                                size=50,
                                                radius="md",
                                                variant="gradient",
                                                gradient={"from": "blue", "to": "cyan"},
                                            ),
                                            dmc.Stack(
                                                children=[
                                                    dmc.Text("工具变量法", weight=700),
                                                    dmc.Text("IV", size="sm", c="dimmed"),
                                                ],
                                                gap=0,
                                            ),
                                        ],
                                        mb="md",
                                    ),
                                    dmc.Text(
                                        "处理内生性问题，使用工具变量分离外生变异，适合面板数据分析。",
                                        size="sm",
                                        c="dimmed",
                                    ),
                                ],
                            ),
                        ],
                    ),
                    dmc.GridCol(
                        span=4,
                        children=[
                            dmc.Card(
                                shadow="md",
                                padding="lg",
                                radius="md",
                                children=[
                                    dmc.Group(
                                        children=[
                                            dmc.ThemeIcon(
                                                "CF",
                                                size=50,
                                                radius="md",
                                                variant="gradient",
                                                gradient={"from": "red", "to": "pink"},
                                            ),
                                            dmc.Stack(
                                                children=[
                                                    dmc.Text("因果森林", weight=700),
                                                    dmc.Text("Causal Forest", size="sm", c="dimmed"),
                                                ],
                                                gap=0,
                                            ),
                                        ],
                                        mb="md",
                                    ),
                                    dmc.Text(
                                        "估计异质性处理效应，识别哪些样本更受益于处理，适合精准营销场景。",
                                        size="sm",
                                        c="dimmed",
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
                mb="xl",
            ),
            # 使用统计（模拟）
            dmc.Paper(
                shadow="md",
                p="lg",
                radius="md",
                style={"backgroundColor": "#f1f5f9"},
                children=[
                    dmc.Group(
                        children=[
                            dmc.Stack(
                                children=[
                                    dmc.Text("10,000+", size="xl", weight=700, c="green"),
                                    dmc.Text("分析次数", size="sm", c="dimmed"),
                                ],
                                align="center",
                            ),
                            dmc.Stack(
                                children=[
                                    dmc.Text("5,000+", size="xl", weight=700, c="green"),
                                    dmc.Text("用户数量", size="sm", c="dimmed"),
                                ],
                                align="center",
                            ),
                            dmc.Stack(
                                children=[
                                    dmc.Text("99.9%", size="xl", weight=700, c="green"),
                                    dmc.Text("服务可用性", size="sm", c="dimmed"),
                                ],
                                align="center",
                            ),
                        ],
                        justify="center",
                    ),
                ],
            ),
        ],
    )
