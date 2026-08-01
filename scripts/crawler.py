"""
模型先生逐字稿自动爬虫
=========================
功能：
1. 读取 data/transcripts.json 获取已有数据
2. 从抖音「模型先生」抓取新视频的逐字稿
3. 增量追加到 JSON 文件

抖音爬取策略（按优先级）：
- 方式1: 通过抖音网页版用户主页 API 获取视频列表，再逐个获取字幕
- 方式2: 使用 Playwright 模拟浏览器访问
- 方式3: 手动补充数据（从 data/manual_entries.json 读取）

输出：
- 更新 data/transcripts.json（增量追加，不覆盖已有数据）
- 打印新增条目数量
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

# ==================== 配置 ====================
DATA_DIR = Path(__file__).parent.parent / "data"
TRANSCRIPTS_FILE = DATA_DIR / "transcripts.json"
MANUAL_FILE = DATA_DIR / "manual_entries.json"  # 手动补充的数据

# 抖音博主标识
DOUYIN_USER_ID = "模型先生"  # 抖音用户ID或sec_uid

# ==================== 工具函数 ====================
def load_json(path: Path) -> dict:
    """安全加载 JSON"""
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(data: dict, path: Path):
    """安全保存 JSON"""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)  # 原子替换

def get_existing_ids(data: dict) -> set:
    """获取已有视频ID集合"""
    return {card["id"] for card in data.get("cards", [])}

def generate_id(publish_time: datetime) -> str:
    """根据发布时间生成唯一ID"""
    return publish_time.strftime("%Y%m%d-%H%M%S")

def parse_duration(duration_text: str) -> str:
    """标准化时长格式"""
    duration_text = duration_text.strip()
    if not duration_text.endswith("s"):
        # 尝试解析纯秒数
        try:
            seconds = int(duration_text)
            return f"{seconds}s"
        except ValueError:
            pass
    return duration_text


# ==================== 爬取策略1: 抖音网页版API ====================
def fetch_douyin_web_api() -> list[dict]:
    """
    通过抖音网页版 API 获取模型先生的视频列表。
    注意：此方法依赖抖音的公开接口，可能随时失效。
    返回格式：[{id, date, duration, tags, body, marketDate, market}]
    """
    import requests

    new_cards = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
        "Referer": "https://www.douyin.com/",
        "Accept": "application/json, text/plain, */*",
    }

    try:
        # Step 1: 获取用户 sec_uid（如果只知道用户名）
        # 通过搜索接口获取
        search_url = f"https://www.douyin.com/aweme/v1/web/discover/search/"
        # 实际使用时需要完整的 API 调用链，这里仅作示意
        print("[API] 抖音网页版API需要完整的cookie和签名，建议使用Playwright方案")
        print("[API] 跳过API方式，使用手动/Playwright方式")

    except Exception as e:
        print(f"[API] 请求失败: {e}")

    return new_cards


# ==================== 爬取策略2: Playwright 浏览器自动化 ====================
def fetch_douyin_playwright() -> list[dict]:
    """
    使用 Playwright 模拟浏览器访问抖音。
    需要安装: pip install playwright && playwright install chromium
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[Playwright] playwright 未安装，跳过")
        return []

    new_cards = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
        )
        page = context.new_page()

        try:
            # 访问抖音用户主页（需要知道用户的 sec_uid）
            # 示例：https://www.douyin.com/user/<sec_uid>
            # 实际使用时需要先通过搜索获取 sec_uid
            print("[Playwright] 请配置用户的 sec_uid 或搜索逻辑")
            print("[Playwright] 示例: page.goto('https://www.douyin.com/user/MS4wLjABAAAA...')")

            # 等待视频列表加载
            # page.wait_for_selector('[data-e2e="user-post-list"]', timeout=15000)

            # 提取视频列表
            # videos = page.evaluate("""() => {
            #     const items = document.querySelectorAll('[data-e2e="user-post-item"]');
            #     return Array.from(items).map(item => ({
            #         title: item.querySelector('.title')?.textContent || '',
            #         link: item.querySelector('a')?.href || '',
            #     }));
            # }""")

            # 逐个访问视频页面提取字幕
            # for video in videos:
            #     page.goto(video['link'])
            #     page.wait_for_timeout(3000)
            #     subtitle = page.evaluate("""() => {
            #         const el = document.querySelector('.subtitle-text');
            #         return el ? el.textContent : '';
            #     }""")
            #     ...

            print("[Playwright] 爬取逻辑需要根据实际抖音页面结构调整")

        except Exception as e:
            print(f"[Playwright] 爬取出错: {e}")
        finally:
            browser.close()

    return new_cards


# ==================== 爬取策略3: 手动数据导入 ====================
def import_manual_entries() -> list[dict]:
    """
    从 data/manual_entries.json 读取手动添加的数据。
    适用于无法自动爬取时，用户手动粘贴逐字稿。
    
    manual_entries.json 格式：
    [
      {
        "date": "2026/8/1 15:30:00 周五",
        "duration": "45s",
        "tags": ["科技股", "市场判断"],
        "body": "逐字稿内容...",
        "marketDate": "2026-08-01（交易日）",
        "market": {
          "上证指数": [4000.00, 0.50],
          "深成指": [15000.00, 0.80],
          "创业板指": [3900.00, 1.20],
          "科创50": [2000.00, 0.30]
        }
      }
    ]
    """
    data = load_json(MANUAL_FILE)
    entries = data if isinstance(data, list) else data.get("entries", [])

    new_cards = []
    for entry in entries:
        # 生成 ID
        dt = datetime.strptime(entry["date"].split(" ")[0], "%Y/%m/%d")
        entry_time = datetime.strptime(
            entry["date"].split(" ")[1], "%H:%M:%S"
        )
        dt = dt.replace(hour=entry_time.hour, minute=entry_time.minute, second=entry_time.second)
        entry["id"] = generate_id(dt)
        entry["duration"] = parse_duration(entry.get("duration", "0s"))
        new_cards.append(entry)

    return new_cards


# ==================== 主流程 ====================
def main():
    print("=" * 60)
    print(f"模型先生逐字稿爬虫 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 加载现有数据
    existing = load_json(TRANSCRIPTS_FILE)
    existing_ids = get_existing_ids(existing)
    print(f"现有数据: {len(existing_ids)} 条逐字稿")

    # 收集新数据（按优先级尝试）
    all_new_cards = []

    # 策略3: 手动数据（最可靠，优先处理）
    if MANUAL_FILE.exists():
        manual_cards = import_manual_entries()
        print(f"手动数据: {len(manual_cards)} 条")
        all_new_cards.extend(manual_cards)

    # 策略1: API（如果配置了）
    api_cards = fetch_douyin_web_api()
    if api_cards:
        print(f"API数据: {len(api_cards)} 条")
        all_new_cards.extend(api_cards)

    # 策略2: Playwright（备选）
    playwright_cards = fetch_douyin_playwright()
    if playwright_cards:
        print(f"Playwright数据: {len(playwright_cards)} 条")
        all_new_cards.extend(playwright_cards)

    # 去重 + 排序
    seen = set()
    unique_new = []
    for card in all_new_cards:
        cid = card.get("id", "")
        if cid and cid not in existing_ids and cid not in seen:
            seen.add(cid)
            unique_new.append(card)

    # 按日期排序（新在前）
    unique_new.sort(key=lambda c: c.get("id", ""), reverse=True)

    if not unique_new:
        print("\n没有新数据，无需更新")
        return 0

    # 合并到现有数据
    existing["cards"] = unique_new + existing.get("cards", [])
    existing["meta"]["stats"]["videos"] = len(existing["cards"])
    existing["meta"]["stats"]["transcripts"] = sum(1 for c in existing["cards"] if c.get("body") and c["body"] != "（该视频无音轨）")
    existing["meta"]["last_updated"] = datetime.now(timezone(timedelta(hours=8))).isoformat()

    # 更新覆盖时段
    dates = [c.get("id", "")[:8] for c in existing["cards"] if c.get("id")]
    if dates:
        existing["meta"]["period"] = f"{min(dates)[:4]}/{min(dates)[4:6]}/{min(dates)[6:8]} ~ {max(dates)[:4]}/{max(dates)[4:6]}/{max(dates)[6:8]}"

    # 保存
    save_json(existing, TRANSCRIPTS_FILE)
    print(f"\n✅ 更新完成: 新增 {len(unique_new)} 条，总计 {len(existing['cards'])} 条")
    for card in unique_new:
        print(f"  + {card['date']} ({card.get('duration','?')}) - {', '.join(card.get('tags',[]))}")

    # 清空手动数据（已导入）
    if MANUAL_FILE.exists():
        MANUAL_FILE.unlink()
        print(f"  已清除 {MANUAL_FILE}")

    # 自动重新构建 app.html
    if unique_new:
        print("\n🔨 重新构建 app.html...")
        import subprocess
        result = subprocess.run(
            [sys.executable, str(Path(__file__).parent / "build.py")],
            capture_output=True, text=True
        )
        print(result.stdout.strip())
        if result.returncode != 0:
            print(f"⚠️ 构建失败: {result.stderr}")

    return len(unique_new)


if __name__ == "__main__":
    sys.exit(main())
