"""
深度案例2：AI内容生产平台
批量生成多平台内容：选题、文案、标题、标签
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from openai import OpenAI
import os

app = FastAPI(title="AI内容生产平台")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))


class TopicRequest(BaseModel):
    field: str
    count: int = 10
    platform: str = "小红书"


class ArticleRequest(BaseModel):
    topic: str
    platform: str = "小红书"
    style: str = "干货分享"


class BatchRequest(BaseModel):
    field: str
    platform: str = "小红书"
    count: int = 5


def call_ai(system: str, user: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
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
        <title>AI内容生产平台</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: system-ui, sans-serif; background: #0a0a0a; color: #e5e5e5; }
            .container { max-width: 900px; margin: 0 auto; padding: 2rem; }
            h1 { font-size: 2rem; margin-bottom: 0.5rem; }
            .subtitle { color: #888; margin-bottom: 2rem; }
            .tabs { display: flex; gap: 0.5rem; margin-bottom: 2rem; flex-wrap: wrap; }
            .tab { padding: 0.5rem 1rem; background: #1a1a1a; border: 1px solid #333; border-radius: 8px; cursor: pointer; font-size: 0.9rem; color: #888; }
            .tab.active { background: #3b82f6; border-color: #3b82f6; color: white; }
            .tab-content { display: none; }
            .tab-content.active { display: block; }
            .section { background: #141414; border: 1px solid #222; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; }
            .section h2 { margin-bottom: 1rem; }
            label { display: block; font-size: 0.9rem; color: #888; margin-bottom: 0.3rem; }
            input, select, textarea { width: 100%; padding: 0.8rem; background: #1a1a1a; border: 1px solid #333; border-radius: 8px; color: #e5e5e5; font-size: 1rem; margin-bottom: 1rem; font-family: inherit; }
            textarea { min-height: 120px; resize: vertical; }
            button { padding: 0.8rem 2rem; background: #3b82f6; color: white; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; }
            button:hover { background: #2563eb; }
            .result { background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 1.5rem; margin-top: 1rem; white-space: pre-wrap; line-height: 1.8; font-size: 0.9rem; }
            .copy-btn { padding: 0.4rem 1rem; background: #333; color: #e5e5e5; border: none; border-radius: 8px; font-size: 0.85rem; cursor: pointer; margin-top: 0.5rem; }
            .copy-btn:hover { background: #444; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>AI内容生产平台</h1>
            <p class="subtitle">批量生成多平台内容</p>

            <div class="tabs">
                <div class="tab active" onclick="switchTab('topics')">选题生成</div>
                <div class="tab" onclick="switchTab('article')">文案生成</div>
                <div class="tab" onclick="switchTab('batch')">批量生产</div>
                <div class="tab" onclick="switchTab('analyze')">内容分析</div>
            </div>

            <div id="tab-topics" class="tab-content active">
                <div class="section">
                    <h2>选题生成</h2>
                    <label>你的领域</label>
                    <input type="text" id="t-field" placeholder="例：AI工具、职场成长、母婴育儿">
                    <label>目标平台</label>
                    <select id="t-platform">
                        <option value="小红书">小红书</option>
                        <option value="抖音">抖音</option>
                        <option value="公众号">公众号</option>
                        <option value="B站">B站</option>
                    </select>
                    <label>生成数量</label>
                    <input type="number" id="t-count" value="10" min="1" max="20">
                    <button onclick="generateTopics()">生成选题</button>
                    <div id="topics-result"></div>
                </div>
            </div>

            <div id="tab-article" class="tab-content">
                <div class="section">
                    <h2>文案生成</h2>
                    <label>选题</label>
                    <input type="text" id="a-topic" placeholder="输入选题，或从选题生成结果复制">
                    <label>目标平台</label>
                    <select id="a-platform">
                        <option value="小红书">小红书</option>
                        <option value="抖音">抖音</option>
                        <option value="公众号">公众号</option>
                        <option value="B站">B站</option>
                    </select>
                    <label>风格</label>
                    <select id="a-style">
                        <option value="干货分享">干货分享</option>
                        <option value="故事叙述">故事叙述</option>
                        <option value="对比测评">对比测评</option>
                        <option value="经验分享">经验分享</option>
                        <option value="清单盘点">清单盘点</option>
                    </select>
                    <button onclick="generateArticle()">生成文案</button>
                    <div id="article-result"></div>
                </div>
            </div>

            <div id="tab-batch" class="tab-content">
                <div class="section">
                    <h2>批量生产</h2>
                    <label>领域</label>
                    <input type="text" id="b-field" placeholder="例：AI工具">
                    <label>平台</label>
                    <select id="b-platform">
                        <option value="小红书">小红书</option>
                        <option value="抖音">抖音</option>
                    </select>
                    <label>生成数量</label>
                    <input type="number" id="b-count" value="5" min="1" max="10">
                    <button onclick="batchGenerate()">批量生成</button>
                    <div id="batch-result"></div>
                </div>
            </div>

            <div id="tab-analyze" class="tab-content">
                <div class="section">
                    <h2>内容分析</h2>
                    <label>粘贴要分析的内容</label>
                    <textarea id="an-content" placeholder="粘贴标题+正文..."></textarea>
                    <button onclick="analyzeContent()">分析爆款因素</button>
                    <div id="analyze-result"></div>
                </div>
            </div>
        </div>

        <script>
            function switchTab(name) {
                document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
                document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
                event.target.classList.add('active');
                document.getElementById('tab-'+name).classList.add('active');
            }

            async function callAPI(endpoint, data, resultId) {
                const div = document.getElementById(resultId);
                div.innerHTML = '<div class="result">生成中...</div>';
                try {
                    const resp = await fetch(endpoint, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(data)
                    });
                    const json = await resp.json();
                    div.innerHTML = '<div class="result">' + json.result.replace(/\\n/g, '<br>') + '</div><button class="copy-btn" onclick="copyResult(this)">复制</button>';
                } catch(e) {
                    div.innerHTML = '<p style="color:red">错误：'+e.message+'</p>';
                }
            }

            function copyResult(btn) {
                const pre = btn.previousElementSibling;
                navigator.clipboard.writeText(pre.textContent);
                btn.textContent = '已复制 ✓';
                setTimeout(() => btn.textContent = '复制', 2000);
            }

            function generateTopics() {
                callAPI('/api/topics', {
                    field: document.getElementById('t-field').value,
                    platform: document.getElementById('t-platform').value,
                    count: parseInt(document.getElementById('t-count').value)
                }, 'topics-result');
            }

            function generateArticle() {
                callAPI('/api/article', {
                    topic: document.getElementById('a-topic').value,
                    platform: document.getElementById('a-platform').value,
                    style: document.getElementById('a-style').value
                }, 'article-result');
            }

            function batchGenerate() {
                callAPI('/api/batch', {
                    field: document.getElementById('b-field').value,
                    platform: document.getElementById('b-platform').value,
                    count: parseInt(document.getElementById('b-count').value)
                }, 'batch-result');
            }

            function analyzeContent() {
                callAPI('/api/analyze', {
                    content: document.getElementById('an-content').value
                }, 'analyze-result');
            }
        </script>
    </body>
    </html>
    """


@app.post("/api/topics")
async def generate_topics(req: TopicRequest):
    system = f"""你是一个{req.platform}爆款选题专家。请生成有爆款潜力的选题。
每个选题包含：标题、角度、预估热度（1-5星）。"""
    user = f"领域：{req.field}\n数量：{req.count}个\n\n请生成选题列表。"
    result = call_ai(system, user)
    return {"result": result}


@app.post("/api/article")
async def generate_article(req: ArticleRequest):
    system = f"""你是一个{req.platform}爆款文案写手。风格：{req.style}
请生成完整文案，包含：标题（5个备选）、正文、标签。"""
    user = f"选题：{req.topic}\n\n请生成完整文案。"
    result = call_ai(system, user)
    return {"result": result}


@app.post("/api/batch")
async def batch_generate(req: BatchRequest):
    system = f"""你是一个{req.platform}内容批量生产专家。
请为每个选题生成完整的文案，包含：标题、正文、标签。
用分隔线隔开每篇内容。"""
    user = f"领域：{req.field}\n数量：{req.count}篇\n\n请先生成{req.count}个选题，然后为每个选题生成完整文案。"
    result = call_ai(system, user)
    return {"result": result}


@app.post("/api/analyze")
async def analyze_content(data: dict):
    content = data.get("content", "")
    system = """你是一个内容分析专家。请分析以下内容的爆款因素。
分析维度：
1. 标题吸引力（1-10分）
2. 内容结构
3. 情绪触发点
4. 平台适配度
5. 优化建议"""
    user = f"内容：\n{content}\n\n请分析。"
    result = call_ai(system, user)
    return {"result": result}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
