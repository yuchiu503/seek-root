"""数据上传页面。

提供文件上传、数据预览和数据质量检查。
"""

import dash_mantine_components as dmc
from dash import html, dcc, callback, Output, Input, State
import base64
import io
import polars as pl


def render_data_page():
    """渲染数据上传页面内容。

    返回:
        html.Div: 页面内容
    """
    return html.Div(
        style={"maxWidth": "1000px", "margin": "0 auto", "padding": "20px"},
        children=[
            dmc.Title("上传数据", order=1, mb="md"),
            dmc.Text("支持CSV和Excel文件上传，建议小于50MB。", size="sm", c="dimmed", mb="md"),

            # 上传区域
            dmc.Paper(
                p="xl",
                shadow="md",
                radius="md",
                children=[
                    dcc.Upload(
                        id="data-upload",
                        children=[
                            html.Div(
                                style={
                                    "border": "2px dashed #10b981",
                                    "borderRadius": "8px",
                                    "padding": "40px 20px",
                                    "textAlign": "center",
                                    "cursor": "pointer",
                                    "backgroundColor": "#f0fdf4",
                                },
                                children=[
                                    dmc.Text("拖拽文件到此处，或点击选择文件", size="lg", c="#064e3b"),
                                    html.Br(),
                                    dmc.Text("支持 CSV、XLSX、XLS 格式", size="sm", c="dimmed"),
                                ],
                            )
                        ],
                        multiple=False,
                        accept=".csv,.xlsx,.xls",
                    ),
                ],
                mb="xl",
            ),

            # 上传状态显示
            html.Div(id="data-upload-status"),

            # 数据预览区域
            html.Div(id="data-preview-area", style={"marginTop": "20px"}),

            # 列选择区域
            html.Div(id="column-selector-area"),
        ],
    )


# 回调
@callback(
    Output("data-upload-status", "children"),
    Output("data-preview-area", "children"),
    Output("current-page", "data", allow_duplicate=True),
    Input("data-upload", "contents"),
    State("data-upload", "filename"),
    State("app-data-store", "data"),
    prevent_initial_call=True,
)
def handle_file_upload(contents, filename, store_data):
    """处理文件上传。

    参数:
        contents: 上传的文件内容（base64编码）
        filename: 文件名
        store_data: 当前存储的数据

    返回:
        tuple: (状态显示, 预览区域, 更新的存储)
    """
    if contents is None:
        return html.Div(), html.Div(), store_data

    try:
        # 解析文件内容
        content_type, content_string = contents.split(",")
        decoded = base64.b64decode(content_string)
        file_data = io.BytesIO(decoded)

        # 读取数据
        if filename.endswith(".csv"):
            df = pl.read_csv(file_data)
        elif filename.endswith(".xlsx") or filename.endswith(".xls"):
            df = pl.read_excel(file_data)
        else:
            return (
                dmc.Alert("不支持的文件格式！", color="red", title="错误"),
                html.Div(),
                store_data,
            )

        # 生成预览
        preview = dmc.Paper(
            p="lg",
            shadow="md",
            radius="md",
            children=[
                dmc.Title("数据预览", order=3, mb="md"),
                dmc.Group(
                    children=[
                        dmc.Stack(
                            children=[
                                dmc.Text("样本量", size="sm", c="dimmed"),
                                dmc.Text(str(len(df)), fw=700)),
                            ],
                            align="center",
                            gap=2,
                        ),
                        dmc.Stack(
                            children=[
                                dmc.Text("列数", size="sm", c="dimmed"),
                                dmc.Text(str(len(df.columns)), fw=700),
                            ],
                            align="center",
                            gap=2,
                        ),
                        dmc.Stack(
                            children=[
                                dmc.Text("数据类型", size="sm", c="dimmed"),
                                dmc.Text(str(df.schema).__name__, fw=700),
                            ],
                            align="center",
                            gap=2,
                        ),
                    ],
                    justify="space-around",
                ),
                html.Br(),
                html.Div(
                    style={"overflow": "auto", "maxHeight": "400px", "border": "1px solid #e5e7eb", "borderRadius": "8px"},
                    children=[
                        html.Table(
                            style={"width": "100%", "borderCollapse": "collapse"},
                            children=[
                                html.Thead(
                                    html.Tr(
                                        [html.Th(col, style={"border": "1px solid #e5e7eb", "background": "#f9fafb", "padding": "8px", "textAlign": "left"}) for col in df.columns]
                                    )
                                ),
                                html.Tbody(
                                    [
                                        html.Tr(
                                            [html.Td(str(row[i]) for i in range(len(row))],
                                            style={"border": "1px solid #e5e7eb", "padding": "8px"},
                                        ) for row in df.head(10).rows()
                                    ]
                                ),
                            ],
                        )
                    ],
                ),
                html.Br(),
                dmc.Group(
                    [
                        dmc.Button("继续分析", id="go-to-analysis", color="green", size="lg"),
                        dmc.Text("共 " + str(len(df)) + " 行数据，显示前10行", size="sm", c="dimmed"),
                    ],
                    justify="space-between",
                ),
            ],
        )

        status = dmc.Alert(
            "文件上传成功！", color="green", title="成功",
        )

        # 存储数据（转换为JSON格式）
        new_store = {
            "filename": filename,
            "columns": df.columns,
            "dtypes": {col: str(dtype) for col, dtype in df.schema.items()},
            "shape": (df.shape[0], df.shape[1]),
        }

        return status, preview, new_store

    except Exception as e:
        return (
            dmc.Alert(f"上传失败: {str(e)}", color="red", title="错误"),
            html.Div(),
            store_data,
        )


# 导航按钮
@callback(
    Output("current-page", "data"),
    Input("go-to-analysis", "n_clicks"),
    prevent_initial_call=True,
)
def go_to_analysis(n_clicks):
    """导航到分析页面。"""
    if n_clicks:
        return "analysis"
    return dash.no_update
