"""
AI自媒体起号助手
输入领域/赛道 → 生成账号定位、30天内容规划、爆款选题、完整文案
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from openai import OpenAI
import os
import json

app = FastAPI(title="AI自媒体起号助手")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))


class AccountRequest(BaseModel):
    field: str  # 领域/赛道
    platform: str = "小红书"  # 平台
    target_audience: str = ""  # 目标人群


class TopicRequest(BaseModel):
    field: str
    hot_topic: str = ""
    count: int = 10


class ArticleRequest(BaseModel):
    topic: str
    platform: str = "小红书"
    style: str = "干货分享"


def call_ai(system_prompt: str, user_prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.8,
    )
    return response.choices[0].message.content


@app.get("/", response_class=HTMLResponse)
async def home():
    return """
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>AI自媒体起号助手</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: system-ui, sans-serif; background: #0a0a0a; color: #e5e5e5; }
            .container { max-width: 800px; margin: 0 auto; padding: 2rem; }
            h1 { font-size: 2rem; margin-bottom: 0.5rem; }
            .subtitle { color: #888; margin-bottom: 2rem; }
            .section { background: #141414; border: 1px solid #222; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; }
            .section h2 { font-size: 1.2rem; margin-bottom: 1rem; }
            label { display: block; font-size: 0.9rem; color: #888; margin-bottom: 0.3rem; }
            input, select, textarea { width: 100%; padding: 0.8rem; background: #1a1a1a; border: 1px solid #333; border-radius: 8px; color: #e5e5e5; font-size: 1rem; margin-bottom: 1rem; }
            textarea { min-height: 100px; resize: vertical; }
            button { padding: 0.8rem 2rem; background: #3b82f6; color: white; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; }
            button:hover { background: #2563eb; }
            button:disabled { opacity: 0.5; cursor: not-allowed; }
            .result { background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 1.5rem; margin-top: 1rem; white-space: pre-wrap; line-height: 1.8; }
            .loading { color: #888; font-style: italic; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🚀 AI自媒体起号助手</h1>
            <p class="subtitle">输入你的领域，10分钟生成30天内容规划</p>

            <div class="section">
                <h2>📋 账号定位</h2>
                <label>你的领域/赛道</label>
                <input type="text" id="field" placeholder="例：职场成长、母婴育儿、AI工具、美食探店...">
                <label>目标平台</label>
                <select id="platform">
                    <option value="小红书">小红书</option>
                    <option value="抖音">抖音</option>
                    <option value="公众号">公众号</option>
                    <option value="B站">B站</option>
                </select>
                <label>目标人群（可选）</label>
                <input type="text" id="audience" placeholder="例：25-35岁职场女性">
                <button onclick="generatePlan()">生成账号定位</button>
                <div id="plan-result"></div>
            </div>

            <div class="section">
                <h2>💡 爆款选题</h2>
                <label>输入热点或留空随机生成</label>
                <input type="text" id="hot-topic" placeholder="例：ChatGPT、双11、职场裁员...">
                <button onclick="generateTopics()">生成10个选题</button>
                <div id="topics-result"></div>
            </div>

            <div class="section">
                <h2>✍️ 完整文案</h2>
                <label>选题</label>
                <input type="text" id="article-topic" placeholder="输入一个选题，或从上面复制">
                <label>风格</label>
                <select id="style">
                    <option value="干货分享">干货分享</option>
                    <option value="故事叙述">故事叙述</option>
                    <option value="对比测评">对比测评</option>
                    <option value="经验分享">经验分享</option>
                </select>
                <button onclick="generateArticle()">生成完整文案</button>
                <div id="article-result"></div>
            </div>
        </div>

        <script>
            async function callAPI(endpoint, data, resultId) {
                const resultDiv = document.getElementById(resultId);
                resultDiv.innerHTML = '<p class="loading">生成中...</p>';
                try {
                    const resp = await fetch(endpoint, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(data)
                    });
                    const json = await resp.json();
                    resultDiv.innerHTML = '<div class="result">' + json.result.replace(/\\n/g, '<br>') + '</div>';
                } catch(e) {
                    resultDiv.innerHTML = '<p style="color:red">错误：' + e.message + '</p>';
                }
            }

            function generatePlan() {
                const field = document.getElementById('field').value;
                if (!field) { alert('请输入领域'); return; }
                callAPI('/api/account-plan', {
                    field: field,
                    platform: document.getElementById('platform').value,
                    target_audience: document.getElementById('audience').value
                }, 'plan-result');
            }

            function generateTopics() {
                const field = document.getElementById('field').value;
                if (!field) { alert('请先输入领域'); return; }
                callAPI('/api/topics', {
                    field: field,
                    hot_topic: document.getElementById('hot-topic').value,
                    count: 10
                }, 'topics-result');
            }

            function generateArticle() {
                const topic = document.getElementById('article-topic').value;
                if (!topic) { alert('请输入选题'); return; }
                callAPI('/api/article', {
                    topic: topic,
                    platform: document.getElementById('platform').value,
                    style: document.getElementById('style').value
                }, 'article-result');
            }
        </script>
    </body>
    </html>
    """


@app.post("/api/account-plan")
async def account_plan(req: AccountRequest):
    system = "你是一个资深自媒体运营专家。请根据用户提供的领域，生成详细的账号定位方案。包含：账号人设、内容方向、差异化定位、变现路径。输出格式清晰，使用emoji。"
    user = f"领域：{req.field}\n平台：{req.platform}\n目标人群：{req.target_audience or '待定'}\n\n请生成完整的账号定位方案。"
    result = call_ai(system, user)
    return {"result": result}


@app.post("/api/topics")
async def generate_topics(req: TopicRequest):
    system = "你是一个爆款选题专家。请根据用户提供的领域和热点，生成有爆款潜力的选题。每个选题包含：标题、角度、预估热度。"
    user = f"领域：{req.field}\n热点：{req.hot_topic or '无特定热点'}\n数量：{req.count}个\n\n请生成选题列表。"
    result = call_ai(system, user)
    return {"result": result}


@app.post("/api/article")
async def generate_article(req: ArticleRequest):
    system = f"""你是一个{req.platform}爆款文案写手。请根据选题生成完整的文案。
要求：
- 标题吸引眼球
- 开头有钩子
- 正文有干货
- 结尾有CTA
- 适合{req.platform}平台风格
- 风格：{req.style}"""
    user = f"选题：{req.topic}\n\n请生成完整文案（含标题、正文、标签）。"
    result = call_ai(system, user)
    return {"result": result}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
