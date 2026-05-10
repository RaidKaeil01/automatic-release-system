# CSDN 技术教程自动生成与发布系统

基于 AI 的单片机/嵌入式技术教程自动生成工具，支持从主题规划、内容编写、AI 配图到 CSDN 一键发布的完整工作流。

## 功能特性

### 核心功能

- **AI 大纲规划** — 输入技术主题，自动生成结构化教程大纲（5-8 章）
- **大纲编辑** — 生成后可编辑大纲（Markdown 编辑器），确认后再生成内容
- **AI 内容生成** — 逐章生成专业 Markdown 教程，含原理讲解、完整代码、运行结果
- **目标字数控制** — 滑动条设定目标字数（1000-20000 字），影响生成文章长度
- **AI 配图生成** — 自动识别需要配图的位置，分别生成流程图和 AI 配图
- **CSDN 一键发布** — 通过 Playwright 浏览器自动化，自动上传图片、注入内容、保存草稿或发布

### 配图管理

- **流程图（Mermaid）** — 自动生成程序流程图、架构图、时序图等，渲染为 PNG
- **AI 配图（即梦）** — 调用即梦 API 生成实物照片、接线效果图等写实风格图片
- **独立数量控制** — 分别设置流程图和 AI 配图的生成数量（0=由内容自动决定）
- **分目录存储** — 图片按类型存储在 `images/diagrams/` 和 `images/ai/` 子目录

### Web 管理界面

- **暗色/亮色主题** — 右上角切换，支持系统偏好检测
- **文章分栏筛选** — 按平台筛选（全部 / STC51 / STM32 / ESP32 / Linux）
- **大纲预览与编辑** — 生成前预览大纲，支持 Markdown 编辑器修改后保存
- **实时进度展示** — 可折叠的进度区域，显示 4 步 Pipeline 状态
- **API 设置面板** — 集中管理所有 API 密钥，支持显示/隐藏切换
- **文章详情页** — Markdown 渲染、章节大纲、配图缩略图、源码查看

---

## 系统要求

- Windows 10/11
- Python 3.11+（推荐通过 Miniconda 管理）
- Chromium 浏览器（Playwright 自动安装）
- Node.js（Mermaid 图表渲染需要，可选）

---

## 快速开始

### 1. 安装 Python 环境

```bash
# 安装 Miniconda（如果尚未安装）
winget install Anaconda.Miniconda3

# 创建虚拟环境
conda create -n csdn_agent python=3.11 -y
conda activate csdn_agent
```

### 2. 安装依赖

```bash
cd CSDN
pip install -r requirements.txt
pip install flask

# 安装 Playwright 浏览器（用于 CSDN 发布）
playwright install chromium

# 安装 Mermaid CLI（可选，用于流程图渲染）
npm install -g @mermaid-js/mermaid-cli
```

### 3. 配置环境变量

复制 `.env.example` 为 `.env` 并填入真实密钥：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# LLM API 配置（小米 MiMo 模型）
MIMO_API_KEY=your_api_key_here
MIMO_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
MIMO_MODEL=mimo-v2.5-pro

# 即梦 API 配置（火山引擎，用于 AI 配图生成）
JIMENG_AK=your_access_key
JIMENG_SK=your_secret_key

# CSDN Cookie（用于发布文章）
CSDN_COOKIE=your_csdn_cookie_string
```

#### 获取各项配置

| 配置项 | 获取方式 |
|--------|----------|
| MIMO_API_KEY | 注册 [硅基流动](https://siliconflow.cn)，创建 API Key |
| JIMENG_AK/SK | 注册 [火山引擎](https://console.volcengine.com)，开通即梦 API |
| CSDN_COOKIE | 运行 `python extract_cookie.py`，在弹出的浏览器中登录 CSDN，自动提取 |

### 4. 启动

```bash
# 方式一：Web 管理界面（推荐）
python web/app.py
# 浏览器打开 http://localhost:5000

# 方式二：命令行生成
python main.py "STM32 PWM 电机控制"
```

---

## 使用方式

### Web 管理界面

启动后访问 http://localhost:5000

#### 生成新文章

1. 在页面顶部「生成新文章」面板输入技术主题
2. 拖动滑块设置目标字数（1000-20000 字）
3. 设置配图数量：
   -   流程图：Mermaid 渲染的架构图、流程图（0=自动）
   -   AI 配图：即梦 API 生成的写实图片（0=自动）
4. 点击「开始生成」
5. 系统先生成大纲预览，确认后继续生成内容
6. 实时查看 4 步进度：规划大纲 → 生成内容 → 生成配图 → 保存草稿
7. 生成完成后点击「查看文章」跳转到详情页

#### 大纲编辑

生成前可对大纲进行编辑：

1. 点击「开始生成」后，系统自动展示大纲预览
2. 点击「编辑大纲」切换到 Markdown 编辑器
3. 修改标题、章节、知识点等
4. 点击「保存编辑」更新大纲
5. 点击「确认生成」继续生成内容

大纲 Markdown 格式：

```markdown
# 教程标题

教程简介描述文字

标签：STM32, PWM, 电机控制

---

## 1. 章节标题

章节描述内容

- 知识点1
- 知识点2

代码语言：c

---

## 2. 第二章标题

...
```

#### API 设置

点击右上角齿轮图标打开设置面板：

- **MIMO LLM** — 配置 LLM API 密钥、地址、模型
- **即梦 AI 图片** — 配置图片生成 API 密钥
- **CSDN 发布** — 配置 CSDN 登录 Cookie

密码类字段默认遮蔽显示，点击   /  ️ 切换显示。

#### 管理文章

- **分栏筛选** — 点击顶部标签页按平台筛选
- **文章详情** — 点击卡片进入，查看渲染内容、章节大纲、配图
- **发布到 CSDN** — 在详情页点击「保存草稿到 CSDN」或「发布到 CSDN」
- **查看源码** — 点击「查看 Markdown」弹窗显示原始内容，支持一键复制
- **删除文章** — 在详情页点击「删除文章」确认后删除

### 命令行

```bash
# 基本用法（默认保存草稿）
python main.py "技术主题"

# 限制配图数量
python main.py "STC51 定时器中断编程" --max-images 3

# 设定目标字数
python main.py "STM32 IIC 时序详解" --word-count 8000

# 直接发布到 CSDN
python main.py "ESP32 WiFi 配网" --publish

# 组合使用
python main.py "STM32 PWM 电机控制" --word-count 10000 --max-images 5 --publish
```

#### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `topic` | 技术主题（必填） | — |
| `--max-images N` | 最大配图数量（0=不限制） | 0 |
| `--word-count N` | 目标文章字数 | 5000 |
| `--publish` | 直接发布到 CSDN | 未设置（保存草稿） |
| `--draft` | 保存为草稿 | 默认开启 |

---

## 项目结构

```
CSDN/
├── main.py                      # CLI 入口 + pipeline 逻辑
├── config.py                    # 环境变量配置
├── .env                         # 密钥文件（不提交到 git）
├── .env.example                 # 环境变量示例
├── requirements.txt             # Python 依赖
├── extract_cookie.py            # CSDN Cookie 自动提取脚本
├── regenerate.py                # 单章重新生成工具
├── verify.py                    # 内容验证工具
│
├── agents/                      # AI Agent 模块
│   ├── base.py                  # Agent 基类（封装 LLM 调用）
│   ├── planner_agent.py         # 大纲规划 Agent
│   ├── writer_agent.py          # 内容生成 Agent
│   ├── visual_agent.py          # 配图生成 Agent（流程图 + AI 图片）
│   ├── coder_agent.py           # 代码生成 Agent（Mermaid 代码等）
│   └── publisher_agent.py       # CSDN 发布 Agent
│
├── services/                    # 外部服务封装
│   ├── llm_service.py           # LLM API 客户端（OpenAI 兼容）
│   ├── jimeng_service.py        # 即梦图片生成 API（火山引擎）
│   ├── mermaid_service.py       # Mermaid 图表渲染（mmdc）
│   └── csdn_upload_service.py   # CSDN 图片上传
│
├── web/                         # Web 管理界面
│   ├── app.py                   # Flask 后端（API + 页面路由）
│   ├── templates/
│   │   ├── index.html           # 首页（列表 + 生成面板 + 设置）
│   │   └── detail.html          # 文章详情页
│   └── static/
│       └── style.css            # 样式（暗色/亮色双主题）
│
├── templates/                   # 大纲模板
│   └── tutorial_outline.json
│
├── tests/                       # 测试文件
│   └── test_pipeline.py
│
└── output/                      # 生成的文章（自动创建）
    └── <文章名称>/
        ├── outline.json         # 结构化大纲（JSON）
        ├── outline.md           # 可编辑大纲（Markdown）
        ├── tutorial.md          # 原始 Markdown
        ├── tutorial_final.md    # 含配图的最终版
        └── images/
            ├── diagrams/        # Mermaid 流程图
            │   ├── diagram_0.png
            │   ├── diagram_1.png
            │   └── mermaid_0.png
            └── ai/              # 即梦 AI 配图
                ├── img_0.png
                └── img_1.png
```

---

## Pipeline 详细流程

```
用户输入技术主题
       │
       ▼
┌─────────────────────┐
│ ① 规划大纲           │  PlannerAgent → MiMo LLM
│   生成 outline.json   │  输出：标题、描述、标签、5-8 个章节
│   生成 outline.md     │  可编辑的 Markdown 大纲
└────────┬────────────┘
         ▼
    [用户确认/编辑大纲]
         ▼
┌─────────────────────┐
│ ② 生成内容           │  WriterAgent → MiMo LLM（逐章调用）
│   生成 tutorial.md    │  每章含：原理、代码、注释、运行结果
│                       │  受目标字数控制
└────────┬────────────┘
         ▼
┌─────────────────────┐
│ ③ 生成配图           │  VisualAgent → MiMo LLM（分析）+ 渲染
│   流程图：Mermaid CLI  │  自动生成 Mermaid 代码 → PNG
│   AI 图：即梦 API     │  生成写实风格配图
│   生成 tutorial_final.md + images/
└────────┬────────────┘
         ▼
┌─────────────────────┐
│ ④ 发布到 CSDN        │  PublisherAgent → Playwright 浏览器自动化
│   上传图片 → 注入内容 → 保存草稿/发布
└─────────────────────┘
```

### 各步骤耗时参考

| 步骤 | 耗时 | 说明 |
|------|------|------|
| ① 规划大纲 | ~10 秒 | 单次 LLM 调用 |
| ② 生成内容 | ~5-6 分钟 | 逐章生成，每章约 50 秒 |
| ③ 生成配图 | ~1-3 分钟 | 取决于图片数量和类型 |
| ④ 保存草稿 | ~30 秒 | 含图片上传和内容注入 |

---

## 支持的技术领域

系统提示词已针对以下领域优化：

| 平台 | 关键词 | 示例主题 |
|------|--------|----------|
| STC51 | stc51, 8051, c51 | 定时器中断、花式流水灯、外部中断、HC-05 蓝牙 |
| STM32 | stm32 | IIC 时序、PWM 电机控制、ADC 采样、GPIO 输出 |
| ESP32 | esp32 | Arduino IDE 入门、WiFi 配网、蓝牙 BLE |
| Linux | linux | 嵌入式 Linux 驱动开发、交叉编译 |

---

## API 接口

Web 界面提供以下 REST API：

### 文章管理

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/articles` | 获取所有文章列表 |
| GET | `/api/article/<name>/outline` | 获取文章大纲（JSON） |
| GET | `/api/article/<name>/content` | 获取文章内容（Markdown） |
| DELETE | `/api/article/<name>` | 删除文章 |

### 大纲操作

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/outline` | 生成大纲（不继续后续步骤） |
| GET | `/api/article/<name>/outline-md` | 获取大纲 Markdown |
| POST | `/api/article/<name>/outline-md` | 保存编辑后的大纲 |

### 生成与发布

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | `/api/generate` | 启动完整 Pipeline（SSE 流式返回进度） |
| POST | `/api/article/<name>/publish` | 发布/保存草稿到 CSDN |

### 系统设置

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/settings` | 获取当前 API 配置 |
| POST | `/api/settings` | 保存 API 配置 |

### SSE 事件格式

`POST /api/generate` 返回 Server-Sent Events：

```
data: {"step": 1, "status": "running", "detail": "正在规划教程大纲..."}
data: {"step": 1, "status": "done", "detail": "标题: xxx，共 6 章"}
data: {"step": 2, "status": "running", "detail": "正在生成教程内容..."}
data: {"step": 2, "status": "done", "detail": "已生成 15000 字符的 Markdown 内容"}
data: {"step": 3, "status": "running", "detail": "正在分析配图需求..."}
data: {"step": 3, "status": "done", "detail": "已生成 5 张配图（3 张流程图 + 2 张 AI 图）"}
data: {"step": 4, "status": "running", "detail": "正在保存草稿到 CSDN..."}
data: {"step": 4, "status": "done", "detail": "草稿已保存"}
data: {"step": 0, "status": "done", "detail": "Pipeline 完成!"}
```

---

## 常见问题

### Q: 生成过程中断了怎么办？

已生成的文件保存在 `output/<文章名称>/` 目录中。可以通过 Web 界面查看已生成的部分内容，或删除后重新生成。

### Q: CSDN Cookie 过期了怎么办？

重新运行 `python extract_cookie.py`，在弹出的浏览器中登录 CSDN 即可自动更新 `.env` 中的 Cookie。也可以在 Web 界面的「API 设置」面板中手动更新。

### Q: 如何只生成内容不发布？

CLI 默认只保存草稿，不发布。Web 界面生成后需要手动点击「保存草稿到 CSDN」。

### Q: 如何修改 LLM 模型？

在 Web 界面的「API 设置」面板中修改，或编辑 `.env` 文件中的 `MIMO_MODEL` 字段。支持任何 OpenAI 兼容的 API 模型。

### Q: 图片生成失败怎么办？

- **流程图失败**：检查是否安装了 Mermaid CLI（`npm install -g @mermaid-js/mermaid-cli`）。失败时会降级为 Mermaid 代码块。
- **AI 图片失败**：检查 `.env` 中的 `JIMENG_AK` 和 `JIMENG_SK` 是否正确。失败时会显示占位文字。

### Q: 如何控制生成文章的字数？

Web 界面中拖动「目标字数」滑块（1000-20000 字）。CLI 使用 `--word-count` 参数。字数会影响 WriterAgent 的生成策略，每章按比例分配目标字数。

### Q: 流程图和 AI 配图有什么区别？

- **流程图（diagrams/）**：由 Mermaid 渲染，适合展示程序流程、架构关系、时序交互等逻辑结构
- **AI 配图（ai/）**：由即梦 API 生成，适合展示实物外观、接线效果、实验场景等写实内容

---

## 依赖说明

| 包 | 用途 |
|----|------|
| openai | LLM API 客户端（OpenAI 兼容接口） |
| httpx | HTTP 请求 |
| playwright | 浏览器自动化（CSDN 发布） |
| markdown | Markdown 转 HTML（Web 界面渲染） |
| python-dotenv | 环境变量加载 |
| pydantic | 数据验证 |
| rich | 终端美化输出 |
| flask | Web 管理界面后端 |

---

## 许可证

MIT License
