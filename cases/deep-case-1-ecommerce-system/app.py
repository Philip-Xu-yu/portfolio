"""
深度案例1：AI电商客服系统 v2.0
多渠道接入、知识库管理、数据分析、自动回复+人工转接
支持 SQLite 持久化、结构化输出、会话历史
"""

import sys
import os
import json
import sqlite3
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared import call_ai, call_ai_json, to_json_response

DB_PATH = os.getenv("DATABASE_URL", "data/ecommerce_cs.db")

app = FastAPI(title="AI电商客服系统", version="2.0.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


def get_db():
    os.makedirs(os.path.dirname(DB_PATH) or ".", exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                user_msg TEXT NOT NULL,
                bot_msg TEXT NOT NULL,
                intent TEXT,
                sentiment TEXT,
                channel TEXT DEFAULT 'web',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_base (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                category TEXT DEFAULT 'general',
                source TEXT DEFAULT 'manual',
                is_active INTEGER DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS feedback (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT,
                conversation_id INTEGER,
                rating INTEGER,
                comment TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()


init_db()


class ChatRequest(BaseModel):
    session_id: str
    message: str
    channel: str = "web"


class KnowledgeRequest(BaseModel):
    content: str
    category: str = "general"
    source: str = "manual"


class FeedbackRequest(BaseModel):
    session_id: str
    conversation_id: int = 0
    rating: int = 5
    comment: str = ""


def get_knowledge_context(category: str = None) -> str:
    """获取知识库上下文"""
    with get_db() as conn:
        if category:
            rows = conn.execute(
                "SELECT content, category FROM knowledge_base WHERE is_active=1 AND category=? ORDER BY id DESC LIMIT 30",
                (category,)
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT content, category FROM knowledge_base WHERE is_active=1 ORDER BY id DESC LIMIT 30"
            ).fetchall()
    return "\n".join([f"[{r['category']}] {r['content']}" for r in rows])


def get_history(session_id: str, limit: int = 10) -> list:
    """获取对话历史"""
    with get_db() as conn:
        rows = conn.execute(
            "SELECT user_msg, bot_msg FROM conversations WHERE session_id=? ORDER BY id DESC LIMIT ?",
            (session_id, limit)
        ).fetchall()
    return list(reversed(rows))


def analyze_intent(message: str) -> dict:
    """分析用户意图"""
    system = """分析用户消息的意图和情绪，返回 JSON：
{
    "intent": "咨询/投诉/购买/退货/其他",
    "sentiment": "positive/neutral/negative",
    "urgency": "high/medium/low",
    "keywords": ["关键词1", "关键词2"]
}"""
    try:
        return call_ai_json(system, f"用户消息：{message}", temperature=0.2)
    except:
        return {"intent": "其他", "sentiment": "neutral", "urgency": "low", "keywords": []}


def generate_reply(message: str, session_id: str, knowledge: str, history: list) -> str:
    """生成客服回复"""
    history_text = ""
    for user_msg, bot_msg in history[-5:]:
        history_text += f"客户：{user_msg}\n客服：{bot_msg}\n"

    system = f"""你是一个专业的电商客服AI助手。

知识库：
{knowledge or '暂无知识库内容'}

对话历史：
{history_text or '新对话'}

回答要求：
1. 简洁友好，使用适当的 emoji
2. 基于知识库内容回答
3. 如果超出知识库范围，说"我需要转接人工客服为您处理"
4. 不要编造信息
5. 如果是投诉，表达歉意并提供解决方案"""

    return call_ai(system, message, temperature=0.5)


@app.get("/", response_class=HTMLResponse)
async def home():
    return """<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI电商客服系统 v2.0</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        :root { --bg: #0a0a0a; --surface: #141414; --border: #222; --text: #e5e5e5; --text-2: #888; --accent: #3b82f6; --success: #22c55e; }
        body { font-family: system-ui, sans-serif; background: var(--bg); color: var(--text); }
        .container { max-width: 1000px; margin: 0 auto; padding: 2rem; }
        h1 { font-size: 2rem; margin-bottom: 0.5rem; }
        .subtitle { color: var(--text-2); margin-bottom: 2rem; }
        .tabs { display: flex; gap: 0.5rem; margin-bottom: 2rem; flex-wrap: wrap; }
        .tab { padding: 0.5rem 1rem; background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; cursor: pointer; font-size: 0.9rem; color: var(--text-2); }
        .tab.active { background: var(--accent); border-color: var(--accent); color: white; }
        .tab-content { display: none; }
        .tab-content.active { display: block; }
        .section { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; }
        .section h2 { margin-bottom: 1rem; }
        .chat-container { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; overflow: hidden; }
        .chat-header { background: #1a1a1a; padding: 1rem 1.5rem; border-bottom: 1px solid var(--border); display: flex; align-items: center; gap: 0.5rem; }
        .chat-header .dot { width: 8px; height: 8px; background: var(--success); border-radius: 50%; }
        .chat-messages { padding: 1.5rem; height: 400px; overflow-y: auto; }
        .msg { margin-bottom: 1rem; display: flex; gap: 0.5rem; }
        .msg.user { justify-content: flex-end; }
        .msg .bubble { max-width: 70%; padding: 0.8rem 1rem; border-radius: 12px; font-size: 0.9rem; line-height: 1.5; }
        .msg.bot .bubble { background: #1a1a1a; border: 1px solid var(--border); }
        .msg.user .bubble { background: var(--accent); color: white; }
        .msg .meta { font-size: 0.7rem; color: var(--text-2); margin-top: 0.3rem; }
        .chat-input { padding: 1rem 1.5rem; border-top: 1px solid var(--border); display: flex; gap: 0.5rem; }
        .chat-input input { flex: 1; padding: 0.8rem; background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; color: var(--text); }
        .chat-input button { padding: 0.8rem 1.5rem; background: var(--accent); color: white; border: none; border-radius: 8px; cursor: pointer; }
        .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
        .stat { background: var(--surface); border: 1px solid var(--border); border-radius: 12px; padding: 1.2rem; text-align: center; }
        .stat .num { font-size: 1.5rem; font-weight: 800; color: var(--accent); }
        .stat .label { font-size: 0.8rem; color: var(--text-2); margin-top: 0.3rem; }
        textarea, input[type="text"] { width: 100%; padding: 0.8rem; background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; color: var(--text); margin-bottom: 1rem; font-family: inherit; }
        textarea { min-height: 100px; resize: vertical; }
        .kb-item { background: #1a1a1a; border: 1px solid var(--border); border-radius: 8px; padding: 1rem; margin-bottom: 0.5rem; display: flex; justify-content: space-between; align-items: center; }
        .kb-item .text { font-size: 0.9rem; flex: 1; }
        .kb-item .category { font-size: 0.75rem; color: var(--accent); background: rgba(59,130,246,0.1); padding: 0.2rem 0.5rem; border-radius: 4px; }
        button.btn { padding: 0.8rem 2rem; background: var(--accent); color: white; border: none; border-radius: 8px; cursor: pointer; font-size: 1rem; }
        .intent-badge { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.75rem; margin-left: 0.5rem; }
        .intent-咨询 { background: rgba(59,130,246,0.2); color: var(--accent); }
        .intent-投诉 { background: rgba(239,68,68,0.2); color: #ef4444; }
        .intent-购买 { background: rgba(34,197,94,0.2); color: var(--success); }
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 AI电商客服系统 v2.0</h1>
        <p class="subtitle">智能客服 + 知识库管理 + 数据分析</p>

        <div class="tabs">
            <div class="tab active" onclick="switchTab('chat')">💬 客服对话</div>
            <div class="tab" onclick="switchTab('kb')">📚 知识库</div>
            <div class="tab" onclick="switchTab('stats')">📊 数据分析</div>
        </div>

        <div id="tab-chat" class="tab-content active">
            <div class="chat-container">
                <div class="chat-header">
                    <div class="dot"></div>
                    <span>AI客服 — 在线</span>
                    <span id="intent-display" style="margin-left:auto;font-size:0.8rem;color:var(--text-2)"></span>
                </div>
                <div class="chat-messages" id="messages">
                    <div class="msg bot"><div class="bubble">您好！我是AI客服，请问有什么可以帮您的？😊</div></div>
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
                <textarea id="kbContent" placeholder="输入知识内容（FAQ、产品信息、售后政策等）"></textarea>
                <div style="display:flex;gap:1rem;margin-bottom:1rem">
                    <div style="flex:1">
                        <label style="display:block;font-size:0.9rem;color:var(--text-2);margin-bottom:0.3rem">分类</label>
                        <select id="kbCategory" style="width:100%;padding:0.8rem;background:#1a1a1a;border:1px solid var(--border);border-radius:8px;color:var(--text)">
                            <option value="general">通用</option>
                            <option value="product">产品信息</option>
                            <option value="shipping">物流配送</option>
                            <option value="return">退换货</option>
                            <option value="payment">支付问题</option>
                        </select>
                    </div>
                    <div style="flex:1">
                        <label style="display:block;font-size:0.9rem;color:var(--text-2);margin-bottom:0.3rem">来源</label>
                        <input type="text" id="kbSource" placeholder="如：产品手册" style="width:100%;padding:0.8rem;background:#1a1a1a;border:1px solid var(--border);border-radius:8px;color:var(--text)">
                    </div>
                </div>
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
                if (data.status === 'error') {
                    addBubble('抱歉，系统出错了：' + data.message, false);
                    return;
                }
                addBubble(data.data.reply, false);
                if (data.data.intent) {
                    document.getElementById('intent-display').innerHTML =
                        '<span class="intent-badge intent-' + data.data.intent + '">' + data.data.intent + '</span>';
                }
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
            const category = document.getElementById('kbCategory').value;
            const source = document.getElementById('kbSource').value.trim() || '手动添加';
            if (!content) return;
            await fetch('/api/knowledge', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({content, category, source})
            });
            document.getElementById('kbContent').value = '';
            document.getElementById('kbSource').value = '';
            loadKB();
        }

        async function loadKB() {
            const resp = await fetch('/api/knowledge');
            const data = await resp.json();
            const div = document.getElementById('kbList');
            div.innerHTML = data.data.map(i =>
                '<div class="kb-item"><div class="text">' + i.content + '</div><div class="category">' + i.category + '</div></div>'
            ).join('');
            document.getElementById('kbCount').textContent = data.data.length;
        }

        async function loadStats() {
            const resp = await fetch('/api/stats');
            const data = await resp.json();
            document.getElementById('totalChats').textContent = data.data.total;
            document.getElementById('todayChats').textContent = data.data.today;
            document.getElementById('avgRating').textContent = data.data.avg_rating || '-';
        }
    </script>
</body>
</html>"""


@app.post("/api/chat")
async def chat(req: ChatRequest):
    """处理客服对话"""
    try:
        knowledge = get_knowledge_context()
        history = get_history(req.session_id)

        # 分析意图
        intent_data = analyze_intent(req.message)

        # 生成回复
        reply = generate_reply(req.message, req.session_id, knowledge, history)

        # 保存对话
        with get_db() as conn:
            conn.execute(
                "INSERT INTO conversations (session_id, user_msg, bot_msg, intent, sentiment, channel) VALUES (?,?,?,?,?,?)",
                (req.session_id, req.message, reply, intent_data.get("intent"), intent_data.get("sentiment"), req.channel)
            )

        return to_json_response({
            "reply": reply,
            "session_id": req.session_id,
            "intent": intent_data.get("intent"),
            "sentiment": intent_data.get("sentiment")
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/knowledge")
async def add_knowledge(req: KnowledgeRequest):
    """添加知识"""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO knowledge_base (content, category, source) VALUES (?,?,?)",
            (req.content, req.category, req.source)
        )
    return to_json_response({"status": "ok"})


@app.get("/api/knowledge")
async def list_knowledge():
    """列出知识库"""
    with get_db() as conn:
        rows = conn.execute("SELECT id, content, category, source FROM knowledge_base WHERE is_active=1 ORDER BY id DESC").fetchall()
    return to_json_response([dict(r) for r in rows])


@app.delete("/api/knowledge/{kb_id}")
async def delete_knowledge(kb_id: int):
    """删除知识"""
    with get_db() as conn:
        conn.execute("UPDATE knowledge_base SET is_active=0 WHERE id=?", (kb_id,))
    return to_json_response({"status": "ok"})


@app.get("/api/stats")
async def get_stats():
    """获取统计"""
    with get_db() as conn:
        total = conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0]
        today = conn.execute("SELECT COUNT(*) FROM conversations WHERE date(created_at)=date('now')").fetchone()[0]
        avg_rating = conn.execute("SELECT AVG(rating) FROM feedback WHERE rating>0").fetchone()[0]
        kb_count = conn.execute("SELECT COUNT(*) FROM knowledge_base WHERE is_active=1").fetchone()[0]
    return to_json_response({
        "total": total,
        "today": today,
        "avg_rating": round(avg_rating, 1) if avg_rating else None,
        "kb_count": kb_count
    })


@app.post("/api/feedback")
async def add_feedback(req: FeedbackRequest):
    """添加反馈"""
    with get_db() as conn:
        conn.execute(
            "INSERT INTO feedback (session_id, conversation_id, rating, comment) VALUES (?,?,?,?)",
            (req.session_id, req.conversation_id, req.rating, req.comment)
        )
    return to_json_response({"status": "ok"})


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
