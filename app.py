import streamlit as st
import datetime
import os
import utils
import arxiv_api
import paper_reader
import ai_agent
import storage

# ==========================================
# 页面配置
# ==========================================
st.set_page_config(page_title="ArXiv 论文小助手", page_icon="📑", layout="wide")

# ==========================================
# 侧边栏：全局设置 & 模式切换
# ==========================================
mode = st.sidebar.radio("功能模式", ["🔍 论文搜索", "⭐ 我的收藏"])
st.sidebar.divider()

# 初始化 Session State
if "papers" not in st.session_state:
    st.session_state.papers = []
if "summaries" not in st.session_state:
    st.session_state.summaries = {}


# ==========================================
# 辅助函数：统一渲染卡片
# ==========================================
def render_paper_card(paper, is_favorite_mode=False, api_key=None, base_url=None, model_name=None):
    """
    渲染单个论文卡片，复用于搜索页和收藏页。
    """
    # 统一数据格式
    if isinstance(paper, dict):
        title = paper['title']
        entry_id = paper['entry_id']
        pdf_url = paper['pdf_url']
        published_date = paper['published']
        authors_list = paper['authors']
        summary_text = paper['summary']
        # 获取标签和笔记 (仅收藏模式下有效)
        current_tags = paper.get('tags', [])
        current_notes = paper.get('notes', "")
    else:
        title = paper.title
        entry_id = paper.entry_id
        pdf_url = paper.pdf_url
        published_date = paper.published.strftime('%Y-%m-%d')
        authors_list = [a.name for a in paper.authors]
        summary_text = paper.summary
        current_tags = []
        current_notes = ""
    
    # --- UI 渲染 ---
    with st.container():
        col1, col2 = st.columns([0.85, 0.15])
        
        with col1:
            st.subheader(title)
            
            # [新增] 如果有标签，在标题下方显示
            if is_favorite_mode and current_tags:
                # 使用 Markdown 模拟 Tag 样式
                tag_str = " ".join([f"`{t}`" for t in current_tags])
                st.markdown(f"🏷️ {tag_str}")
            
            author_str = ", ".join(authors_list[:3]) + (" et al." if len(authors_list) > 3 else "")
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
                    storage.update_favorite_summary(entry_id, summary)
                    status.empty()
            
            # 2. 收藏/移除按钮
            if is_favorite_mode:
                if st.button("❌ 移除", key=f"del_{entry_id}"):
                    storage.remove_favorite(entry_id)
            else:
                if st.button("❤️ 收藏", key=f"fav_{entry_id}"):
                    current_ai_summary = st.session_state.summaries.get(entry_id)
                    storage.save_favorite(paper, ai_summary=current_ai_summary)
        
        # 展示 AI 结果
        if entry_id in st.session_state.summaries:
            with st.expander("📝 AI 深度分析", expanded=True):
                st.info(st.session_state.summaries[entry_id])
        
        # [新增] 标签与笔记编辑区 (仅在收藏模式显示)
        if is_favorite_mode:
            with st.expander("🏷️ 编辑标签 & 📝 个人笔记"):
                with st.form(key=f"form_{entry_id}"):
                    # 标签输入
                    tags_str = st.text_input("标签 (用逗号分隔, 例如: LLM, Economics)", value=", ".join(current_tags))
                    # 笔记输入
                    notes_content = st.text_area("个人笔记 / 备忘录", value=current_notes, height=100)
                    
                    if st.form_submit_button("💾 保存更改"):
                        # 处理标签字符串 -> 列表
                        new_tags = [t.strip() for t in tags_str.split(",") if t.strip()]
                        storage.update_favorite_details(entry_id, new_tags, notes_content)
                        st.rerun()
        
        with st.expander("📖 摘要 (Abstract)"):
            st.write(summary_text)
        
        st.divider()


# ==========================================
# 页面 1: 🔍 论文搜索
# ==========================================
if mode == "🔍 论文搜索":
    st.sidebar.header("🔍 搜索设置")
    
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
    
    st.title("📑 ArXiv Paper Daily Tracker")
    st.caption(f"当前模式: {category_bundle} | 窗口: {days_back}天 | 关键词：{keywords}")
    
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
    
    if st.session_state.papers:
        st.divider()
        for paper in st.session_state.papers:
            render_paper_card(paper, is_favorite_mode=False, api_key=api_key, base_url=base_url, model_name=model_name)
        
        st.header("📤 导出结果")
        if st.button("生成 Markdown 报告"):
            export_text = utils.generate_export_text(st.session_state.papers, keywords)
            st.download_button("下载文件", export_text, f"arxiv_report_{datetime.date.today()}.md")

# ==========================================
# 页面 2: ⭐ 我的收藏
# ==========================================
elif mode == "⭐ 我的收藏":
    st.title("⭐ 我的论文收藏夹")
    
    st.sidebar.header("🤖 AI 设置")
    env_api_key = os.getenv("OPENAI_API_KEY", "")
    api_key = st.sidebar.text_input("API Key", value=env_api_key, type="password")
    base_url = st.sidebar.text_input("Base URL", value="https://api.openai.com/v1")
    model_name = st.sidebar.text_input("模型名称", value="gpt-4o-mini")
    
    # 1. 加载所有收藏
    favorites = storage.load_favorites()
    
    if not favorites:
        st.info("还没有收藏任何论文。去搜索页点个 ❤️ 吧！")
    else:
        # [新增] 顶部标签筛选器
        all_tags = storage.get_all_unique_tags()
        if all_tags:
            selected_tags = st.multiselect("🏷️ 按标签筛选 (显示满足任一标签的论文)", options=all_tags)
        else:
            selected_tags = []
        
        # 执行筛选逻辑
        if selected_tags:
            # 只要包含选中的任意一个标签，就显示 (OR 逻辑)
            display_papers = [
                p for p in favorites
                if any(tag in p.get('tags', []) for tag in selected_tags)
            ]
        else:
            display_papers = favorites
        
        st.markdown(f"显示 **{len(display_papers)}** 篇论文 (总收藏: {len(favorites)})")
        st.divider()
        
        for paper_dict in display_papers:
            # 自动加载 AI 解读
            entry_id = paper_dict['entry_id']
            if paper_dict.get('ai_summary') and entry_id not in st.session_state.summaries:
                st.session_state.summaries[entry_id] = paper_dict['ai_summary']
            
            render_paper_card(paper_dict, is_favorite_mode=True, api_key=api_key, base_url=base_url,
                              model_name=model_name)