# CSDN 技术教程自动生成与发布系统

基于 AI 的单片机/嵌入式技术教程自动生成工具，支持从主题规划、内容编写、AI 配图到 CSDN 一键发布的完整工作流。

## 功能特性

- **AI 大纲规划** — 输入技术主题，自动生成结构化教程大纲（5-8 章）
- **AI 内容生成** — 逐章生成专业 Markdown 教程，含原理讲解、完整代码、运行结果
- **AI 配图生成** — 自动识别需要配图的位置，调用即梦 API 生成技术架构图
- **CSDN 一键发布** — 通过 Playwright 浏览器自动化，自动上传图片、注入内容、保存草稿或发布
- **Web 管理界面** — 暗色/亮色主题、文章分栏筛选（STC51/STM32/ESP32/Linux）、在线生成、实时进度

## 系统要求

- Windows 10/11
- Python 3.11+（推荐通过 Miniconda 管理）
- Chromium 浏览器（Playwright 自动安装）

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
```

### 3. 配置环境变量

在项目根目录创建 `.env` 文件：

```env
# LLM API 配置（通过硅基流动调用 MiMo 模型）
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

1. 页面顶部「生成新文章」面板，输入技术主题
2. 设置配图数量（默认 3 张）
3. 点击「开始生成」或按回车
4. 实时查看 4 步进度：规划大纲 → 生成内容 → 生成配图 → 保存草稿
5. 生成完成后点击「查看文章」跳转到详情页

#### 管理文章

- **分栏筛选** — 点击顶部标签页按平台筛选（全部 / STC51 / STM32 / ESP32 / Linux）
- **文章详情** — 点击卡片进入，查看 Markdown 渲染内容、章节大纲、配图缩略图
- **发布到 CSDN** — 在详情页点击「保存草稿到 CSDN」或「发布到 CSDN」
- **查看源码** — 点击「查看 Markdown」弹窗显示原始 Markdown，支持一键复制
- **删除文章** — 在详情页点击「删除文章」确认后删除
- **主题切换** — 右上角太阳/月亮图标切换暗色/亮色主题

### 命令行

```bash
# 基本用法（默认保存草稿）
python main.py "技术主题"

# 限制配图数量
python main.py "STC51 定时器中断编程" --max-images 3

# 直接发布到 CSDN
python main.py "STM32 IIC 时序详解" --publish

# 组合使用
python main.py "ESP32 WiFi 配网" --max-images 5 --publish
```

#### 命令行参数

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `topic` | 技术主题（必填） | — |
| `--max-images N` | 最大配图数量（0=不限制） | 0 |
| `--publish` | 直接发布到 CSDN | 未设置（保存草稿） |
| `--draft` | 保存为草稿 | 默认开启 |

---

## 项目结构

```
CSDN/
├── main.py                      # CLI 入口 + pipeline 逻辑
├── config.py                    # 环境变量配置
├── .env                         # 密钥文件（不提交到 git）
├── requirements.txt             # Python 依赖
├── extract_cookie.py            # CSDN Cookie 自动提取脚本
├── regenerate.py                # 单章重新生成工具
├── verify.py                    # 内容验证工具
│
├── agents/                      # AI Agent 模块
│   ├── base.py                  # Agent 基类（封装 LLM 调用）
│   ├── planner_agent.py         # 大纲规划 Agent
│   ├── writer_agent.py          # 内容生成 Agent
│   ├── visual_agent.py          # 配图生成 Agent
│   └── publisher_agent.py       # CSDN 发布 Agent
│
├── services/                    # 外部服务封装
│   ├── llm_service.py           # LLM API 客户端（OpenAI 兼容）
│   ├── jimeng_service.py        # 即梦图片生成 API
│   ├── mermaid_service.py       # Mermaid 图表渲染
│   └── csdn_upload_service.py   # CSDN 图片上传
│
├── web/                         # Web 管理界面
│   ├── app.py                   # Flask 后端
│   ├── templates/
│   │   ├── index.html           # 首页（列表 + 生成面板）
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
        ├── outline.json         # 结构化大纲
        ├── tutorial.md          # 原始 Markdown
        ├── tutorial_final.md    # 含配图的最终版
        └── images/              # AI 生成的配图
```

---

## Pipeline 详细流程

```
用户输入技术主题
       │
       ▼
┌─────────────────┐
│ ① 规划大纲       │  PlannerAgent → MiMo LLM
│   生成 outline.json │  输出：标题、描述、标签、5-8 个章节
└────────┬────────┘
         ▼
┌─────────────────┐
│ ② 生成内容       │  WriterAgent → MiMo LLM（逐章调用）
│   生成 tutorial.md  │  每章含：原理、代码、注释、运行结果
└────────┬────────┘
         ▼
┌─────────────────┐
│ ③ 生成配图       │  VisualAgent → MiMo LLM（分析）+ 即梦 API（生成）
│   生成 tutorial_final.md + images/*.png │
└────────┬────────┘
         ▼
┌─────────────────┐
│ ④ 发布到 CSDN    │  PublisherAgent → Playwright 浏览器自动化
│   上传图片 → 注入内容 → 保存草稿/发布 │
└─────────────────┘
```

### 各步骤耗时参考

| 步骤 | 耗时 | 说明 |
|------|------|------|
| ① 规划大纲 | ~10 秒 | 单次 LLM 调用 |
| ② 生成内容 | ~5-6 分钟 | 逐章生成，每章约 50 秒 |
| ③ 生成配图 | ~1-3 分钟 | 取决于图片数量 |
| ④ 保存草稿 | ~30 秒 | 含图片上传和内容注入 |

---

## 支持的技术领域

系统提示词已针对以下领域优化：

| 平台 | 关键词 | 示例主题 |
|------|--------|----------|
| STC51 | stc51, 8051, c51 | 定时器中断、花式流水灯、外部中断、HC-05 蓝牙 |
| STM32 | stm32 | IIC 时序、PWM 电机控制、ADC 采样、YOLOv8 部署 |
| ESP32 | esp32 | Arduino IDE 入门、WiFi 配网、蓝牙 BLE |
| Linux | linux | 嵌入式 Linux 驱动开发、交叉编译 |

---

## 常见问题

### Q: 生成过程中断了怎么办？

已生成的文件保存在 `output/<文章名称>/` 目录中。可以通过 Web 界面查看已生成的部分内容，或删除后重新生成。

### Q: CSDN Cookie 过期了怎么办？

重新运行 `python extract_cookie.py`，在弹出的浏览器中登录 CSDN 即可自动更新 `.env` 中的 Cookie。

### Q: 如何只生成内容不发布？

CLI 默认只保存草稿，不发布。Web 界面生成后需要手动点击「保存草稿到 CSDN」。

### Q: 如何修改 LLM 模型？

编辑 `.env` 文件中的 `MIMO_MODEL` 字段，支持任何 OpenAI 兼容的 API 模型。

### Q: 图片生成失败怎么办？

检查 `.env` 中的 `JIMENG_AK` 和 `JIMENG_SK` 是否正确。图片生成失败时会显示占位文字，不影响文章内容。

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
