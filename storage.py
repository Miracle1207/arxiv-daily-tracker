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
            data = json.load(f)
        
        # [兼容性处理] 确保所有旧数据都有 tags 和 notes 字段
        for paper in data:
            if 'tags' not in paper:
                paper['tags'] = []
            if 'notes' not in paper:
                paper['notes'] = ""
            if 'ai_summary' not in paper:
                paper['ai_summary'] = None
        return data
    
    except Exception:
        return []


def save_favorite(paper_obj, ai_summary=None):
    """
    保存论文到收藏夹。
    """
    favorites = load_favorites()
    paper_id = paper_obj.entry_id
    
    if any(p['entry_id'] == paper_id for p in favorites):
        st.toast("⚠️ 这篇论文已经在收藏夹里啦！")
        return
    
    paper_dict = {
        "title": paper_obj.title,
        "entry_id": paper_obj.entry_id,
        "pdf_url": paper_obj.pdf_url,
        "published": paper_obj.published.strftime('%Y-%m-%d'),
        "authors": [a.name for a in paper_obj.authors],
        "summary": paper_obj.summary,
        "ai_summary": ai_summary,
        "tags": [],  # <--- 新增
        "notes": ""  # <--- 新增
    }
    
    favorites.insert(0, paper_dict)
    
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(favorites, f, ensure_ascii=False, indent=4)
    
    st.toast("✅ 收藏成功！")


def update_favorite_summary(paper_id, ai_summary):
    """更新 AI 解读"""
    favorites = load_favorites()
    updated = False
    
    for p in favorites:
        if p['entry_id'] == paper_id:
            p['ai_summary'] = ai_summary
            updated = True
            break
    
    if updated:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(favorites, f, ensure_ascii=False, indent=4)


def update_favorite_details(paper_id, tags, notes):
    """
    [新增] 更新论文的标签和笔记
    """
    favorites = load_favorites()
    updated = False
    
    for p in favorites:
        if p['entry_id'] == paper_id:
            p['tags'] = tags
            p['notes'] = notes
            updated = True
            break
    
    if updated:
        with open(DB_FILE, "w", encoding="utf-8") as f:
            json.dump(favorites, f, ensure_ascii=False, indent=4)
        st.toast("💾 标签与笔记已保存")


def remove_favorite(paper_id):
    """删除论文"""
    favorites = load_favorites()
    new_list = [p for p in favorites if p['entry_id'] != paper_id]
    
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(new_list, f, ensure_ascii=False, indent=4)
    
    st.toast("🗑️ 已移除收藏")
    st.rerun()


def get_all_unique_tags():
    """获取所有已使用的标签 (用于筛选)"""
    favorites = load_favorites()
    tags = set()
    for p in favorites:
        for t in p.get('tags', []):
            tags.add(t)
    return sorted(list(tags))