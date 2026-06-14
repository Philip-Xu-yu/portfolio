"""
AI爆款内容分析器
输入内容链接/文本 → 分析爆款因素、生成优化建议
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from openai import OpenAI
import os

app = FastAPI(title="AI爆款内容分析器")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY", ""))


class AnalyzeRequest(BaseModel):
    content: str  # 要分析的内容文本
    platform: str = "小红书"  # 平台


class OptimizeRequest(BaseModel):
    content: str  # 原始内容
    issues: str = ""  # 已知问题（可选）
    platform: str = "小红书"


class RewriteRequest(BaseModel):
    content: str  # 原始内容
    style: str = "爆款风格"  # 目标风格
    platform: str = "小红书"


def call_ai(system_prompt: str, user_prompt: str) -> str:
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
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
        <title>AI爆款内容分析器</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body { font-family: system-ui, sans-serif; background: #0a0a0a; color: #e5e5e5; }
            .container { max-width: 800px; margin: 0 auto; padding: 2rem; }
            h1 { font-size: 2rem; margin-bottom: 0.5rem; }
            .subtitle { color: #888; margin-bottom: 2rem; }
            .section { background: #141414; border: 1px solid #222; border-radius: 12px; padding: 1.5rem; margin-bottom: 1.5rem; }
            .section h2 { font-size: 1.2rem; margin-bottom: 1rem; }
            label { display: block; font-size: 0.9rem; color: #888; margin-bottom: 0.3rem; }
            input, select, textarea { width: 100%; padding: 0.8rem; background: #1a1a1a; border: 1px solid #333; border-radius: 8px; color: #e5e5e5; font-size: 1rem; margin-bottom: 1rem; font-family: inherit; }
            textarea { min-height: 150px; resize: vertical; }
            button { padding: 0.8rem 2rem; background: #3b82f6; color: white; border: none; border-radius: 8px; font-size: 1rem; cursor: pointer; }
            button:hover { background: #2563eb; }
            .result { background: #1a1a1a; border: 1px solid #333; border-radius: 8px; padding: 1.5rem; margin-top: 1rem; white-space: pre-wrap; line-height: 1.8; }
            .loading { color: #888; font-style: italic; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>📊 AI爆款内容分析器</h1>
            <p class="subtitle">输入内容，AI帮你分析爆款因素并生成优化建议</p>

            <div class="section">
                <h2>🔍 内容分析</h2>
                <label>粘贴要分析的内容</label>
                <textarea id="content" placeholder="粘贴一篇文章、一条笔记、一段文案..."></textarea>
                <label>平台</label>
                <select id="platform">
                    <option value="小红书">小红书</option>
                    <option value="抖音">抖音</option>
                    <option value="公众号">公众号</option>
                    <option value="B站">B站</option>
                </select>
                <button onclick="analyzeContent()">分析爆款因素</button>
                <div id="analyze-result"></div>
            </div>

            <div class="section">
                <h2>✨ 优化建议</h2>
                <button onclick="getOptimization()">基于分析结果生成优化建议</button>
                <div id="optimize-result"></div>
            </div>

            <div class="section">
                <h2>🔄 仿写生成</h2>
                <label>仿写风格</label>
                <select id="style">
                    <option value="爆款风格">爆款风格</option>
                    <option value="专业干货">专业干货</option>
                    <option value="轻松幽默">轻松幽默</option>
                    <option value="情感共鸣">情感共鸣</option>
                </select>
                <button onclick="rewriteContent()">生成仿写内容</button>
                <div id="rewrite-result"></div>
            </div>
        </div>

        <script>
            let analysisResult = '';

            async function callAPI(endpoint, data, resultId) {
                const resultDiv = document.getElementById(resultId);
                resultDiv.innerHTML = '<p class="loading">分析中...</p>';
                try {
                    const resp = await fetch(endpoint, {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(data)
                    });
                    const json = await resp.json();
                    resultDiv.innerHTML = '<div class="result">' + json.result.replace(/\\n/g, '<br>') + '</div>';
                    return json.result;
                } catch(e) {
                    resultDiv.innerHTML = '<p style="color:red">错误：' + e.message + '</p>';
                    return '';
                }
            }

            async function analyzeContent() {
                const content = document.getElementById('content').value;
                if (!content) { alert('请输入内容'); return; }
                analysisResult = await callAPI('/api/analyze', {
                    content: content,
                    platform: document.getElementById('platform').value
                }, 'analyze-result');
            }

            async function getOptimization() {
                const content = document.getElementById('content').value;
                if (!content) { alert('请先输入内容并分析'); return; }
                await callAPI('/api/optimize', {
                    content: content,
                    platform: document.getElementById('platform').value
                }, 'optimize-result');
            }

            async function rewriteContent() {
                const content = document.getElementById('content').value;
                if (!content) { alert('请先输入内容'); return; }
                await callAPI('/api/rewrite', {
                    content: content,
                    style: document.getElementById('style').value,
                    platform: document.getElementById('platform').value
                }, 'rewrite-result');
            }
        </script>
    </body>
    </html>
    """


@app.post("/api/analyze")
async def analyze_content(req: AnalyzeRequest):
    system = f"""你是一个{req.platform}爆款内容分析专家。请从以下维度分析内容：
1. 标题分析（吸引力、关键词、情绪词、数字使用）
2. 内容结构（钩子、正文框架、CTA）
3. 情绪触发点（共鸣、好奇、焦虑、兴奋）
4. 平台适配度（是否符合{req.platform}风格）
5. 爆款评分（1-10分）及理由
6. 可借鉴的亮点"""
    user = f"请分析以下内容：\n\n{req.content}"
    result = call_ai(system, user)
    return {"result": result}


@app.post("/api/optimize")
async def optimize_content(req: OptimizeRequest):
    system = f"""你是一个{req.platform}内容优化专家。请针对内容的不足之处，给出具体的优化建议。
每个建议包含：问题描述、优化方案、优化前后对比。"""
    user = f"请优化以下内容：\n\n{req.content}\n\n已知问题：{req.issues or '待分析'}"
    result = call_ai(system, user)
    return {"result": result}


@app.post("/api/rewrite")
async def rewrite_content(req: RewriteRequest):
    system = f"""你是一个{req.platform}爆款文案写手。请根据原始内容，用指定风格重新撰写。
要求：保留核心信息，但用更吸引人的方式表达。"""
    user = f"原始内容：\n{req.content}\n\n目标风格：{req.style}\n\n请重新撰写。"
    result = call_ai(system, user)
    return {"result": result}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
