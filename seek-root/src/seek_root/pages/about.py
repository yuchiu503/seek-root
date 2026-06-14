"""关于页面模块。

展示产品介绍和使用文档。
"""

import dash
import dash_mantine_components as dmc
from dash import html, register_page

dash.register_page(__name__, path="/about", title="关于")


def layout():
    """关于页面布局。

    返回:
        html.Div: 关于页面组件
    """
    return html.Div(
        style={"maxWidth": "1000px", "margin": "0 auto", "padding": "20px"},
        children=[
            # 页面标题
            dmc.Title("关于 Seek Root", order=1, mb="xl"),
            # 产品介绍
            dmc.Paper(
                shadow="md",
                p="xl",
                radius="md",
                mb="xl",
                children=[
                    dmc.Title("产品介绍", order=2, mb="md"),
                    dmc.Text(
                        "Seek Root（问源）是一款面向业务人员的因果推断Web应用。"
                        "我们相信，每个人都应该能够从数据中发现因果关系，而不需要编写代码或深入了解统计学知识。",
                        mb="sm",
                    ),
                    dmc.Text(
                        "通过简单的拖拽操作，您可以：",
                        weight=500,
                        mb="sm",
                    ),
                    dmc.List(
                        spacing="xs",
                        size="sm",
                        children=[
                            dmc.ListItem("上传Excel/CSV数据，无需编程"),
                            dmc.ListItem("选择预设的分析场景，获得智能推荐"),
                            dmc.ListItem("一键执行5种专业的因果推断方法"),
                            dmc.ListItem("获取可视化的分析结果和业务解读"),
                        ],
                    ),
                ],
            ),
            # 技术栈
            dmc.Paper(
                shadow="md",
                p="xl",
                radius="md",
                mb="xl",
                children=[
                    dmc.Title("技术特性", order=2, mb="md"),
                    dmc.Grid(
                        children=[
                            dmc.GridCol(
                                span=4,
                                children=[
                                    dmc.Card(
                                        shadow="sm",
                                        padding="md",
                                        radius="md",
                                        children=[
                                            dmc.Text("🔧", size="xl"),
                                            dmc.Text("Polars", weight=700, mt="sm"),
                                            dmc.Text("高性能数据处理", size="sm", c="dimmed"),
                                        ],
                                    ),
                                ],
                            ),
                            dmc.GridCol(
                                span=4,
                                children=[
                                    dmc.Card(
                                        shadow="sm",
                                        padding="md",
                                        radius="md",
                                        children=[
                                            dmc.Text("📈", size="xl"),
                                            dmc.Text("DoWhy + EconML", weight=700, mt="sm"),
                                            dmc.Text("微软因果推断引擎", size="sm", c="dimmed"),
                                        ],
                                    ),
                                ],
                            ),
                            dmc.GridCol(
                                span=4,
                                children=[
                                    dmc.Card(
                                        shadow="sm",
                                        padding="md",
                                        radius="md",
                                        children=[
                                            dmc.Text("🤖", size="xl"),
                                            dmc.Text("LLM 解读", weight=700, mt="sm"),
                                            dmc.Text("AI 业务解读", size="sm", c="dimmed"),
                                        ],
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            # 使用方法
            dmc.Paper(
                shadow="md",
                p="xl",
                radius="md",
                mb="xl",
                children=[
                    dmc.Title("使用方法", order=2, mb="md"),
                    dmc.Accordion(
                        children=[
                            dmc.AccordionItem(
                                label="如何上传数据？",
                                children=[
                                    dmc.Text(
                                        "在「上传数据」页面，点击上传区域，选择您的Excel或CSV文件即可。"
                                        "系统会自动识别列类型并显示数据预览。"
                                    ),
                                ],
                            ),
                            dmc.AccordionItem(
                                label="如何选择分析方法？",
                                children=[
                                    dmc.Text(
                                        "在「分析」页面，选择适合您数据和分析目标的场景模板。"
                                        "系统会根据场景智能推荐最合适的因果推断方法。"
                                    ),
                                ],
                            ),
                            dmc.AccordionItem(
                                label="DID和PSM有什么区别？",
                                children=[
                                    dmc.Text(
                                        "DID（双差分法）适用于有处理组和控制组、且有前后时间点对比的数据。"
                                        "PSM（倾向得分匹配）通过为每个处理组样本匹配相似的对照样本来估计因果效应，"
                                        "适用于没有明确时间序列的场景。"
                                    ),
                                ],
                            ),
                            dmc.AccordionItem(
                                label="结果如何解读？",
                                children=[
                                    dmc.Text(
                                        "分析完成后，系统会生成可视化图表展示因果效应的大小和统计显著性，"
                                        "并通过LLM生成通俗易懂的业务解读，帮助您理解分析结果并做出决策。"
                                    ),
                                ],
                            ),
                        ],
                    ),
                ],
            ),
            # 版本信息
            dmc.Paper(
                shadow="sm",
                p="md",
                radius="md",
                style={"textAlign": "center", "backgroundColor": "#f8fafc"},
                children=[
                    dmc.Text("Seek Root v0.1.0", size="sm", c="dimmed"),
                    dmc.Text("MIT License", size="xs", c="dimmed", mt="xs"),
                ],
            ),
        ],
    )
