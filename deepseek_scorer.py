#!/usr/bin/env python3
"""
DeepSeek 精细化评分模块（Phase 2）
====================================
替代关键词规则评分，用 DeepSeek 对产品进行5维评估。
支持 Playwright 提取页面内容（可选）和纯文本模式。
集成到 accumulate.py 中使用。

用法:
  python3 deepseek_scorer.py < items.json          # 从stdin读入
  python3 deepseek_scorer.py items.json             # 从文件读入
  python3 deepseek_scorer.py --items '[{...}]'      # 从参数读入

环境变量:
  DEEPSEEK_API_KEY  必需, DeepSeek API key
  PLAYWRIGHT_LOAD   设为 "0" 跳过 Playwright 页面加载（纯文本模式）

输入格式: JSON 数组，每项含 title, description, category, url
输出格式: 每项增加 _deepseek 字段包含评分结果
"""

import json, os, sys, time, ssl, urllib.request, urllib.error
from typing import Optional, Dict, Any, List

DEEPSEEK_API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

# 宽松 SSL 上下文
_CTX = ssl.create_default_context()
_CTX.check_hostname = False
_CTX.verify_mode = ssl.CERT_NONE

# DeepSeek API 配置
DEEPSEEK_API_URL = "https://api.deepseek.com/v1/chat/completions"
MODEL = "deepseek-chat"  # 标准对话模型，快且便宜

# 每批处理的并发数（DeepSeek API 没有严格限制，但别太快）
BATCH_SIZE = 5
# 两次 API 调用间隔（秒）— 避免速率限制
API_DELAY = 0.5
# 单次评分超时（秒）
REQUEST_TIMEOUT = 30


# ─── 评分模板 ─────────────────────────────────────

SYSTEM_PROMPT = """You are a professional product curator. Your job is to score products on 5 key dimensions for a Chinese design discovery platform.

Score each dimension from 0-10:
- 直观度 (Intuitiveness): Can people understand what this product is and how it works within 3 seconds?
- 打击面 (Mass Appeal): How broad is the target audience? Does it appeal to many different demographics?
- 实用性 (Practicality): How useful is it in everyday life? Does it solve a real, common problem?
- 创意价值 (Creativity): How innovative or delightful is the design? Does it have a "Wow!" factor?
- 情绪价值 (Emotional Value): Does it create emotional resonance — warmth, joy, nostalgia, surprise?

Rules:
- Be critical but fair. A good everyday product scores 7-8 on 实用性, even if it's simple.
- 打击面 should be higher for everyday items (cups, bags, lamps) and lower for niche products.
- 情绪价值 is about emotional design, not just aesthetics. A beautiful but cold object scores lower.
- Return ONLY valid JSON, no explanation."""

USER_PROMPT_TEMPLATE = None  # 在运行时动态构建


def _call_deepseek(prompt: str, retries: int = 2) -> Optional[Dict[str, int]]:
    """调用 DeepSeek API 评分，返回解析后的 JSON"""
    if not DEEPSEEK_API_KEY:
        print("  ❌ DEEPSEEK_API_KEY 未设置", file=sys.stderr)
        return None
    
    payload = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.1,        # 低温度保持一致性
        "max_tokens": 200,          # 回复很短，只要JSON
        "stream": False,
    }).encode("utf-8")
    
    req = urllib.request.Request(
        DEEPSEEK_API_URL,
        data=payload,
        headers={
            "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    
    for attempt in range(retries + 1):
        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT, context=_CTX) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, 
                json.JSONDecodeError, TimeoutError) as e:
            if attempt < retries:
                wait = 2 ** attempt
                print(f"  ⚠️  API 请求失败: {e} (重试 {attempt+1}/{retries} 在 {wait}s 后)", file=sys.stderr)
                time.sleep(wait)
                continue
            print(f"  ❌ API 请求最终失败: {e}", file=sys.stderr)
            return None
        
        # 提取回复内容
        try:
            content = data["choices"][0]["message"]["content"].strip()
            # 去掉可能的 ```json ``` 包裹
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]
            content = content.strip()
            result = json.loads(content)
            # 校验维度完整性
            required = {"intuitive", "broad_appeal", "usefulness", "creativity", "emotional"}
            if not required.issubset(result.keys()):
                print(f"  ⚠️  API 返回缺失维度: {set(result.keys()) - required}", file=sys.stderr)
                return None
            return result
        except (KeyError, IndexError, json.JSONDecodeError) as e:
            if attempt < retries:
                time.sleep(2 ** attempt)
                continue
            print(f"  ❌ 解析响应失败: {e}", file=sys.stderr)
            return None
    
    return None


def _playwright_load_page(url: str, timeout_ms: int = 10000) -> Optional[str]:
    """用 Playwright 加载页面提取文本内容（可选步骤）"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return None
    
    if os.environ.get("PLAYWRIGHT_LOAD") == "0":
        return None
    
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            ctx = browser.new_context(
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                           "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                viewport={"width": 1280, "height": 800},
            )
            page = ctx.new_page()
            try:
                page.goto(url, timeout=timeout_ms, wait_until="domcontentloaded")
                # 等待内容加载
                page.wait_for_timeout(2000)
                # 提取可见文本（正文内容，去除导航/页脚噪音）
                text = page.evaluate("""() => {
                    // 优先从 article/main 提取
                    const main = document.querySelector('article, main, .content, .description')
                    if (main) return main.innerText.slice(0, 3000)
                    // 没有则拿 body 文本（尽量干净）
                    const body = document.body
                    if (!body) return ''
                    const clone = body.cloneNode(true)
                    // 移除脚本/样式/导航/页脚
                    clone.querySelectorAll('script, style, nav, footer, header, .sidebar, .menu').forEach(el => el.remove())
                    return (clone.innerText || '').slice(0, 3000)
                }""")
                browser.close()
                return text.strip() if text else None
            except Exception as e:
                print(f"  ⚠️ Playwright 加载失败 {url}: {e}", file=sys.stderr)
                browser.close()
                return None
    except Exception as e:
        print(f"  ⚠️ Playwright 启动失败: {e}", file=sys.stderr)
        return None


def score_item(title: str, description: str = "", category: str = "",
               url: str = "", use_playwright: bool = True) -> Dict[str, Any]:
    """对单个产品进行 DeepSeek 评分
    
    流程:
      1. 可选：Playwright 加载页面提取丰富内容
      2. 调用 DeepSeek API 进行5维评分
      3. 解析 JSON 返回
    
    返回:
      {
        "intuitive": 0-10,
        "broad_appeal": 0-10,
        "usefulness": 0-10,
        "creativity": 0-10,
        "emotional": 0-10,
        "total": 总分,
        "source": "deepseek"
      }
      失败时返回 None
    """
    # 1. 尝试 Playwright 加载页面
    page_text = None
    if use_playwright and url and not url.startswith("http"):
        pass  # 非 HTTP URL 不加载
    elif use_playwright and url and url.startswith("http"):
        page_text = _playwright_load_page(url)
    
    # 2. 构建 prompt
    page_section = ""
    if page_text:
        # 截取前 1500 字
        truncated = page_text[:1500]
        page_section = f"Page Content:\n{truncated}\n"
    
    schema_str = json.dumps({"intuitive": 0, "broad_appeal": 0, "usefulness": 0, "creativity": 0, "emotional": 0})
    prompt = f"Score this product:\n\nTitle: {title}\nDescription: {description}\nCategory: {category}\n{page_section}\nReturn ONLY this exact JSON (no explanation): {schema_str}"
    
    # 3. 调用 API
    result = _call_deepseek(prompt)
    if not result:
        return None
    
    # 钳制到 0-10
    for k in result:
        result[k] = max(0, min(10, int(result[k])))
    
    result["total"] = sum(result[d] for d in ["intuitive", "broad_appeal", "usefulness", "creativity", "emotional"])
    result["source"] = "deepseek"
    
    return result


# ─── 批量评分 ─────────────────────────────────────

def score_batch(items: List[Dict], use_playwright: bool = True,
                report_every: int = 10) -> List[Dict]:
    """批量评分，逐项调用 DeepSeek API
    
    返回: 更新了 _deepseek 字段的 items 列表
    """
    total = len(items)
    success = 0
    failed = 0
    
    print(f"\n🔮 DeepSeek 精细化评分")
    print(f"   项数: {total}")
    print(f"   Playwright: {'开启' if use_playwright else '关闭'}")
    print()
    
    for i, item in enumerate(items):
        title = item.get("title", "")
        desc = item.get("description", "") or item.get("reason", "") or ""
        cat = item.get("category", "")
        url = item.get("url", "")
        
        result = score_item(title, desc, cat, url, use_playwright)
        
        if result:
            item["_deepseek"] = result
            item["_score_total"] = result["total"]
            # 更新单项评分
            labels = {"intuitive": "直观度", "broad_appeal": "打击面",
                      "usefulness": "实用性", "creativity": "创意价值",
                      "emotional": "情绪价值"}
            item["_scores"] = {labels[k]: result[k] for k in ["intuitive", "broad_appeal", "usefulness", "creativity", "emotional"]}
            item["score"] = round(result["total"] / 5, 1)
            success += 1
        else:
            failed += 1
        
        if (i + 1) % report_every == 0 or i == total - 1:
            print(f"  📊 进度: {i+1}/{total} | ✅ {success} | ❌ {failed}")
        
        if i < total - 1:
            time.sleep(API_DELAY)
    
    print(f"\n   ✅ DeepSeek 评分完成: {success}/{total} 成功")
    if failed:
        print(f"   ⚠️  {failed} 项使用关键词评分（回退）")
    
    return items


def main():
    """CLI 入口：从 stdin 或文件读 JSON，输出 DeepSeek 评分结果"""
    if not DEEPSEEK_API_KEY:
        print("❌ DEEPSEEK_API_KEY 环境变量未设置", file=sys.stderr)
        sys.exit(1)
    
    # 读取输入
    input_data = None
    if not sys.stdin.isatty():
        input_data = sys.stdin.read()
    elif len(sys.argv) > 1 and not sys.argv[1].startswith("--"):
        with open(sys.argv[1], "r") as f:
            input_data = f.read()
    elif "--items" in sys.argv:
        idx = sys.argv.index("--items")
        input_data = sys.argv[idx + 1]
    
    if not input_data:
        print("📖 用法: python3 deepseek_scorer.py < items.json", file=sys.stderr)
        print("        python3 deepseek_scorer.py items.json", file=sys.stderr)
        sys.exit(1)
    
    items = json.loads(input_data)
    if not isinstance(items, list):
        items = [items]
    
    print(f"📥 读取 {len(items)} 个产品")
    
    use_playwright = os.environ.get("PLAYWRIGHT_LOAD") != "0"
    
    result = score_batch(items, use_playwright)
    
    # 输出
    print(f"\n{'='*40}")
    print(f"📊 评分结果:")
    for item in result[:5]:  # 显示前5个
        ds = item.get("_deepseek", {})
        t = ds.get("total", 0)
        tag = "⭐" if t >= 45 else ("👍" if t >= 40 else "✅" if t >= 35 else "👀" if t >= 27 else "❌")
        print(f"  {tag} {item.get('title','')[:50]}")
        print(f"     总分: {t}/50 | 直观度:{ds.get('intuitive','?')} 打击面:{ds.get('broad_appeal','?')} 实用性:{ds.get('usefulness','?')} 创意:{ds.get('creativity','?')} 情绪:{ds.get('emotional','?')}")
    
    # 输出完整 JSON 到 stdout
    print(f"\n---FULL JSON---")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print("---END JSON---")


if __name__ == "__main__":
    main()
