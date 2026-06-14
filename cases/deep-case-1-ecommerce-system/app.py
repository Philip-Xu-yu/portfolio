"""
深度案例1：完整AI电商客服系统
多渠道接入、知识库管理、数据分析、自动回复+人工转接
"""

from fastapi import FastAPI, HTTPException, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from openai import OpenAI
import os
import json
import sqlite3
from datetime import datetime
from typing import Optional

app = FastAPI(title="AI电商客服系统")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))

# 数据库初始化
def init_db():
    conn = sqlite3.connect("客服系统.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS conversations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            user_msg TEXT,
            bot_msg TEXT,
            channel TEXT DEFAULT "web",
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS knowledge_base (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            content TEXT,
            source TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT,
            rating INTEGER,
            comment TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()


class ChatRequest(BaseModel):
    session_id: str
    message: str
    channel: str = "web"


class FeedbackRequest(BaseModel):
    session_id: str
    rating: int
    comment: str = ""


class KnowledgeRequest(BaseModel):
    content: str
    source: str = "manual"


def get_knowledge():
    conn = sqlite3.connect("客服系统.db")
    c = conn.cursor()
    c.execute("SELECT content, source FROM knowledge_base ORDER BY id DESC LIMIT 50")
    rows = c.fetchall()
    conn.close()
    return "\n".join([f"[{r[1]}] {r[0]}" for r in rows])


def get_history(session_id: str, limit: int = 10):
    conn = sqlite3.connect("客服系统.db")
    c = conn.cursor()
    c.execute(
        "SELECT user_msg, bot_msg FROM conversations WHERE session_id=? ORDER BY id DESC LIMIT ?",
        (session_id, limit),
    )
    rows = c.fetchall()
    conn.close()
    return list(reversed(rows))


def save_conversation(session_id: str, user_msg: str, bot_msg: str, channel: str):
    conn = sqlite3.connect("客服系统.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO conversations (session_id, user_msg, bot_msg, channel) VALUES (?,?,?,?)",
        (session_id, user_msg, bot_msg, channel),
    )
    conn.commit()
    conn.close()


@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <title>AI电商客服系统</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: system-ui, sans-serif; background: #0a0a0a; color: #e5e5e5; }
            .container { max-width: 900px; margin: 0 auto; padding: 2rem; }
            h1 { font-size: 2rem; margin-bottom: 0.5rem; }
            .subtitle { color: #888; margin-bottom: 2rem; }
            .tabs { display: flex; gap: 0.5rem; margin-bottom: 2rem; }
            .tab { padding: 0.5rem 1rem; background: #1a1a1a; border: 1px solid #333; border-radius: 8px; cursor: pointer; font-size: 0.9rem; color: #888; }
            .tab.active { background: #3b82f6; border-color: #3b82f6; color: white; }
            .tab-content { display: none; }
            .tab-content.active { display: block; }
            .section { background: #141414; border: 1px solid #222; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; }
            .section h2 { margin-bottom: 1rem; }
            .chat-container { background: #141414; border: 1px solid #222; border-radius: 12px; overflow: hidden; }
            .chat-header { background: #1a1a1a; padding: 1rem 1.5rem; border-bottom: 1px solid #222; display: flex; align-items: center; gap: 0.5rem; }
            .chat-header .dot { width: 8px; height: 8px; background: #22c55e; border-radius: 50%; }
            .chat-messages { padding: 1.5rem; height: 400px; overflow-y: auto; }
            .msg { margin-bottom: 1rem; display: flex; gap: 0.5rem; }
            .msg.user { justify-content: flex-end; }
            .msg .bubble { max-width: 70%; padding: 0.8rem 1rem; border-radius: 12px; font-size: 0.9rem; line-height: 1.5; }
            .msg.bot .bubble { background: #1a1a1a; border: 1px solid #333; }
            .msg.user .bubble { background: #3b82f6; color: white; }
            .chat-input { padding: 1rem 1.5rem; border-top: 1px solid #222; display: flex; gap: 0.5rem; }
            .chat-input input { flex: 1; padding: 0.8rem; background: #1a1a1a; border: 1px solid #333; border-radius: 8px; color: #e5e5e5; }
            .chat-input button { padding: 0.8rem 1.5rem; background: #3b82f6; color: white; border: none; border-radius: 8px; cursor: pointer; }
            textarea, input[type="text"] { width: 100%; padding: 0.8rem; background: #1a1a1a; border: 1px solid #333; border-radius: 8px; color: #e5e5e5; margin-bottom: 1rem; font-family: inherit; }
            textarea { min-height: 100px; resize: vertical; }
            .stats { display: grid; grid-template-columns: repeat(4, 1fr); gap: 1rem; margin-bottom: 2rem; }
            .stat { background: #141414; border: 1px solid #222; border-radius: 12px; padding: 1.2rem; text-align: center; }
            .stat .num { font-size: 1.5rem; font-weight: 800; color: #3b82f6; }
            .stat .label { font-size: 0.8rem; color: #888; margin-top: 0.3rem; }
            .kb-item { background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 1rem; margin-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center; }
            .kb-item .text { font-size: 0.9rem; flex: 1; }
            .kb-item .source { font-size: 0.75rem; color: #888; }
            button.btn { padding: 0.8rem 2rem; background: #3b82f6; color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 1rem; }
            @media (max-width: 768px) { .stats { grid-template-columns: repeat(2, 1fr); } }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>AI电商客服系统</h1>
            <p class="subtitle">完整后台管理界面</p>

            <div class="tabs">
                <div class="tab active" onclick="switchTab('chat')">客服对话</div>
                <div class="tab" onclick="switchTab('kb')">知识库</div>
                <div class="tab" onclick="switchTab('stats')">数据分析</div>
            </div>

            <div id="tab-chat" class="tab-content active">
                <div class="chat-container">
                    <div class="chat-header">
                        <div class="dot"></div>
                        <span>AI客服 — 在线</span>
                    </div>
                    <div class="chat-messages" id="messages">
                        <div class="msg bot"><div class="bubble">您好！我是AI客服，请问有什么可以帮您的？</div></div>
                    </div>
                    <div class="chat-input">
                        <input type="text" id="userInput" placeholder="输入消息..." onkeydown="if(event.key==='Enter')sendMsg()">
                        <button onclick="sendMsg()">发送</button>
                    </div>
                </div>
            </div>

            <div id="tab-kb" class="tab-content">
                <div class="section">
                    <h2>添加知识</h2>
                    <textarea id="kbContent" placeholder="输入知识内容（FAQ、产品信息等）"></textarea>
                    <input type="text" id="kbSource" placeholder="来源（如：产品手册、FAQ）">
                    <button class="btn" onclick="addKnowledge()">添加</button>
                </div>
                <div class="section">
                    <h2>知识库内容</h2>
                    <div id="kbList"></div>
                </div>
            </div>

            <div id="tab-stats" class="tab-content">
                <div class="stats">
                    <div class="stat"><div class="num" id="totalChats">0</div><div class="label">总对话数</div></div>
                    <div class="stat"><div class="num" id="todayChats">0</div><div class="label">今日对话</div></div>
                    <div class="stat"><div class="num" id="avgRating">-</div><div class="label">平均评分</div></div>
                    <div class="stat"><div class="num" id="kbCount">0</div><div class="label">知识条数</div></div>
                </div>
                <div class="section">
                    <h2>最近对话</h2>
                    <div id="recentChats"></div>
                </div>
            </div>
        </div>

        <script>
            const sessionId = 'session_' + Date.now();

            function switchTab(name) {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
                event.target.classList.add('active');
                document.getElementById('tab-'+name).classList.add('active');
                if (name === 'stats') loadStats();
                if (name === 'kb') loadKB();
            }

            async function sendMsg() {
                const input = document.getElementById('userInput');
                const msg = input.value.trim();
                if (!msg) return;
                addBubble(msg, true);
                input.value = '';
                try {
                    const resp = await fetch('/api/chat', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify({session_id: sessionId, message: msg, channel: 'web'})
                    });
                    const data = await resp.json();
                    addBubble(data.reply, false);
                } catch(e) {
                    addBubble('抱歉，系统出错了，请稍后重试。', false);
                }
            }

            function addBubble(text, isUser) {
                const div = document.createElement('div');
                div.className = 'msg ' + (isUser ? 'user' : 'bot');
                div.innerHTML = '<div class="bubble">' + text.replace(/\\n/g, '<br>') + '</div>';
                document.getElementById('messages').appendChild(div);
                document.getElementById('messages').scrollTop = document.getElementById('messages').scrollHeight;
            }

            async function addKnowledge() {
                const content = document.getElementById('kbContent').value.trim();
                const source = document.getElementById('kbSource').value.trim() || '手动添加';
                if (!content) return;
                await fetch('/api/knowledge', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json'},
                    body: JSON.stringify({content, source})
                });
                document.getElementById('kbContent').value = '';
                document.getElementById('kbSource').value = '';
                loadKB();
            }

            async function loadKB() {
                const resp = await fetch('/api/knowledge');
                const data = await resp.json();
                const div = document.getElementById('kbList');
                div.innerHTML = data.items.map(i =>
                    '<div class="kb-item"><div class="text">' + i.content + '</div><div class="source">' + i.source + '</div></div>'
                ).join('');
                document.getElementById('kbCount').textContent = data.items.length;
            }

            async function loadStats() {
                const resp = await fetch('/api/stats');
                const data = await resp.json();
                document.getElementById('totalChats').textContent = data.total;
                document.getElementById('todayChats').textContent = data.today;
                document.getElementById('avgRating').textContent = data.avg_rating || '-';
            }
        </script>
    </body>
    </html>
    """


@app.post("/api/chat")
async def chat(req: ChatRequest):
    knowledge = get_knowledge()
    history = get_history(req.session_id)

    messages = [
        {
            "role": "system",
            "content": f"""你是一个专业的电商客服AI助手。
请基于以下知识库内容回答客户问题。
如果问题超出知识库范围，请诚实说"我需要转接人工客服为您处理"。

知识库：
{knowledge}

回答要求：
- 简洁友好
- 使用emoji
- 不要编造信息""",
        }
    ]

    for user_msg, bot_msg in history:
        messages.append({"role": "user", "content": user_msg})
        messages.append({"role": "assistant", "content": bot_msg})

    messages.append({"role": "user", "content": req.message})

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", messages=messages, temperature=0.7
        )
        reply = response.choices[0].message.content
    except Exception as e:
        reply = "抱歉，系统繁忙，请稍后重试。"

    save_conversation(req.session_id, req.message, reply, req.channel)
    return {"reply": reply, "session_id": req.session_id}


@app.post("/api/knowledge")
async def add_knowledge(req: KnowledgeRequest):
    conn = sqlite3.connect("客服系统.db")
    c = conn.cursor()
    c.execute("INSERT INTO knowledge_base (content, source) VALUES (?,?)", (req.content, req.source))
    conn.commit()
    conn.close()
    return {"status": "ok"}


@app.get("/api/knowledge")
async def list_knowledge():
    conn = sqlite3.connect("客服系统.db")
    c = conn.cursor()
    c.execute("SELECT id, content, source FROM knowledge_base ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return {"items": [{"id": r[0], "content": r[1], "source": r[2]} for r in rows]}


@app.get("/api/stats")
async def get_stats():
    conn = sqlite3.connect("客服系统.db")
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM conversations")
    total = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM conversations WHERE date(created_at)=date('now')")
    today = c.fetchone()[0]
    c.execute("SELECT AVG(rating) FROM feedback WHERE rating>0")
    avg_rating = c.fetchone()[0]
    c.execute("SELECT COUNT(*) FROM knowledge_base")
    kb_count = c.fetchone()[0]
    conn.close()
    return {
        "total": total,
        "today": today,
        "avg_rating": round(avg_rating, 1) if avg_rating else None,
        "kb_count": kb_count,
    }


@app.post("/api/feedback")
async def add_feedback(req: FeedbackRequest):
    conn = sqlite3.connect("客服系统.db")
    c = conn.cursor()
    c.execute(
        "INSERT INTO feedback (session_id, rating, comment) VALUES (?,?,?)",
        (req.session_id, req.rating, req.comment),
    )
    conn.commit()
    conn.close()
    return {"status": "ok"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
