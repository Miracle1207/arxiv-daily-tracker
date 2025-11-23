

import os  # 新增 import
from openai import OpenAI


def get_ai_summary(content, title, api_key, base_url, model_name):
    # 优先使用传入的 api_key，如果为空，尝试从环境变量读取
    if not api_key:
        api_key = os.getenv("OPENAI_API_KEY")
    
    if not api_key:
        return "⚠️ 未检测到 API Key。请在侧边栏输入，或在终端设置环境变量 export OPENAI_API_KEY='sk-...'"
    
    # 简单的 Token 截断保护
    if len(content) > 30000:
        content = content[:30000] + "...(truncated)"
    
    client = OpenAI(api_key=api_key, base_url=base_url)
    
    # 针对全文阅读的 Prompt (深度详细版)
    system_prompt = """
    你是一个资深的 AI 学术研究助手。你正在阅读一篇论文的完整正文。
    请忽略格式乱码，专注于深度理解核心逻辑。请用中文详细回答以下 5 个板块的内容。
    **注意：回答需要具体、深入，拒绝泛泛而谈。请尽可能提取论文中的具体术语、参数和实验数据。**

    1. **🧐 背景与痛点 (Background & Motivation)**:
       - 该研究针对的具体问题是什么？
       - 现有的解决方案（SOTA）存在什么具体的局限性和挑战？

    2. **🏗️ 方法论细节 (Methodology)**:
       - 论文提出的核心方法/架构叫什么？
       - 它的工作原理是什么？请分步骤或分模块详细描述关键技术点。

    3. **🧪 实验与评估 (Experiments)**:
       - 使用了哪些具体的数据集？
       - 对比了哪些 Baseline 模型？
       - 核心指标的具体提升数值是多少？（请引用文中的关键数字）

    4. **🤔 优势与局限 (Pros & Cons)**:
       - 相比其他方法，本文最大的优势在哪里？
       - 作者是否提到了该方法的局限性？或者你认为它有什么潜在弱点？

    5. **💡 总结与启发 (Insight)**:
       - 用一句话高度概括这篇论文的核心贡献。
       - 这项工作对未来的研究有什么具体的启发？
    """
    
    try:
        response = client.chat.completions.create(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Title: {title}\n\nContent:\n{content}"}
            ],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ AI 报错: {str(e)}"