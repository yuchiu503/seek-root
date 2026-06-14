"""数据上传页面模块。

提供数据文件上传和数据预览功能。
"""

import dash
import dash_mantine_components as dmc
from dash import html, dcc, callback, Output, Input, State, register_page
import polars as pl
import base64
import io

from seek_root.data.loader import DataLoader
from seek_root.data.validator import DataValidator

dash.register_page(__name__, path="/data", title="上传数据")


def parse_contents(contents: str, filename: str) -> tuple:
    """解析上传的文件内容。

    参数:
        contents: 文件内容（base64编码）
        filename: 文件名

    返回:
        tuple: (数据DataFrame, 列信息, 文件名)
    """
    content_type, content_string = contents.split(",")
    decoded = base64.b64decode(content_string)

    loader = DataLoader(content=decoded, file_path=filename)
    df = loader.load()

    return df, loader.get_column_info(), filename


def layout():
    """数据上传页面布局。

    返回:
        html.Div: 数据上传页面组件
    """
    return html.Div(
        style={"maxWidth": "1000px", "margin": "0 auto", "padding": "20px"},
        children=[
            # 页面标题
            dmc.Title("上传数据", order=1, mb="md"),
            dmc.Text(
                "拖拽或点击上传您的数据文件，支持 Excel (.xlsx, .xls) 和 CSV 格式。",
                c="dimmed",
                mb="xl",
            ),
            # 上传区域
            dcc.Upload(
                id="upload-data",
                children=[
                    dmc.Paper(
                        shadow="md",
                        p="xl",
                        radius="md",
                        style={
                            "border": "2px dashed #10b981",
                            "textAlign": "center",
                            "cursor": "pointer",
                            "backgroundColor": "#f0fdf4",
                        },
                        children=[
                            dmc.ThemeIcon(
                                "📁",
                                size=60,
                                variant="transparent",
                            ),
                            dmc.Text(
                                "将文件拖拽到此处，或点击选择文件",
                                size="lg",
                                weight=500,
                                mt="md",
                            ),
                            dmc.Text(
                                "支持 .xlsx, .xls, .csv 格式",
                                size="sm",
                                c="dimmed",
                                mt="sm",
                            ),
                        ],
                    ),
                ],
                accept=".csv,.xlsx,.xls",
                max_size=10 * 1024 * 1024,  # 10MB
            ),
            # 数据预览区域
            html.Div(id="output-data-upload", style={"marginTop": "30px"}),
            # 数据信息存储
            dcc.Store(id="data-info-store"),
        ],
    )


@callback(
    Output("output-data-upload", "children"),
    Output("data-info-store", "data"),
    Input("upload-data", "contents"),
    State("upload-data", "filename"),
    State("upload-data", "last_modified"),
)
def update_output(contents, filename, last_modified):
    """处理文件上传并显示预览。

    参数:
        contents: 文件内容
        filename: 文件名
        last_modified: 最后修改时间

    返回:
        tuple: (预览组件, 数据信息)
    """
    if contents is None:
        return html.Div(), None

    try:
        # 解析文件
        df, column_info, fname = parse_contents(contents, filename)

        # 数据预览表格
        preview_df = df.head(10)

        # 构建预览组件
        children = [
            dmc.Title(f"数据预览 - {fname}", order=3, mt="xl", mb="md"),
            dmc.Alert(
                f"成功加载 {df.height:,} 行 × {len(df.columns)} 列 数据",
                color="green",
                title="加载成功",
                mb="md",
            ),
            # 数据预览表格
            dmc.Paper(
                shadow="sm",
                p="md",
                radius="md",
                style={"overflowX": "auto"},
                children=[
                    dmc.Table(
                        children=[
                            # 表头
                            html.Thead(
                                html.Tr(
                                    [
                                        html.Th(col) for col in preview_df.columns
                                    ]
                                )
                            ),
                            # 表体
                            html.Tbody(
                                [
                                    html.Tr(
                                        [
                                            html.Td(str(val)[:50])  # 限制显示长度
                                            for val in row
                                        ]
                                    )
                                    for row in preview_df.rows()
                                ]
                            ),
                        ],
                        striped=True,
                        highlightOnHover=True,
                    ),
                ],
            ),
            # 列信息
            dmc.Title("数据列信息", order=3, mt="xl", mb="md"),
            dmc.SimpleGrid(
                cols=3,
                children=[
                    dmc.Card(
                        shadow="sm",
                        padding="md",
                        radius="md",
                        children=[
                            dmc.Text(col_info["name"], weight=700),
                            dmc.Text(f"类型: {col_info['dtype']}", size="sm", c="dimmed"),
                            dmc.Text(f"缺失值: {col_info['null_count']}", size="sm", c="dimmed"),
                            dmc.Text(f"唯一值: {col_info['unique_count']}", size="sm", c="dimmed"),
                        ],
                    )
                    for col_info in column_info
                ],
            ),
            # 下一步按钮
            dmc.Group(
                children=[
                    dmc.Button(
                        "进入分析",
                        size="lg",
                        variant="filled",
                        color="green",
                        leftSection="🔬",
                        href="/analysis",
                    ),
                ],
                mt="xl",
                justify="center",
            ),
        ]

        # 数据信息
        data_info = {
            "filename": fname,
            "row_count": df.height,
            "column_count": len(df.columns),
            "columns": df.columns,
            "column_info": column_info,
        }

        return children, data_info

    except Exception as e:
        return dmc.Alert(
            f"加载数据失败: {str(e)}",
            color="red",
            title="错误",
        ), None
