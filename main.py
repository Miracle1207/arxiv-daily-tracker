import streamlit as st
import arxiv
import datetime
from datetime import timedelta
import pandas as pd
# 在 app.py 最上面导入
from openai import OpenAI
# ==========================================
# 页面配置
# ==========================================
st.set_page_config(
    page_title="ArXiv 论文小助手",
    page_icon="📑",
    layout="wide"
)

# ==========================================
# 侧边栏：搜索条件设置
# ==========================================
st.sidebar.header("🔍 搜索设置")

# 1. 关键词输入
keywords = st.sidebar.text_input("请输入关键词 (支持 AND, OR)", value='(Economic OR Economics OR Finance OR Financial OR Market) AND (LLM OR "Large Language Model" OR RL OR "Reinforcement Learning")')

# 2. 宽泛领域选择 (解决分类不准的问题)
category_bundle = st.sidebar.selectbox(
    "选择搜索范围 (防止漏掉跨领域论文)",
    options=["AI & CS (智能组合)", "Computer Science (仅CS)", "Physics", "Math", "All Fields (全库)"],
    index=0
)

# 定义领域查询语句
category_queries = {
    "AI & CS (智能组合)": 'cat:cs.CV OR cat:cs.CL OR cat:cs.LG OR cat:cs.AI OR cat:stat.ML OR cat:eess.IV OR cat:cs.RO',
    "Computer Science (仅CS)": 'cat:cs.*',
    "Physics": 'cat:astro-ph OR cat:cond-mat OR cat:gr-qc OR cat:hep-ex OR cat:hep-lat OR cat:hep-ph OR cat:hep-th OR cat:math-ph OR cat:nlin OR cat:nucl-ex OR cat:nucl-th OR cat:physics OR cat:quant-ph',
    "Math": 'cat:math.*',
    "All Fields (全库)": 'all'
}

# 3. 时间范围选择
days_back = st.sidebar.slider("搜索过去多少天?", min_value=1, max_value=365, value=7)
today = datetime.datetime.now(datetime.timezone.utc)
start_date = today - timedelta(days=days_back)

# 4. 最大结果数
max_results = st.sidebar.number_input("最大结果数量", min_value=5, max_value=100, value=20)

# 5. 排序方式
sort_by_options = {
    "发布时间 (最新)": arxiv.SortCriterion.SubmittedDate,
    "相关性": arxiv.SortCriterion.Relevance,
    "最后更新时间": arxiv.SortCriterion.LastUpdatedDate
}
sort_text = st.sidebar.selectbox("排序方式", list(sort_by_options.keys()))
sort_criterion = sort_by_options[sort_text]

st.sidebar.header("🤖 AI 设置")
api_key = st.sidebar.text_input("OpenAI API Key", type="password", help="输入你的 API Key 以启用总结功能")

# ==========================================
# 核心逻辑：构建查询并获取数据
# ==========================================

# 构建 ArXiv 查询语句
def build_query(keywords, category_bundle_key):
    cat_query = category_queries[category_bundle_key]
    
    if category_bundle_key == "All Fields (全库)":
        # 全库搜索不需要加 cat: 前缀逻辑
        final_query = keywords
    else:
        # 关键词 + 领域限制
        final_query = f'({keywords}) AND ({cat_query})'
    
    return final_query



# ==========================================
# 优化后的核心抓取函数
# ==========================================

@st.cache_data(ttl=3600)
# @retry(stop=stop_after_attempt(3), wait=wait_fixed(2)) # 如果没装 tenacity 可以注释掉这行
def fetch_arxiv_papers(query, days_back, max_display_results):
    """
    策略：宽进严出。
    1. 向 API 请求比用户需要多 3-5 倍的数据 (buffer)。
    2. 强制按 Relevance (相关性) 排序，保证搜到的都是匹配度高的。
    3. 在本地进行“时间清洗”，剔除老文章。
    4. (可选) 进行“标题优先”重排序。
    """
    
    # 计算截止日期
    today = datetime.datetime.now(datetime.timezone.utc)
    start_date = today - timedelta(days=days_back)
    
    # 1. 设定抓取缓冲区 (Buffer)
    # 如果用户要看 20 篇，我们去 API 抓 100 篇，确保过滤掉老文章后还有剩下的
    fetch_limit = max_display_results * 5
    
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=fetch_limit,
        sort_by=arxiv.SortCriterion.Relevance,  # 强制按相关性，解决“不够match”的问题
        sort_order=arxiv.SortOrder.Descending
    )
    
    filtered_results = []
    
    # 2. 遍历并清洗数据
    for result in client.results(search):
        # [时间过滤器]
        # 如果文章发布时间 早于 我们设定的起始时间，丢弃
        if result.published < start_date:
            continue
        
        # [本地加权逻辑 - 可选]
        # 我们可以给 result 对象加一个自定义属性 score
        # 简单逻辑：标题里有关键词的排在前面
        # 注意：这里仅作简单处理，保留原顺序（因为ArXiv已经算过相关性了），但把时间符合的留下来
        
        filtered_results.append(result)
        
        # 如果过滤后的数量已经够了用户要的数量，就停止
        if len(filtered_results) >= max_display_results:
            break
    
    return filtered_results


def get_ai_summary(abstract, title, api_key):
    if not api_key:
        return "⚠️ 请先在左侧边栏输入 OpenAI API Key"
    
    client = OpenAI(api_key=api_key)
    
    # 提示词工程 (Prompt Engineering)
    system_prompt = """
    你是一个专业的 AI 科研助手。请根据用户提供的论文标题和摘要，用中文回答以下5个问题。
    请保持回答简洁、专业，逻辑清晰。如果摘要中没有提及某点，请说明“摘要未提及”。

    输出格式要求：
    1. **🎯 问题与方法**: （本文使用了什么方法解决了什么问题）...
    2. **⚙️ 关键技术**: ...
    3. **💡 核心创新**: (对比现有方法有何不同)
    4. **📊 验证与结果**: (使用了什么数据，提升了多少)
    5. **🚀 研究意义**: ...
    """
    
    user_prompt = f"Title: {title}\nAbstract: {abstract}"
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",  # 或者 gpt-4o-mini (更便宜更快)
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.3  # 低温度保证事实准确性
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ AI 调用失败: {e}"

# ==========================================
# 主界面展示
# ==========================================
st.title("📑 ArXiv Paper Daily Tracker")
st.markdown(f"**当前搜索:** `{keywords}` | **范围:** `{category_bundle}` | **过去:** `{days_back} 天`")

if st.button("开始抓取", type="primary"):
    if not keywords:
        st.warning("请输入关键词！")
    else:
        with st.spinner('正在连接 ArXiv 数据库...'):
            query_string = build_query(keywords, category_bundle)
            try:
                # papers = fetch_arxiv_papers(query_string, max_results, sort_criterion)
                papers = fetch_arxiv_papers(query_string, days_back, max_results)
                
                if not papers:
                    st.info("未找到符合条件的论文，请尝试放宽时间或更换关键词。")
                else:
                    st.success(f"成功找到 {len(papers)} 篇论文！")
                    st.divider()
                    
                    # 用于收集导出数据的列表
                    export_text = f"# ArXiv Papers: {keywords}\nDate: {datetime.datetime.now().strftime('%Y-%m-%d')}\n\n"

                    # 初始化 session state 用于存储 AI 总结的结果，防止点击按钮后页面刷新结果消失
                    if "summaries" not in st.session_state:
                        st.session_state.summaries = {}

                    for i, paper in enumerate(papers):
                        # 论文卡片布局
                        with st.container():
                            col1, col2 = st.columns([0.85, 0.15])
                            with col1:
                                st.subheader(f"{i + 1}. {paper.title}")
                                # 作者处理
                                authors = [a.name for a in paper.authors]
                                author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
            
                                st.markdown(
                                    f"**✍️ 作者:** {author_str} | **📅 发布:** {paper.published.strftime('%Y-%m-%d')}")
                                st.markdown(f"**🔗 链接:** [PDF]({paper.pdf_url}) | [ArXiv Page]({paper.entry_id})")
        
                            with col2:
                                # 这是一个独特的 Key，确保每个按钮唯一
                                btn_key = f"btn_{paper.entry_id}"
                                if st.button("🤖 AI 深度解读", key=btn_key):
                                    # 点击按钮时，调用 AI
                                    with st.spinner("AI 正在阅读摘要..."):
                                        summary = get_ai_summary(paper.summary, paper.title, api_key)
                                        st.session_state.summaries[paper.entry_id] = summary
        
                            # 展示 AI 总结结果 (如果存在)
                            if paper.entry_id in st.session_state.summaries:
                                st.markdown("#### 🤖 AI 深度分析报告")
                                st.info(st.session_state.summaries[paper.entry_id])
        
                            # 原有的摘要折叠
                            with st.expander("📖 查看原始摘要 (Abstract)"):
                                st.write(paper.summary)
        
                            st.divider()
                        
                        # 准备导出文本
                        export_text += f"### {paper.title}\n- **Authors:** {author_str}\n- **Link:** {paper.entry_id}\n- **Summary:** {paper.summary}\n\n---\n\n"
                    
                    # 导出区域
                    st.header("📤 导出结果")
                    st.download_button(
                        label="下载 Markdown 报告",
                        data=export_text,
                        file_name=f"arxiv_papers_{datetime.datetime.now().strftime('%Y%m%d')}.md",
                        mime="text/markdown"
                    )
            
            except Exception as e:
                st.error(f"发生错误: {e}")

else:
    st.info("👈 请在左侧设置搜索条件，然后点击“开始抓取”")