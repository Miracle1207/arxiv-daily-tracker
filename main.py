import streamlit as st
import arxiv
import datetime
from datetime import timedelta
import pandas as pd

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
keywords = st.sidebar.text_input("请输入关键词 (支持 AND, OR)", value="LLM AND Reasoning")

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


# 获取数据的函数 (带缓存，防止重复请求)
# @st.cache_data(ttl=3600)  # 缓存1小时
# def fetch_arxiv_papers(query, max_results, sort_criterion):
#     client = arxiv.Client()
#     search = arxiv.Search(
#         query=query,
#         max_results=max_results,
#         sort_by=sort_criterion,
#         sort_order=arxiv.SortOrder.Descending
#     )
#
#     results = []
#     for result in client.results(search):
#         # 二次过滤：确保时间符合（API的sortBy date有时候不绝对精确过滤，手动卡一下更准）
#         # 注意：Relevance 排序时，API 可能会返回旧论文，这里根据用户需求决定是否严格按时间过滤
#         # 如果用户选的是“按时间排序”，通常不需要手动过滤太多，但为了保险起见：
#         if sort_criterion == arxiv.SortCriterion.SubmittedDate:
#             if result.published < start_date:
#                 continue
#
#         results.append(result)
#     return results


from tenacity import retry, stop_after_attempt, wait_fixed


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
                    
                    for i, paper in enumerate(papers):
                        # 格式化作者 (只显示前3位)
                        authors = [a.name for a in paper.authors]
                        author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
                        
                        # 论文卡片
                        with st.container():
                            col1, col2 = st.columns([0.85, 0.15])
                            with col1:
                                st.subheader(f"{i + 1}. {paper.title}")
                                st.markdown(
                                    f"**✍️ 作者:** {author_str} | **📅 发布:** {paper.published.strftime('%Y-%m-%d')}")
                                st.markdown(f"**🔗 链接:** [PDF]({paper.pdf_url}) | [ArXiv Page]({paper.entry_id})")
                            
                            # 摘要折叠区域
                            with st.expander("📖 查看摘要 (Abstract)"):
                                st.write(paper.summary)
                                st.caption(f"Categories: {', '.join(paper.categories)}")
                            
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