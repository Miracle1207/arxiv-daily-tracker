import datetime

# ==========================================
# 常量定义：严格复用你代码中的分类
# ==========================================
CATEGORY_QUERIES = {
    "AI & CS (智能组合)": 'cat:cs.CV OR cat:cs.CL OR cat:cs.LG OR cat:cs.AI OR cat:stat.ML OR cat:eess.IV OR cat:cs.RO',
    "Computer Science (仅CS)": 'cat:cs.*',
    "Physics": 'cat:astro-ph OR cat:cond-mat OR cat:gr-qc OR cat:hep-ex OR cat:hep-lat OR cat:hep-ph OR cat:hep-th OR cat:math-ph OR cat:nlin OR cat:nucl-ex OR cat:nucl-th OR cat:physics OR cat:quant-ph',
    "Math": 'cat:math.*',
    "All Fields (全库)": 'all'
}


# ==========================================
# 辅助函数：构建查询语句 (复用你的逻辑)
# ==========================================
def build_query(keywords, category_bundle_key):
    cat_query = CATEGORY_QUERIES[category_bundle_key]
    
    if category_bundle_key == "All Fields (全库)":
        # 全库搜索不需要加 cat: 前缀逻辑
        final_query = keywords
    else:
        # 关键词 + 领域限制
        final_query = f'({keywords}) AND ({cat_query})'
    
    return final_query


# ==========================================
# 辅助函数：生成导出文本
# ==========================================
def generate_export_text(papers, keywords):
    text = f"# ArXiv Papers Report\n"
    text += f"**Keywords:** {keywords}\n"
    text += f"**Date:** {datetime.datetime.now().strftime('%Y-%m-%d')}\n\n"
    text += "---\n\n"
    
    for i, paper in enumerate(papers):
        authors = [a.name for a in paper.authors]
        author_str = ", ".join(authors[:3]) + (" et al." if len(authors) > 3 else "")
        text += f"### {i + 1}. {paper.title}\n"
        text += f"- **Authors:** {author_str}\n"
        text += f"- **Date:** {paper.published.strftime('%Y-%m-%d')}\n"
        text += f"- **Link:** {paper.entry_id}\n"
        text += f"- **Summary:** {paper.summary}\n\n"
        text += "---\n\n"
    
    return text