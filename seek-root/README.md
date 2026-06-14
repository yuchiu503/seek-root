# Seek Root - 让每个人都能找到数据背后的因果关系

让非技术人员也能轻松完成专业的因果推断分析。

## 功能特性

- **5种因果推断方法**: 双差分法(DID)、倾向得分匹配(PSM)、断点回归(RD)、工具变量法(IV)、因果森林
- **智能场景推荐**: 根据数据特征自动推荐最适合的分析方法
- **无代码操作**: 拖拽上传Excel/CSV，配置参数，即可完成分析
- **自动业务解读**: LLM将统计结果翻译成业务人员能理解的语言
- **深浅色主题**: 支持Mantine内置主题切换
- **私有部署**: 支持Docker一键部署，数据完全自主可控

## 安装

```bash
# 从PyPI安装
pip install seek-root

# 或从源码安装（开发模式）
git clone https://github.com/seek-root/seek-root.git
cd seek-root
pip install -e .
```

## 快速开始

### 启动服务

```bash
# 使用命令行启动
seek-root serve

# 或使用Python模块启动
python -m seek_root

# 指定端口
seek-root serve --port 8050 --host 0.0.0.0
```

然后访问 http://localhost:8050

### Docker部署

```bash
# 构建镜像
docker build -t seek-root .

# 运行容器
docker run -p 8050:8050 seek-root
```

## 配置

环境变量配置文件 `.env`：

```env
# 服务配置
PORT=8050
HOST=0.0.0.0
DEBUG=false

# 数据库配置
DATABASE_URL=sqlite:///./data/seek_root.db

# LLM配置（OpenAI兼容接口）
LLM_API_KEY=your-api-key
LLM_API_BASE=https://api.openai.com/v1
LLM_MODEL=gpt-3.5-turbo

# 数据目录
DATA_DIR=./data
```

## 使用流程

1. **上传数据**: 拖拽或点击上传Excel/CSV文件
2. **选择场景**: 从预设的场景模板中选择分析场景
3. **配置参数**: 选择结果变量、处理变量、协变量等
4. **查看结果**: 获取可视化图表和LLM生成的业务解读

## 支持的因果推断方法

| 方法 | 适用场景 | 输入要求 |
|------|---------|---------|
| DID 双差分 | 政策/活动效果评估 | 处理组+控制组，前后时间点 |
| PSM 倾向得分匹配 | 选择偏差下的因果效应 | 处理组+对照组，协变量 |
| RD 断点回归 | 阈值效应分析 | 运行变量、断点 |
| IV 工具变量 | 内生性问题处理 | 工具变量、处理变量、结果变量 |
| Causal Forest | 异质性处理效应 | 处理标识、协变量、结果变量 |

## 技术栈

- **前端**: Dash + dash-mantine-components + ECharts
- **数据处理**: Polars
- **因果推断**: DoWhy + EconML
- **数据库**: SQLite
- **LLM**: OpenAI兼容接口

## 许可证

MIT License

## 联系方式

- GitHub: https://github.com/seek-root/seek-root
- 邮箱: team@seekroot.ai
