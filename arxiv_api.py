import arxiv
import datetime
from datetime import timedelta
import streamlit as st


@st.cache_data(ttl=3600)
def fetch_arxiv_papers(query, days_back, max_display_results):
    """
    策略：宽进严出 (完全还原用户原始代码逻辑)。
    1. 向 API 请求比用户需要多 5 倍的数据 (buffer)。
    2. 强制按 Relevance (相关性) 排序。
    3. 在本地进行“时间清洗”，剔除老文章。
    """
    
    # 计算截止日期
    today = datetime.datetime.now(datetime.timezone.utc)
    start_date = today - timedelta(days=days_back)
    
    # 1. 设定抓取缓冲区 (Buffer)
    # 原始逻辑: max_display_results * 5
    fetch_limit = max_display_results * 5
    
    client = arxiv.Client()
    search = arxiv.Search(
        query=query,
        max_results=fetch_limit,
        sort_by=arxiv.SortCriterion.Relevance,  # 强制按相关性
        sort_order=arxiv.SortOrder.Descending
    )
    
    filtered_results = []
    
    # 2. 遍历并清洗数据
    try:
        for result in client.results(search):
            # [时间过滤器]
            # 如果文章发布时间 早于 我们设定的起始时间，丢弃
            if result.published < start_date:
                continue
            
            filtered_results.append(result)
            
            # 如果过滤后的数量已经够了用户要的数量，就停止
            if len(filtered_results) >= max_display_results:
                break
    except Exception as e:
        st.error(f"ArXiv API Error: {e}")
        return []
    
    return filtered_results