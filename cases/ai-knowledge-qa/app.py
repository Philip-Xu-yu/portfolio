"""
AI知识库问答助手
上传文档 → 自动建立知识库 → 基于文档内容回答问题
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from openai import OpenAI
import os
import json
import hashlib

app = FastAPI(title="AI知识库问答助手")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

# 简单的内存知识库（生产环境应使用向量数据库）
knowledge_bases = {}


class QARequest(BaseModel):
    question: str
    kb_id: str = "default"


class DocumentChunk(BaseModel):
    content: str
    source: str = "user_input"


def call_ai(system_prompt: str, user_prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.3,
    )
    return response.choices[0].message.content


def split_text(text: str, chunk_size: int = 500) -> list:
    """将文本分割成小块"""
    chunks = []
    sentences = text.replace("\n", " ").split("。")
    current = ""
    for s in sentences:
        if len(current) + len(s) > chunk_size:
            if current:
                chunks.append(current.strip())
            current = s
        else:
            current += "。" + s
    if current:
        chunks.append(current.strip())
    return chunks


@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI知识库问答助手</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: system-ui, sans-serif; background: #0a0a0a; color: #e5e5e5; }
            .container { max-width: 800px; margin: 0 auto; padding: 2rem; }
            h1 { font-size: 2rem; margin-bottom: 0.5rem; }
            .subtitle { color: #888; margin-bottom: 2rem; }
            .section { background: #141414; border: 1px solid #222; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; }
            .section h2 { font-size: 1.2rem; margin-bottom: 1rem; }
            label { display: block; font-size: 0.9rem; color: #888; margin-bottom: 0.3rem; }
            textarea { width: 100%; padding: 0.8rem; background: #1a1a1a; border: 1px solid #333; border-radius: 8px; color: #e5e5e5; font-size: 1rem; margin-bottom: 1rem; font-family: inherit; }
            textarea.doc { min-height: 200px; resize: vertical; }
            textarea.q { min-height: 60px; resize: vertical; }
            button { padding: 0.8rem 2rem; background: #3b82f6; color: white; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; }
            button:hover { background: #2563eb; }
            .result { background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 1.5rem; margin-top: 1rem; white-space: pre-wrap; line-height: 1.8; }
            .loading { color: #888; font-style: italic; }
            .kb-info { background: #1a2a1a; border: 1px solid #2a4a2a; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; font-size: 0.9rem; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📚 AI知识库问答助手</h1>
            <p class="subtitle">上传文档 → 建立知识库 → 基于文档内容回答问题</p>

            <div class="section">
                <h2>📤 上传文档</h2>
                <label>粘贴文档内容（支持任意文本）</label>
                <textarea class="doc" id="doc-content" placeholder="粘贴你的文档内容：产品手册、FAQ、知识库、论文..."></textarea>
                <label>知识库名称</label>
                <textarea class="q" id="kb-name" placeholder="例：产品手册、客服FAQ" style="min-height:40px"></textarea>
                <button onclick="uploadDoc()">建立知识库</button>
                <div id="upload-result"></div>
            </div>

            <div class="section">
                <h2>❓ 提问</h2>
                <div class="kb-info" id="kb-status">知识库状态：未建立</div>
                <label>你的问题</label>
                <textarea class="q" id="question" placeholder="基于上传的文档提问..."></textarea>
                <button onclick="askQuestion()">获取答案</button>
                <div id="qa-result"></div>
            </div>
        </div>

        <script>
            let currentKB = null;

            async function uploadDoc() {
                const content = document.getElementById('doc-content').value;
                const name = document.getElementById('kb-name').value || 'default';
                if (!content) { alert('请输入文档内容'); return; }

                const resultDiv = document.getElementById('upload-result');
                resultDiv.innerHTML = '<p class="loading">建立知识库中...</p>';

                try {
                    const resp = await fetch('/api/upload', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({content: content, source: name})
                    });
                    const json = await resp.json();
                    currentKB = json.kb_id;
                    document.getElementById('kb-status').textContent = '知识库状态：已建立 (' + name + ', ' + json.chunks + '个片段)';
                    resultDiv.innerHTML = '<div class="result">✅ 知识库建立成功！\n\n知识库ID：' + json.kb_id + '\n文档片段数：' + json.chunks + '\n\n现在可以提问了。</div>';
                } catch(e) {
                    resultDiv.innerHTML = '<p style="color:red">错误：' + e.message + '</p>';
                }
            }

            async function askQuestion() {
                const question = document.getElementById('question').value;
                if (!question) { alert('请输入问题'); return; }
                if (!currentKB) { alert('请先上传文档建立知识库'); return; }

                const resultDiv = document.getElementById('qa-result');
                resultDiv.innerHTML = '<p class="loading">思考中...</p>';

                try {
                    const resp = await fetch('/api/ask', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({question: question, kb_id: currentKB})
                    });
                    const json = await resp.json();
                    resultDiv.innerHTML = '<div class="result">' + json.answer.replace(/\\n/g, '<br>') + '</div>';
                } catch(e) {
                    resultDiv.innerHTML = '<p style="color:red">错误：' + e.message + '</p>';
                }
            }
        </script>
    </body>
    </html>
    """


@app.post("/api/upload")
async def upload_document(doc: DocumentChunk):
    kb_id = hashlib.md5(doc.source.encode()).hexdigest()[:8]
    chunks = split_text(doc.content)
    knowledge_bases[kb_id] = {
        "source": doc.source,
        "chunks": chunks,
    }
    return {"kb_id": kb_id, "chunks": len(chunks), "source": doc.source}


@app.post("/api/ask")
async def ask_question(req: QARequest):
    if req.kb_id not in knowledge_bases:
        raise HTTPException(status_code=404, detail="知识库不存在，请先上传文档")

    kb = knowledge_bases[req.kb_id]
    context = "\n---\n".join(kb["chunks"][:10])  # 取前10个片段作为上下文

    system = f"""你是基于文档内容的问答助手。
规则：
1. 只根据提供的文档内容回答问题
2. 如果文档中没有相关内容，明确告知用户
3. 引用文档中的原文作为依据
4. 回答要准确、简洁

文档来源：{kb['source']}
文档内容：
{context}"""

    user = f"问题：{req.question}\n\n请基于文档内容回答。"
    answer = call_ai(system, user)
    return {"answer": answer, "kb_id": req.kb_id, "source": kb["source"]}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
