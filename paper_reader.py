import requests
import io
import fitz  # PyMuPDF
from bs4 import BeautifulSoup


def get_paper_content(paper_entry_id, pdf_url):
    """
    智能获取论文内容：
    1. 优先尝试解析 ArXiv HTML 页面 (极速)。
    2. 如果失败，回退到 PDF 下载模式。
    """
    
    # 提取 paper_id (例如从 http://arxiv.org/abs/2310.xxxxx 提取 2310.xxxxx)
    paper_id = paper_entry_id.split('/')[-1]
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    
    # --- 尝试 1: HTML 路线 ---
    html_url = f"https://arxiv.org/html/{paper_id}"
    
    try:
        response = requests.get(html_url, headers=headers, timeout=10)
        
        # 200 OK 表示有 HTML 版本
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # 清洗无关标签 (参考文献、页脚等)
            for useless_tag in soup.find_all(['nav', 'footer', 'div', 'section'],
                                             class_=['ltx_bibliography', 'ltx_page_footer', 'extra-services']):
                useless_tag.decompose()
            
            # 提取文本
            text = soup.get_text(separator='\n')
            clean_text = "\n".join([line.strip() for line in text.splitlines() if line.strip()])
            
            return clean_text, "HTML (极速)"
    
    except Exception as e:
        print(f"HTML fetch failed, falling back to PDF...")
    
    # --- 尝试 2: PDF 兜底路线 ---
    try:
        response = requests.get(pdf_url, headers=headers, timeout=15)
        pdf_file = io.BytesIO(response.content)
        doc = fitz.open(stream=pdf_file, filetype="pdf")
        
        text = ""
        # 限制读取前 8 页，防止 token 溢出
        read_limit = min(8, len(doc))
        for i in range(read_limit):
            text += doc[i].get_text()
        
        return text, "PDF (兜底)"
    
    except Exception as e:
        return f"Error: {str(e)}", "Failed"