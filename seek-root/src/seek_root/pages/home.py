"""首页模块。

提供Seek Root应用的首页/引导页面内容渲染。
"""

import dash_mantine_components as dmc
from dash import html, dcc


def render_home_page():
    """渲染首页内容。

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
                                color="green",
                            ),
                            dmc.Button(
                                "查看示例",
                                size="lg",
                                variant="outline",
                                style={"color": "white", "borderColor": "rgba(255,255,255,0.5)"},
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
                                    dmc.Group(
                                        children=[
                                            dmc.Badge("1", size="xl", radius="lg"),
                                            dmc.Text("上传数据", fw=700),
                                        ],
                                        mb="md",
                                    ),
                                    dmc.Text("拖拽Excel/CSV文件", size="sm", c="dimmed"),
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
                                    dmc.Group(
                                        children=[
                                            dmc.Badge("2", size="xl", radius="lg"),
                                            dmc.Text("选择场景", fw=700),
                                        ],
                                        mb="md",
                                    ),
                                    dmc.Text("智能推荐分析方法", size="sm", c="dimmed"),
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
                                    dmc.Group(
                                        children=[
                                            dmc.Badge("3", size="xl", radius="lg"),
                                            dmc.Text("获取结果", fw=700),
                                        ],
                                        mb="md",
                                    ),
                                    dmc.Text("可视化图表+业务解读", size="sm", c="dimmed"),
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
                                    dmc.Text("DID", fw=700),
                                    dmc.Text("双差分法", size="sm", c="dimmed", mt="xs"),
                                    dmc.Text("评估政策/活动效果。", size="sm", c="dimmed", mt="md"),
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
                                    dmc.Text("PSM", fw=700),
                                    dmc.Text("倾向得分匹配", size="sm", c="dimmed", mt="xs"),
                                    dmc.Text("构造对照组消除选择偏差。", size="sm", c="dimmed", mt="md"),
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
                                    dmc.Text("RD", fw=700),
                                    dmc.Text("断点回归", size="sm", c="dimmed", mt="xs"),
                                    dmc.Text("分析阈值附近的局部处理效应。", size="sm", c="dimmed", mt="md"),
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
                                    dmc.Text("IV", fw=700),
                                    dmc.Text("工具变量法", size="sm", c="dimmed", mt="xs"),
                                    dmc.Text("处理内生性问题。", size="sm", c="dimmed", mt="md"),
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
                                    dmc.Text("CF", fw=700),
                                    dmc.Text("因果森林", size="sm", c="dimmed", mt="xs"),
                                    dmc.Text("识别异质性效应，精准定位。", size="sm", c="dimmed", mt="md"),
                                ],
                            ),
                        ],
                    ),
                ],
                mb="xl",
            ),
            # 使用统计
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
                                    dmc.Text("10,000+", size="xl", fw=700, c="green"),
                                    dmc.Text("分析次数", size="sm", c="dimmed"),
                                ],
                                align="center",
                            ),
                            dmc.Stack(
                                children=[
                                    dmc.Text("5,000+", size="xl", fw=700, c="green"),
                                    dmc.Text("用户数量", size="sm", c="dimmed"),
                                ],
                                align="center",
                            ),
                            dmc.Stack(
                                children=[
                                    dmc.Text("99.9%", size="xl", fw=700, c="green"),
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
