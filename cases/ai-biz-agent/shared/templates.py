"""
统一的 HTML 模板
所有项目使用相同的 UI 框架
"""


def get_base_css() -> str:
    """获取基础 CSS 样式"""
    return """
    * { margin: 0; padding: 0; box-sizing: border-box; }
    :root {
        --bg: #0a0a0a;
        --surface: #141414;
        --border: #222;
        --text: #e5e5e5;
        --text-secondary: #888;
        --accent: #3b82f6;
        --accent-hover: #2563eb;
        --success: #22c55e;
        --warning: #f59e0b;
        --error: #ef4444;
    }
    body {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        background: var(--bg);
        color: var(--text);
        line-height: 1.6;
    }
    .container { max-width: 900px; margin: 0 auto; padding: 2rem; }
    h1 { font-size: 2rem; margin-bottom: 0.5rem; }
    .subtitle { color: var(--text-secondary); margin-bottom: 2rem; }
    .section {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
    }
    .section h2 { margin-bottom: 1rem; }
    label {
        display: block;
        font-size: 0.9rem;
        color: var(--text-secondary);
        margin-bottom: 0.3rem;
    }
    input, select, textarea {
        width: 100%;
        padding: 0.8rem;
        background: #1a1a1a;
        border: 1px solid var(--border);
        border-radius: 8px;
        color: var(--text);
        font-size: 1rem;
        margin-bottom: 1rem;
        font-family: inherit;
    }
    textarea { min-height: 100px; resize: vertical; }
    button {
        padding: 0.8rem 2rem;
        background: var(--accent);
        color: white;
        border: none;
        border-radius: 8px;
        font-size: 1rem;
        cursor: pointer;
        transition: background 0.2s;
    }
    button:hover { background: var(--accent-hover); }
    button:disabled { opacity: 0.5; cursor: not-allowed; }
    .btn-secondary {
        background: transparent;
        border: 1px solid var(--border);
        color: var(--text);
    }
    .btn-secondary:hover { background: #1a1a1a; }
    .result {
        background: #1a1a1a;
        border: 1px solid var(--border);
        border-radius: 8px;
        padding: 1.5rem;
        margin-top: 1rem;
        white-space: pre-wrap;
        line-height: 1.8;
    }
    .loading { color: var(--text-secondary); font-style: italic; }
    .error { color: var(--error); }
    .success { color: var(--success); }
    .tabs { display: flex; gap: 0.5rem; margin-bottom: 1.5rem; flex-wrap: wrap; }
    .tab {
        padding: 0.5rem 1rem;
        background: #1a1a1a;
        border: 1px solid var(--border);
        border-radius: 8px;
        cursor: pointer;
        font-size: 0.9rem;
        color: var(--text-secondary);
    }
    .tab.active { background: var(--accent); border-color: var(--accent); color: white; }
    .tab-content { display: none; }
    .tab-content.active { display: block; }
    .badge {
        display: inline-block;
        padding: 0.2rem 0.6rem;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
    }
    .badge-success { background: rgba(34, 197, 94, 0.2); color: var(--success); }
    .badge-warning { background: rgba(245, 158, 11, 0.2); color: var(--warning); }
    .badge-error { background: rgba(239, 68, 68, 0.2); color: var(--error); }
    .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 1rem; margin-bottom: 2rem; }
    .stat {
        background: var(--surface);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 1.2rem;
        text-align: center;
    }
    .stat .num { font-size: 1.5rem; font-weight: 800; color: var(--accent); }
    .stat .label { font-size: 0.8rem; color: var(--text-secondary); margin-top: 0.3rem; }
    @media (max-width: 768px) {
        .container { padding: 1rem; }
        h1 { font-size: 1.5rem; }
        .stats { grid-template-columns: repeat(2, 1fr); }
    }
    """


def get_demo_script(demo_data: dict) -> str:
    """获取 Demo 自动填充脚本"""
    return f"""
    <script>
    // Demo 自动填充
    window.addEventListener('load', () => {{
        const demoData = {demo_data};
        Object.entries(demoData).forEach(([id, value]) => {{
            const el = document.getElementById(id);
            if (el) el.value = value;
        }});
        // 自动触发演示
        setTimeout(() => {{
            const demoBtn = document.getElementById('demo-btn');
            if (demoBtn) demoBtn.click();
        }}, 500);
    }});
    </script>
    """


def wrap_html(title: str, content: str, extra_css: str = "", extra_js: str = "") -> str:
    """包装 HTML 页面"""
    return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        {get_base_css()}
        {extra_css}
    </style>
</head>
<body>
    {content}
    {extra_js}
</body>
</html>"""
