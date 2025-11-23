
# 📑 ArXiv Paper Daily Tracker

> **Your Personal AI Research Assistant.** \> 一个基于 Python Streamlit 的高效 ArXiv 论文追踪工具，专为解决“信息过载”和“搜索不准”而生。

  <img width="1909" height="1603" alt="image" src="https://github.com/user-attachments/assets/e197e400-e8f6-4936-b93d-4e73118cfbd3" />
ArXiv Paper Daily Tracker 网页示意图

## 📖 简介 (Introduction)

你是否觉得 ArXiv 上的论文太多，或者官方搜索经常搜出“驴唇不对马嘴”的结果？
这个工具旨在帮助研究人员（特别是 AI、CS、Econ 交叉领域）高效筛选每日新论文。

**核心差异化优势：**

  * **智能“宽进严出”策略**：解决了 ArXiv API “按时间排序相关性差，按相关性排序时间太旧”的痛点。
  * **跨学科组合包**：一键搜索 AI + 金融、AI + 科学等交叉领域，防止漏掉投递到非 CS 板块的优质论文。
  * **笔记友好**：一键导出 Markdown 格式，完美适配 Obsidian / Notion。

## ✨ 功能特性 (Features)

  * **🔍 高级布尔搜索**：支持 `AND`, `OR`, `NOT` 及括号组合逻辑。
  * **🎯 精准模式**：提供“仅搜索标题”开关，拒绝摘要里的关键词“蹭热度”。
  * **📦 智能领域组合**：
      * `AI & CS`: 涵盖 CV, NLP, ML, RO 等主流计算机子领域。
      * `AI + Fin/Econ`: 专为 AI for Science/Economics 设计，包含 `q-fin`, `econ` 等板块。
  * **📅 智能时效过滤**：在保证相关性的前提下（Relevance Sort），本地二次过滤出“过去 N 天”的论文。
  * **📝 一键导出**：生成包含标题、作者、链接、摘要的格式化报告。

## 🛠️ 快速开始 (Quick Start)

### 1\. 环境准备

确保你的电脑上安装了 Python (3.8+)。

```bash
# 克隆项目 (如果你有 git)
git clone https://github.com/your-username/arxiv-daily-tracker.git
cd arxiv-daily-tracker

# 或者直接下载代码文件夹
```

### 2\. 安装依赖

建议使用虚拟环境，或者直接安装：

```bash
pip install streamlit arxiv pandas tenacity
```

### 3\. 运行应用

在终端中运行以下命令：

```bash
streamlit run main.py
```

浏览器会自动打开 `http://localhost:8501`。

## 💡 搜索技巧 (Search Tips)

为了获得最精准的结果，建议参考以下输入格式：

| 你的需求 | 输入示例 |
| :--- | :--- |
| **精确短语匹配** | `"Chain of Thought"` (加双引号) |
| **逻辑组合** | `(LLM OR Transformer) AND (Reasoning OR Planning)` |
| **AI + 经济学 (推荐)** | `(Economic OR Finance) AND (LLM OR RL)` <br> *注：请选择 "AI + Fin/Econ" 领域分类* |
| **仅看标题** | 在侧边栏勾选 ✅ **"只搜索标题 (更精准)"** |

## ⚙️ 核心逻辑说明 (How It Works)

本工具采用了 **Relevance-First, Date-Filter-Second** 的策略：

1.  **Fetch (抓取)**: 向 ArXiv API 请求比用户所需多 `5倍` 的数据，强制按 **相关性 (Relevance)** 排序。
2.  **Filter (清洗)**: 在本地 Python 内存中，剔除发布日期早于设定时间范围（如 7 天前）的论文。
3.  **Display (展示)**: 最终展示给你的，是 **既高度相关、又是最近发布** 的高质量论文。

## 📂 项目结构

```text
.
├── main.py           # 主程序代码 (Streamlit 界面与逻辑)
├── README.md        # 项目文档
```

## 📝 TODO / 未来计划

  - [ ] 集成 LLM (OpenAI/Claude) API，自动生成中文一句话总结。
  - [ ] 增加 Semantic Scholar 引用数显示。
  - [ ] 支持定时的邮件推送功能。

## 🤝 贡献 (Contributing)

欢迎提交 Issue 或 Pull Request 来改进这个工具！

