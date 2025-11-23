import arxiv
import datetime
from datetime import timedelta
import streamlit as st


@st.cache_data(ttl=3600)
def fetch_arxiv_papers(query, days_back, max_display_results):
    """
    策略：时间优先 + 精准匹配 (Time-First Strict Search)。
    1. 按 'SubmittedDate' (提交时间) 倒序抓取。
    2. 这样保证了只要最近几天有符合 'utils.py' 中构造的精准 query 的论文，
       它一定会被抓取到，而不会被埋没在老的高引论文中。
    """
    
    # 计算截止日期
    today = datetime.datetime.now(datetime.timezone.utc)
    start_date = today - timedelta(days=days_back)
    
    # 设定缓冲区：因为是按时间排序，我们不需要抓太多
    # 只要抓取量覆盖了"过去N天"的所有论文即可，给个 10 倍缓冲很安全
    fetch_limit = max_display_results * 10
    
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=fetch_limit,
        sort_by=arxiv.SortCriterion.SubmittedDate,  # <--- 关键修改：按时间排序
        sort_order=arxiv.SortOrder.Descending
    )
    
    filtered_results = []
    
    try:
        for result in client.results(search):
            # 1. 时间硬过滤
            if result.published < start_date:
                # 因为是按时间倒序，一旦遇到早于 start_date 的，
                # 说明后面的更老，直接停止抓取 (极大提升效率)
                break
            
            filtered_results.append(result)
            
            # 数量够了就停止
            if len(filtered_results) >= max_display_results:
                break
    
    except Exception as e:
        st.error(f"ArXiv API Error: {e}")
        return []
    
    return filtered_results