import json
import os
import streamlit as st

DB_FILE = "my_favorites.json"


def load_favorites():
    """从本地 JSON 文件加载收藏列表"""
    if not os.path.exists(DB_FILE):
        return []
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []


def save_favorite(paper_obj):
    """
    保存论文。
    注意：arxiv 的 Result 对象不能直接存 JSON，
    我们需要把它转换成普通的 Python 字典。
    """
    favorites = load_favorites()
    
    # 提取 paper_id 用于查重
    paper_id = paper_obj.entry_id
    
    # 查重：如果已经存在，就不存了
    if any(p['entry_id'] == paper_id for p in favorites):
        st.toast("⚠️ 这篇论文已经在收藏夹里啦！")
        return
    
    # 将 arxiv 对象转为字典
    paper_dict = {
        "title": paper_obj.title,
        "entry_id": paper_obj.entry_id,
        "pdf_url": paper_obj.pdf_url,
        "published": paper_obj.published.strftime('%Y-%m-%d'),
        "authors": [a.name for a in paper_obj.authors],
        "summary": paper_obj.summary
    }
    
    favorites.insert(0, paper_dict)  # 新收藏的放最前面
    
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(favorites, f, ensure_ascii=False, indent=4)
    
    st.toast("✅ 收藏成功！")


def remove_favorite(paper_id):
    """根据 ID 删除论文"""
    favorites = load_favorites()
    new_list = [p for p in favorites if p['entry_id'] != paper_id]
    
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(new_list, f, ensure_ascii=False, indent=4)
    
    st.toast("🗑️ 已移除收藏")
    st.rerun()  # 强制刷新页面