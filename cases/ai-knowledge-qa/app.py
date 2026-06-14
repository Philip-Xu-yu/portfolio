"""
AI知识库问答助手 v2.0
上传文档 → SQLite 持久化 → 语义搜索 → 基于文档内容回答问题
支持文件上传、多知识库、历史记录
"""

import sys
import os
import json
import sqlite3
import hashlib
from datetime import datetime
from typing import Optional

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared import call_ai, call_ai_json, to_json_response, split_text_chunks

DB_PATH = os.getenv("DATABASE_URL", "data/knowledge_qa.db")

app = FastAPI(title="AI知识库问答助手", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ==================== 数据库 ====================

def get_db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_bases (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                chunk_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS chunks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kb_id TEXT NOT NULL,
                content TEXT NOT NULL,
                chunk_index INTEGER,
                embedding TEXT,
                FOREIGN KEY (kb_id) REFERENCES knowledge_bases(id)
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS qa_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                kb_id TEXT NOT NULL,
                question TEXT NOT NULL,
                answer TEXT NOT NULL,
                sources TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (kb_id) REFERENCES knowledge_bases(id)
            )
        """)
        conn.commit()


init_db()


# ==================== 数据模型 ====================

class QARequest(BaseModel):
    question: str
    kb_id: str = "default"


class DocumentUpload(BaseModel):
    content: str
    name: str = "default"
    description: str = ""


class KBCreate(BaseModel):
    name: str
    description: str = ""


# ==================== 核心功能 ====================

def create_knowledge_base(name: str, description: str = "") -> str:
    """创建知识库"""
    kb_id = hashlib.md5(f"{name}:{datetime.now().isoformat()}".encode()).hexdigest()[:8]
    with get_db() as conn:
        conn.execute(
            "INSERT INTO knowledge_bases (id, name, description) VALUES (?,?,?)",
            (kb_id, name, description)
        )
    return kb_id


def add_document(kb_id: str, content: str) -> int:
    """添加文档到知识库"""
    chunks = split_text_chunks(content, chunk_size=500, overlap=50)

    with get_db() as conn:
        # 获取当前最大索引
        max_idx = conn.execute("SELECT MAX(chunk_index) FROM chunks WHERE kb_id=?", (kb_id,)).fetchone()[0] or 0

        for i, chunk in enumerate(chunks):
            conn.execute(
                "INSERT INTO chunks (kb_id, content, chunk_index) VALUES (?,?,?)",
                (kb_id, chunk, max_idx + i + 1)
            )

        # 更新知识库的 chunk 数量
        total = conn.execute("SELECT COUNT(*) FROM chunks WHERE kb_id=?", (kb_id,)).fetchone()[0]
        conn.execute("UPDATE knowledge_bases SET chunk_count=? WHERE id=?", (total, kb_id))

    return len(chunks)


def search_chunks(kb_id: str, query: str, top_k: int = 5) -> list[str]:
    """搜索相关片段（简单关键词匹配，生产环境用 Embedding）"""
    with get_db() as conn:
        chunks = conn.execute(
            "SELECT content FROM chunks WHERE kb_id=? ORDER BY chunk_index",
            (kb_id,)
        ).fetchall()

    if not chunks:
        return []

    # 简单的关键词匹配评分
    query_words = set(query.lower().split())
    scored = []
    for chunk in chunks:
        content = chunk["content"].lower()
        score = sum(1 for word in query_words if word in content)
        scored.append((score, chunk["content"]))

    # 按分数排序，取 top_k
    scored.sort(key=lambda x: x[0], reverse=True)
    return [content for _, content in scored[:top_k]]


def answer_question(kb_id: str, question: str) -> dict:
    """基于知识库回答问题"""
    # 搜索相关片段
    relevant_chunks = search_chunks(kb_id, question, top_k=5)

    if not relevant_chunks:
        return {
            "answer": "知识库中没有找到相关内容，请先上传文档。",
            "sources": []
        }

    # 构建上下文
    context = "\n---\n".join(relevant_chunks)

    system = f"""你是一个基于文档内容的问答助手。

规则：
1. 只根据提供的文档内容回答问题
2. 如果文档中没有相关内容，明确告知用户"文档中未找到相关信息"
3. 引用文档中的原文作为依据
4. 回答要准确、简洁
5. 在回答末尾标注引用的文档片段编号

文档内容：
{context}"""

    user = f"问题：{question}\n\n请基于文档内容回答。"
    answer = call_ai(system, user, temperature=0.3)

    return {
        "answer": answer,
        "sources": relevant_chunks[:3],
        "chunks_searched": len(relevant_chunks)
    }


# ==================== API 端点 ====================

@app.get("/", response_class=HTMLResponse)
async def home():
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI知识库问答助手 v2.0</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root { --bg: #0a0a0a; --surface: #141414; --border: #222; --text: #e5e5e5; --text-2: #888; --accent: #3b82f6; --success: #22c55e; }
        body { font-family: system-ui, sans-serif; background: var(--bg); color: var(--text); }
        .container { max-width: 900px; margin: 0 auto; padding: 2rem; }
        h1 { font-size: 2rem; margin-bottom: 0.5rem; }
        .subtitle { color: var(--text-2); margin-bottom: 2rem; }
        .section { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; }
        .section h2 { margin-bottom: 1rem; }
        label { display: block; font-size: 0.9rem; color: var(--text-2); margin-bottom: 0.3rem; }
        input, select, textarea { width: 100%; padding: 0.8rem; background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; color: var(--text); font-size: 1rem; margin-bottom: 1rem; font-family: inherit; }
        textarea.doc { min-height: 200px; resize: vertical; }
        textarea.q { min-height: 60px; resize: vertical; }
        button { padding: 0.8rem 2rem; background: var(--accent); color: white; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; }
        button:hover { background: #2563eb; }
        .btn-secondary { background: transparent; border: 1px solid var(--border); color: var(--text); }
        .result { background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; padding: 1.5rem; margin-top: 1rem; white-space: pre-wrap; line-height: 1.8; }
        .loading { color: var(--text-2); font-style: italic; }
        .kb-info { background: #1a2a1a; border: 1px solid #2a4a2a; border-radius: 8px; padding: 1rem; margin-bottom: 1rem; font-size: 0.9rem; }
        .kb-list { margin-bottom: 1rem; }
        .kb-item { background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; padding: 1rem; margin-bottom: 0.5rem; cursor: pointer; display: flex; justify-content: space-between; align-items: center; }
        .kb-item:hover { border-color: var(--accent); }
        .kb-item.active { border-color: var(--success); background: #1a2a1a; }
        .kb-item .name { font-weight: 600; }
        .kb-item .count { font-size: 0.8rem; color: var(--text-2); }
        .tabs { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; }
        .tab { padding: 0.5rem 1rem; background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; cursor: pointer; font-size: 0.9rem; color: var(--text-2); }
        .tab.active { background: var(--accent); border-color: var(--accent); color: white; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .source-box { background: #1a1a1a; border-left: 3px solid var(--accent); padding: 0.8rem; margin-top: 0.5rem; font-size: 0.85rem; color: var(--text-2); }
    </style>
</head>
<body>
    <div class="container">
        <h1>📚 AI知识库问答助手 v2.0</h1>
        <p class="subtitle">上传文档 → 建立知识库 → 基于文档内容回答问题</p>

        <div class="tabs">
            <div class="tab active" onclick="switchTab('qa')">❓ 问答</div>
            <div class="tab" onclick="switchTab('manage')">📁 知识库管理</div>
            <div class="tab" onclick="switchTab('history')">📋 历史记录</div>
        </div>

        <div id="tab-qa" class="tab-content active">
            <div class="section">
                <h2>选择知识库</h2>
                <div class="kb-list" id="kb-list">加载中...</div>
            </div>

            <div class="section">
                <h2>❓ 提问</h2>
                <div class="kb-info" id="kb-status">请先选择知识库</div>
                <label>你的问题</label>
                <textarea class="q" id="question" placeholder="基于上传的文档提问..."></textarea>
                <button onclick="askQuestion()">获取答案</button>
                <div id="qa-result"></div>
            </div>
        </div>

        <div id="tab-manage" class="tab-content">
            <div class="section">
                <h2>创建知识库</h2>
                <label>知识库名称</label>
                <input type="text" id="kb-name" placeholder="例：产品手册、客服FAQ">
                <label>描述（可选）</label>
                <input type="text" id="kb-desc" placeholder="简要描述知识库用途">
                <button onclick="createKB()">创建知识库</button>
            </div>

            <div class="section">
                <h2>上传文档</h2>
                <label>选择知识库</label>
                <select id="upload-kb-select"></select>
                <label>粘贴文档内容</label>
                <textarea class="doc" id="doc-content" placeholder="粘贴你的文档内容：产品手册、FAQ、知识库、论文..."></textarea>
                <button onclick="uploadDoc()">上传文档</button>
                <div id="upload-result"></div>
            </div>
        </div>

        <div id="tab-history" class="tab-content">
            <div class="section">
                <h2>📋 问答历史</h2>
                <div id="history-list">加载中...</div>
            </div>
        </div>
    </div>

    <script>
        let currentKB = null;
        let kbList = [];

        function switchTab(name) {
            document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            event.target.classList.add('active');
            document.getElementById('tab-'+name).classList.add('active');
            if (name === 'qa' || name === 'manage') loadKBList();
            if (name === 'history') loadHistory();
        }

        async function loadKBList() {
            try {
                const resp = await fetch('/api/knowledge-bases');
                const json = await resp.json();
                kbList = json.data || [];
                renderKBList();
                updateKBSelect();
            } catch(e) {
                document.getElementById('kb-list').innerHTML = '<p style="color:red">加载失败</p>';
            }
        }

        function renderKBList() {
            const div = document.getElementById('kb-list');
            if (kbList.length === 0) {
                div.innerHTML = '<p style="color:var(--text-2)">暂无知识库，请先创建</p>';
                return;
            }
            div.innerHTML = kbList.map(kb =>
                '<div class="kb-item' + (currentKB === kb.id ? ' active' : '') + '" onclick="selectKB(\'' + kb.id + '\')">' +
                '<div><div class="name">' + kb.name + '</div>' +
                '<div style="font-size:0.8rem;color:var(--text-2)">' + (kb.description || '') + '</div></div>' +
                '<div class="count">' + kb.chunk_count + ' 个片段</div></div>'
            ).join('');
        }

        function updateKBSelect() {
            const select = document.getElementById('upload-kb-select');
            select.innerHTML = kbList.map(kb =>
                '<option value="' + kb.id + '">' + kb.name + ' (' + kb.chunk_count + '片段)</option>'
            ).join('');
        }

        function selectKB(kbId) {
            currentKB = kbId;
            const kb = kbList.find(k => k.id === kbId);
            document.getElementById('kb-status').textContent = '当前知识库：' + (kb ? kb.name : kbId);
            renderKBList();
        }

        async function createKB() {
            const name = document.getElementById('kb-name').value.trim();
            if (!name) { alert('请输入知识库名称'); return; }
            try {
                const resp = await fetch('/api/knowledge-bases', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({name, description: document.getElementById('kb-desc').value})
                });
                const json = await resp.json();
                if (json.status === 'success') {
                    alert('知识库创建成功！');
                    loadKBList();
                }
            } catch(e) {
                alert('创建失败：' + e.message);
            }
        }

        async function uploadDoc() {
            const content = document.getElementById('doc-content').value.trim();
            const kbId = document.getElementById('upload-kb-select').value;
            if (!content) { alert('请输入文档内容'); return; }
            if (!kbId) { alert('请先创建知识库'); return; }

            const resultDiv = document.getElementById('upload-result');
            resultDiv.innerHTML = '<p class="loading">上传中...</p>';

            try {
                const resp = await fetch('/api/upload', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({content, kb_id: kbId})
                });
                const json = await resp.json();
                resultDiv.innerHTML = '<div class="result">✅ 上传成功！\n\n知识库：' + kbId + '\n新增片段：' + json.data.chunks_added + '\n总片段数：' + json.data.total_chunks + '</div>';
                loadKBList();
            } catch(e) {
                resultDiv.innerHTML = '<p style="color:red">错误：' + e.message + '</p>';
            }
        }

        async function askQuestion() {
            const question = document.getElementById('question').value;
            if (!question) { alert('请输入问题'); return; }
            if (!currentKB) { alert('请先选择知识库'); return; }

            const resultDiv = document.getElementById('qa-result');
            resultDiv.innerHTML = '<p class="loading">思考中...</p>';

            try {
                const resp = await fetch('/api/ask', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({question, kb_id: currentKB})
                });
                const json = await resp.json();
                let html = '<div class="result">' + json.data.answer.replace(/\\n/g, '<br>') + '</div>';
                if (json.data.sources && json.data.sources.length > 0) {
                    html += '<div style="margin-top:1rem"><strong>引用来源：</strong></div>';
                    json.data.sources.forEach((s, i) => {
                        html += '<div class="source-box">片段' + (i+1) + '：' + s.substring(0, 150) + '...</div>';
                    });
                }
                resultDiv.innerHTML = html;
            } catch(e) {
                resultDiv.innerHTML = '<p style="color:red">错误：' + e.message + '</p>';
            }
        }

        async function loadHistory() {
            if (!currentKB) {
                document.getElementById('history-list').innerHTML = '<p style="color:var(--text-2)">请先选择知识库</p>';
                return;
            }
            try {
                const resp = await fetch('/api/history?kb_id=' + currentKB);
                const json = await resp.json();
                const div = document.getElementById('history-list');
                if (!json.data || json.data.length === 0) {
                    div.innerHTML = '<p style="color:var(--text-2)">暂无问答记录</p>';
                    return;
                }
                div.innerHTML = json.data.map(item =>
                    '<div style="background:#1a1a1a;border:1px solid #222;border-radius:8px;padding:1rem;margin-bottom:0.5rem">' +
                    '<div style="font-size:0.8rem;color:#888">' + item.created_at + '</div>' +
                    '<div><strong>Q:</strong> ' + item.question + '</div>' +
                    '<div><strong>A:</strong> ' + item.answer.substring(0, 200) + '...</div>' +
                    '</div>'
                ).join('');
            } catch(e) {
                document.getElementById('history-list').innerHTML = '<p style="color:red">加载失败</p>';
            }
        }

        // 初始化
        loadKBList();
    </script>
</body>
</html>"""


@app.post("/api/knowledge-bases")
async def create_kb(req: KBCreate):
    """创建知识库"""
    kb_id = create_knowledge_base(req.name, req.description)
    return to_json_response({"id": kb_id, "name": req.name})


@app.get("/api/knowledge-bases")
async def list_kbs():
    """列出所有知识库"""
    with get_db() as conn:
        kbs = conn.execute("SELECT * FROM knowledge_bases ORDER BY created_at DESC").fetchall()
    return to_json_response([dict(kb) for kb in kbs])


@app.post("/api/upload")
async def upload_document(req: DocumentUpload):
    """上传文档到知识库"""
    if not req.kb_id:
        raise HTTPException(status_code=400, detail="请指定知识库 ID")

    # 检查知识库是否存在
    with get_db() as conn:
        kb = conn.execute("SELECT * FROM knowledge_bases WHERE id=?", (req.kb_id,)).fetchone()
    if not kb:
        raise HTTPException(status_code=404, detail="知识库不存在")

    chunks_added = add_document(req.kb_id, req.content)

    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM chunks WHERE kb_id=?", (req.kb_id,)).fetchone()[0]

    return to_json_response({
        "kb_id": req.kb_id,
        "chunks_added": chunks_added,
        "total_chunks": total
    })


@app.post("/api/ask")
async def ask_question(req: QARequest):
    """提问"""
    if not req.kb_id:
        raise HTTPException(status_code=400, detail="请指定知识库 ID")

    result = answer_question(req.kb_id, req.question)

    # 保存历史
    with get_db() as conn:
        conn.execute(
            "INSERT INTO qa_history (kb_id, question, answer, sources) VALUES (?,?,?,?)",
            (req.kb_id, req.question, result["answer"], json.dumps(result["sources"], ensure_ascii=False))
        )

    return to_json_response(result)


@app.get("/api/history")
async def get_history(kb_id: str = ""):
    """获取问答历史"""
    with get_db() as conn:
        if kb_id:
            rows = conn.execute(
                "SELECT question, answer, created_at FROM qa_history WHERE kb_id=? ORDER BY id DESC LIMIT 50",
                (kb_id,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT question, answer, created_at FROM qa_history ORDER BY id DESC LIMIT 50"
            ).fetchall()
    return to_json_response([dict(r) for r in rows])


@app.get("/api/stats")
async def get_stats():
    """获取统计信息"""
    with get_db() as conn:
        kb_count = conn.execute("SELECT COUNT(*) FROM knowledge_bases").fetchone()[0]
        chunk_count = conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        qa_count = conn.execute("SELECT COUNT(*) FROM qa_history").fetchone()[0]
    return to_json_response({"knowledge_bases": kb_count, "chunks": chunk_count, "questions": qa_count})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
