import streamlit as st
import datetime
import os
# 导入自定义模块
import utils
import arxiv_api
import paper_reader
import ai_agent
import storage  # <--- 保持导入存储模块

# ==========================================
# 页面配置
# ==========================================
st.set_page_config(page_title="ArXiv 论文小助手", page_icon="📑", layout="wide")

# ==========================================
# 侧边栏：全局设置 & 模式切换
# ==========================================
# 模式切换放在最上面，方便切换
mode = st.sidebar.radio("功能模式", ["🔍 论文搜索", "⭐ 我的收藏"])
st.sidebar.divider()

# 初始化 Session State
if "papers" not in st.session_state:
    st.session_state.papers = []
if "summaries" not in st.session_state:
    st.session_state.summaries = {}


# ==========================================
# 辅助函数：统一渲染卡片 (保持 UI 风格一致)
# ==========================================
def render_paper_card(paper, is_favorite_mode=False, api_key=None, base_url=None, model_name=None):
    """
    渲染单个论文卡片，复用于搜索页和收藏页。
    """
    # 统一数据格式
    if isinstance(paper, dict):
        # 收藏页的数据是字典
        title = paper['title']
        entry_id = paper['entry_id']
        pdf_url = paper['pdf_url']
        published_date = paper['published']
        authors_list = paper['authors']
        summary_text = paper['summary']
    else:
        # 搜索页的数据是 arxiv.Result 对象
        title = paper.title
        entry_id = paper.entry_id
        pdf_url = paper.pdf_url
        published_date = paper.published.strftime('%Y-%m-%d')
        authors_list = [a.name for a in paper.authors]
        summary_text = paper.summary
    
    # --- UI 渲染 ---
    with st.container():
        col1, col2 = st.columns([0.85, 0.15])
        
        with col1:
            st.subheader(title)
            author_str = ", ".join(authors_list[:3]) + (" et al." if len(authors_list) > 3 else "")
            
            # 链接
            html_link = f"https://arxiv.org/html/{entry_id.split('/')[-1]}"
            st.markdown(f"**✍️ 作者:** {author_str} | **📅 发布:** {published_date}")
            st.markdown(f"[HTML 阅读]({html_link}) | [PDF 下载]({pdf_url}) | [ArXiv 页面]({entry_id})")
        
        with col2:
            # 1. AI 解读按钮
            ai_btn_key = f"ai_{entry_id}_{'fav' if is_favorite_mode else 'search'}"
            if st.button("🤖 AI 解读", key=ai_btn_key):
                status = st.empty()
                status.info("⏳ 获取正文...")
                content, src = paper_reader.get_paper_content(entry_id, pdf_url)
                if content.startswith("Error"):
                    status.error("❌ 获取失败")
                else:
                    status.info(f"✅ 正在阅读 ({src})...")
                    summary = ai_agent.get_ai_summary(content, title, api_key, base_url, model_name)
                    st.session_state.summaries[entry_id] = summary
                    status.empty()
            
            # 2. 收藏/移除按钮
            if is_favorite_mode:
                if st.button("❌ 移除", key=f"del_{entry_id}"):
                    storage.remove_favorite(entry_id)
            else:
                if st.button("❤️ 收藏", key=f"fav_{entry_id}"):
                    storage.save_favorite(paper)
        
        # 展示 AI 结果
        if entry_id in st.session_state.summaries:
            st.markdown("#### 📝 AI 深度分析")
            st.info(st.session_state.summaries[entry_id])
        
        with st.expander("📖 摘要 (Abstract)"):
            st.write(summary_text)
        
        st.divider()


# ==========================================
# 页面 1: 🔍 论文搜索 (还原你的经典界面)
# ==========================================
if mode == "🔍 论文搜索":
    # --- 侧边栏：搜索设置 (仅在搜索模式显示) ---
    st.sidebar.header("🔍 搜索设置")
    
    # 预设与关键词
    search_presets = {
        "1. AI + Economics":
            '(Economic OR Economics OR Finance OR Financial OR Market OR "Behavioral Economics") AND (LLM OR "Large Language Model" OR RL OR "Reinforcement Learning")',
        "2. Agents (Multi-Agent / LLM Agent)":
            '("Multi-Agent" OR "Multiagent" OR "Autonomous Agent" OR "LLM Agent" OR "Language Agent" OR "RL Agent" OR "Agentic") AND (LLM OR "Large Language Model" OR RL OR "Reinforcement Learning")',
        "3. World Models":
            '"World Model" OR "World Models" OR "Generative World Model" OR "Model-Based RL" OR MBRL OR "Predictive Model"',
        "4. Evolution":
        'agent AND LLM AND (evolution OR evole)',
        "5. 自定义 (空白)": ""
    }
    selected_preset_key = st.sidebar.selectbox("快速选择预设", options=list(search_presets.keys()), index=0)
    default_keyword = search_presets[selected_preset_key]
    
    keywords = st.sidebar.text_input("关键词", value=default_keyword)
    category_bundle = st.sidebar.selectbox("选择搜索范围", options=list(utils.CATEGORY_QUERIES.keys()), index=0)
    days_back = st.sidebar.slider("搜索过去多少天?", min_value=1, max_value=365, value=7)
    max_results = st.sidebar.number_input("最大结果数量", min_value=5, max_value=100, value=20)
    
    st.sidebar.divider()
    st.sidebar.header("🤖 AI 设置")
    env_api_key = os.getenv("OPENAI_API_KEY", "")
    api_key = st.sidebar.text_input("API Key", value=env_api_key, type="password")
    base_url = st.sidebar.text_input("Base URL", value="https://api.openai.com/v1")
    model_name = st.sidebar.text_input("模型名称", value="gpt-4o-mini")
    
    # --- 主界面 UI (还原经典风格) ---
    st.title("📑 ArXiv Paper Daily Tracker")
    # 还原你想要的小字展示
    st.caption(f"当前模式: {category_bundle} | 窗口: {days_back}天")
    
    # 还原“开始抓取”按钮文案
    if st.button("开始抓取", type="primary"):
        if not keywords:
            st.warning("请输入关键词！")
        else:
            with st.spinner('正在连接 ArXiv 数据库...'):
                query_string = utils.build_query(keywords, category_bundle)
                papers = arxiv_api.fetch_arxiv_papers(query_string, days_back, max_results)
                
                if not papers:
                    st.info("未找到符合条件的论文，请尝试放宽时间或更换关键词。")
                else:
                    st.session_state.papers = papers
                    st.session_state.summaries = {}
                    st.success(f"成功找到 {len(papers)} 篇论文！")
    
    # 展示结果
    if st.session_state.papers:
        st.divider()
        for paper in st.session_state.papers:
            render_paper_card(paper, is_favorite_mode=False, api_key=api_key, base_url=base_url, model_name=model_name)
        
        # 导出功能
        st.header("📤 导出结果")
        if st.button("生成 Markdown 报告"):
            export_text = utils.generate_export_text(st.session_state.papers, keywords)
            st.download_button("下载文件", export_text, f"arxiv_report_{datetime.date.today()}.md")

# ==========================================
# 页面 2: ⭐ 我的收藏 (新功能)
# ==========================================
elif mode == "⭐ 我的收藏":
    st.title("⭐ 我的论文收藏夹")
    
    # 收藏页也需要 AI 设置，以便在这里直接解读
    st.sidebar.header("🤖 AI 设置")
    env_api_key = os.getenv("OPENAI_API_KEY", "")
    api_key = st.sidebar.text_input("API Key", value=env_api_key, type="password")
    base_url = st.sidebar.text_input("Base URL", value="https://api.openai.com/v1")
    model_name = st.sidebar.text_input("模型名称", value="gpt-4o-mini")
    
    favorites = storage.load_favorites()
    
    if not favorites:
        st.info("还没有收藏任何论文。去搜索页点个 ❤️ 吧！")
    else:
        st.markdown(f"共收藏了 **{len(favorites)}** 篇优质论文")
        st.divider()
        
        for paper_dict in favorites:
            render_paper_card(paper_dict, is_favorite_mode=True, api_key=api_key, base_url=base_url,
                              model_name=model_name)