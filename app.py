import streamlit as st
import datetime
import os  # 新增: 用于读取环境变量
# 导入我们自定义的模块
import utils
import arxiv_api
import paper_reader
import ai_agent

# ==========================================
# 页面配置
# ==========================================
st.set_page_config(page_title="ArXiv 论文小助手", page_icon="📑", layout="wide")

# ==========================================
# 侧边栏设置
# ==========================================
st.sidebar.header("🔍 搜索设置")

# --- 新增: 预设关键词字典 (优化通用版) ---
search_presets = {
    "1. AI + Economics (AI与经济/金融 - 通用版)":
        '(Economic OR Economics OR Finance OR Financial OR Market OR "Behavioral Economics") AND (LLM OR "Large Language Model" OR RL OR "Reinforcement Learning" OR "Generative AI")',
    
    "2. Agents (LLM Agent / RL Agent / Multi-Agent)":
        '("Multi-Agent" OR "Multiagent" OR "Autonomous Agent" OR "LLM Agent" OR "Language Agent" OR "RL Agent" OR "Agentic") AND (LLM OR "Large Language Model" OR RL OR "Reinforcement Learning")',
    
    "3. World Models (世界模型 & MBRL)":
        '"World Model" OR "World Models" OR "Generative World Model" OR "Model-Based RL" OR MBRL OR "Predictive Model"',
    
    "4. 自定义 (空白)": ""
}

# 预设选择器
selected_preset_key = st.sidebar.selectbox("快速选择预设", options=list(search_presets.keys()), index=0)
default_keyword = search_presets[selected_preset_key]

# 1. 关键词输入框 (value 会根据预设自动变化)
keywords = st.sidebar.text_input("关键词 (支持 AND, OR)", value=default_keyword)

# 2. 领域选择
category_bundle = st.sidebar.selectbox("选择搜索范围", options=list(utils.CATEGORY_QUERIES.keys()), index=0)

# 3. 时间与数量
days_back = st.sidebar.slider("搜索过去多少天?", min_value=1, max_value=365, value=7)
max_results = st.sidebar.number_input("最大结果数量", min_value=5, max_value=100, value=20)

st.sidebar.divider()
st.sidebar.header("🤖 AI 设置")

# --- 自动从环境变量读取 API Key ---
env_api_key = os.getenv("OPENAI_API_KEY", "")

api_key = st.sidebar.text_input(
    "API Key",
    value=env_api_key,
    type="password",
    help="如果在终端设置了 export OPENAI_API_KEY='...', 此处会自动填充"
)

base_url = st.sidebar.text_input("Base URL", value="https://api.openai.com/v1", help="国内请填转发地址")
model_name = st.sidebar.text_input("模型名称", value="gpt-4o-mini", help="例如 gpt-4o-mini 或 deepseek-chat")

# ==========================================
# 主逻辑
# ==========================================
st.title("📑 ArXiv Paper Daily Tracker")
st.caption(f"当前模式: {category_bundle} | 窗口: {days_back}天")

# 初始化 Session State
if "papers" not in st.session_state:
    st.session_state.papers = []
if "summaries" not in st.session_state:
    st.session_state.summaries = {}

# --- 搜索按钮 ---
if st.button("开始抓取", type="primary"):
    if not keywords:
        st.warning("请输入关键词！")
    else:
        with st.spinner('正在连接 ArXiv 数据库...'):
            # 1. 构建查询
            query_string = utils.build_query(keywords, category_bundle)
            
            # 2. 执行搜索
            papers = arxiv_api.fetch_arxiv_papers(query_string, days_back, max_results)
            
            if not papers:
                st.info("未找到符合条件的论文，请尝试放宽时间或更换关键词。")
            else:
                # 3. 结果存入 Session
                st.session_state.papers = papers
                st.session_state.summaries = {}  # 清空旧总结
                st.success(f"成功找到 {len(papers)} 篇论文！")

# --- 结果展示 ---
if st.session_state.papers:
    st.divider()
    
    for i, paper in enumerate(st.session_state.papers):
        with st.container():
            col1, col2 = st.columns([0.82, 0.18])
            
            with col1:
                st.subheader(f"{i + 1}. {paper.title}")
                authors = [a.name for a in paper.authors]
                author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
                
                html_link = f"https://arxiv.org/html/{paper.entry_id.split('/')[-1]}"
                st.markdown(f"**✍️ 作者:** {author_str} | **📅 发布:** {paper.published.strftime('%Y-%m-%d')}")
                st.markdown(f"[HTML 阅读]({html_link}) | [PDF 下载]({paper.pdf_url}) | [ArXiv Page]({paper.entry_id})")
            
            with col2:
                btn_key = f"ai_btn_{paper.entry_id}"
                if st.button("🤖 AI 全文解读", key=btn_key):
                    status = st.empty()
                    status.info("⏳ 正在获取正文 (HTML优先)...")
                    
                    # 1. 获取正文
                    content, src_type = paper_reader.get_paper_content(paper.entry_id, paper.pdf_url)
                    
                    if content.startswith("Error"):
                        status.error("❌ 获取内容失败，请检查网络")
                    else:
                        status.info(f"✅ 获取成功 ({src_type})! AI 正在阅读...")
                        # 2. AI 总结
                        summary = ai_agent.get_ai_summary(content, paper.title, api_key, base_url, model_name)
                        
                        # 3. 存结果
                        st.session_state.summaries[paper.entry_id] = summary
                        status.empty()
            
            if paper.entry_id in st.session_state.summaries:
                st.markdown("#### 📝 AI 深度分析报告")
                st.info(st.session_state.summaries[paper.entry_id])
            
            with st.expander("📖 查看原始摘要 (Abstract)"):
                st.write(paper.summary)
            
            st.divider()
    
    # --- 导出功能 ---
    st.header("📤 导出结果")
    if st.button("生成 Markdown 报告"):
        export_text = utils.generate_export_text(st.session_state.papers, keywords)
        st.download_button(
            label="下载文件",
            data=export_text,
            file_name=f"arxiv_report_{datetime.datetime.now().strftime('%Y%m%d')}.md",
            mime="text/markdown"
        )