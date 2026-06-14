# 网站SEO优化方案

---

## 已完成的SEO

- 标题标签：每个页面有独立的title
- 描述标签：每个页面有meta description
- 语义化HTML：使用nav、section、footer等语义标签
- 移动端适配：响应式设计

## 需要补充的SEO

### 1. sitemap.xml

```xml
<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
  <url><loc>https://yourusername.github.io/portfolio/</loc></url>
  <url><loc>https://yourusername.github.io/portfolio/blog.html</loc></url>
  <url><loc>https://yourusername.github.io/portfolio/service-basic.html</loc></url>
  <url><loc>https://yourusername.github.io/portfolio/service-standard.html</loc></url>
  <url><loc>https://yourusername.github.io/portfolio/service-premium.html</loc></url>
</urlset>
```

### 2. robots.txt

```
User-agent: *
Allow: /
Sitemap: https://yourusername.github.io/portfolio/sitemap.xml
```

### 3. Open Graph标签

每个页面添加：

```html
<meta property="og:title" content="页面标题" />
<meta property="og:description" content="页面描述" />
<meta property="og:image" content="截图URL" />
<meta property="og:url" content="页面URL" />
```

### 4. 关键词策略

| 页面   | 目标关键词                       |
| ------ | -------------------------------- |
| 首页   | AI工作室、AI定制开发、AI工具定制 |
| 服务页 | AI客服机器人、AI自动化、AI知识库 |
| 博客页 | AI工具、AI教程、AI案例           |
| 案例页 | AI自媒体助手、AI内容分析器       |

### 5. 内容SEO

- 每篇文章800-1500字
- 标题包含目标关键词
- 正文自然使用关键词
- 使用H1-H3标签
- 图片添加alt属性

## 部署后操作

1. 提交sitemap到Google Search Console
2. 提交sitemap到百度站长平台
3. 在社交媒体分享网站链接
4. 定期更新博客内容
