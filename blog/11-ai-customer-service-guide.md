# AI客服搭建指南：从0到1只需要3步

> 发布日期：2026-06-12
> 系列：教程

---

## 第一步：准备FAQ

把你的常见问题和答案整理成一个列表：

```
Q: 发货时间？
A: 拍下后48小时内发货，顺丰包邮。

Q: 支持退换货吗？
A: 7天无理由退换，运费我们承担。

Q: 有优惠券吗？
A: 关注店铺领取5元无门槛券。
```

问题越多越好，至少20个。

## 第二步：搭建AI

用FastAPI + OpenAI API搭建后端：

```python
from openai import OpenAI

client = OpenAI(api_key="your-key")

def answer(question, faq):
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": f"你是客服，根据FAQ回答问题。\nFAQ:\n{faq}"},
            {"role": "user", "content": question}
        ]
    )
    return response.choices[0].message.content
```

## 第三步：部署

部署到Render（免费）：

1. 推送代码到GitHub
2. 连接Render
3. 设置环境变量（OPENAI_API_KEY）
4. 部署完成

## 总结

3步就能搭建一个AI客服。不会编程？找我帮你做，99元起。
