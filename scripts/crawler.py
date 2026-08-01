"""
模型先生逐字稿自动爬虫
=========================
功能：
1. 读取 data/transcripts.json 获取已有数据
2. 通过 Playwright 访问抖音「模型先生」主页，抓取最新视频
3. 提取视频文案/字幕/章节要点
4. 增量追加到 JSON 文件并重新生成 app.html

策略：
- 方式1: Playwright 爬取抖音用户主页视频列表
- 方式2: 手动补充数据（从 data/manual_entries.json 读取）
"""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ==================== 配置 ====================
DATA_DIR = Path(__file__).parent.parent / "data"
TRANSCRIPTS_FILE = DATA_DIR / "transcripts.json"
MANUAL_FILE = DATA_DIR / "manual_entries.json"

# 模型先生的抖音 sec_uid（从搜索结果获取）
DOUYIN_USER_URL = "https://www.douyin.com/user/MS4wLjABAAAAK713M9d8PGNb_WiMYf7yKhOI5y60H4uELJK2guDjJT0"

# ==================== 工具函数 ====================
def load_json(path: Path) -> dict:
    if path.exists():
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_json(data: dict, path: Path):
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    tmp.replace(path)

def get_existing_ids(data: dict) -> set:
    return {card["id"] for card in data.get("cards", [])}

def generate_id(date_str: str) -> str:
    """从日期字符串生成ID"""
    # 尝试解析各种日期格式
    for fmt in ["%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M:%S"]:
        try:
            dt = datetime.strptime(date_str.split(" 周")[0].strip(), fmt)
            return dt.strftime("%Y%m%d-%H%M%S")
        except ValueError:
            continue
    # 如果解析失败，用时间戳
    return datetime.now().strftime("%Y%m%d-%H%M%S")


# ==================== 爬取策略1: Playwright ====================
def fetch_douyin_playwright() -> list[dict]:
    """使用 Playwright 爬取抖音用户主页最新视频"""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("[Playwright] 未安装，跳过自动爬取")
        print("[Playwright] 安装方法: pip install playwright && playwright install chromium")
        return []

    new_cards = []
    
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 720},
        )
        page = context.new_page()

        try:
            print(f"[Playwright] 访问用户主页: {DOUYIN_USER_URL}")
            page.goto(DOUYIN_USER_URL, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(5000)

            # 获取视频列表
            videos = page.evaluate("""() => {
                const items = document.querySelectorAll('a[href*="/video/"]');
                const results = [];
                const seen = new Set();
                for (const item of items) {
                    const href = item.href;
                    if (href.includes('/video/') && !seen.has(href)) {
                        seen.add(href);
                        const titleEl = item.querySelector('p, span, div');
                        results.push({
                            url: href,
                            title: titleEl ? titleEl.textContent.trim() : ''
                        });
                    }
                }
                return results.slice(0, 5);  // 只取最新5个
            }""")
            
            print(f"[Playwright] 发现 {len(videos)} 个视频")

            # 获取已有数据中的最新日期
            existing = load_json(TRANSCRIPTS_FILE)
            existing_ids = get_existing_ids(existing)
            
            for i, video in enumerate(videos):
                video_url = video['url']
                # 从URL提取视频ID
                vid_match = re.search(r'/video/(\d+)', video_url)
                if not vid_match:
                    continue
                video_id = vid_match.group(1)
                
                # 用视频ID做去重检查（取后10位作为日期近似）
                # 我们需要访问视频页面才能获取发布时间
                print(f"[Playwright] 访问视频 {i+1}/{len(videos)}: {video_url}")
                
                try:
                    page.goto(video_url, wait_until="domcontentloaded", timeout=30000)
                    page.wait_for_timeout(3000)
                    
                    # 提取页面文字
                    text = page.evaluate("() => document.body.innerText")
                    title = page.title()
                    
                    # 提取发布时间
                    date_match = re.search(r'发布时间[：:]\s*(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})', text)
                    if not date_match:
                        date_match = re.search(r'(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2})', text)
                    
                    if not date_match:
                        print(f"  无法提取发布时间，跳过")
                        continue
                    
                    pub_date_str = date_match.group(1)
                    pub_dt = datetime.strptime(pub_date_str, "%Y-%m-%d %H:%M")
                    card_id = pub_dt.strftime("%Y%m%d-%H%M%S")
                    
                    if card_id in existing_ids:
                        print(f"  已存在 {card_id}，跳过")
                        continue
                    
                    # 提取时长
                    duration_match = re.search(r'(\d{2}:\d{2})\s*/\s*(\d{2}:\d{2})', text)
                    duration = "0s"
                    if duration_match:
                        time_str = duration_match.group(2)
                        parts = time_str.split(":")
                        if len(parts) == 2:
                            duration = f"{int(parts[0])*60 + int(parts[1])}s"
                    
                    # 提取章节要点（AI生成的内容）
                    chapters = []
                    chapter_match = re.search(r'章节要点\s*(.*?)(?:\d{1,2}:\d{2}\n|$)', text, re.DOTALL)
                    
                    # 提取描述文字
                    desc_match = re.search(r'章节要点\n(.*?)\d{2}:\d{2}', text, re.DOTALL)
                    if desc_match:
                        desc = desc_match.group(1).strip()
                    else:
                        # 尝试提取视频描述
                        desc_lines = []
                        for line in text.split('\n'):
                            line = line.strip()
                            if line and not any(skip in line for skip in [
                                '抖音', '登录', '搜索', '充钻石', '客户端', '通知', '消息',
                                '投稿', '精选', '推荐', '关注', '朋友', '直播', '放映厅',
                                '短剧', '小游戏', '读屏', '打开声音', '倍速', '智能',
                                '清屏', '连播', '理财有风险', '举报', '发布时间',
                                '全部评论', '请先登录', '大家都在搜', '暂无评论',
                                '粉丝', '获赞', '推荐视频', '广告投放', '用户服务',
                                '隐私政策', '账号找回', '加入我们', '营业执照',
                                '友情链接', '站点地图', '下载抖音', '抖音电商',
                                '网络谣言', '违法和不良', '算法推荐', '体育饭圈',
                                '京ICP', '广播电视', '增值电信', '网络文化',
                                '京公网', '互联网宗教', '热门', '内容由AI生成',
                                '抢首评', '点赞', '收藏', '转发', '分享'
                            ]):
                                if len(line) > 10 and len(line) < 500:
                                    desc_lines.append(line)
                        desc = '\n'.join(desc_lines[:3]) if desc_lines else video.get('title', '')
                    
                    # 提取标签
                    tags = []
                    for tag_match in re.finditer(r'#([\u4e00-\u9fa5\w]+)', text):
                        tag = tag_match.group(1)
                        if tag not in tags and len(tag) < 10:
                            tags.append(tag)
                    if not tags:
                        tags = ["市场判断"]
                    tags = tags[:4]
                    
                    # 提取点赞数
                    likes_match = re.search(r'(\d+\.?\d*万?)\s*抢首评', text)
                    likes = likes_match.group(1) if likes_match else ""
                    
                    card = {
                        "id": card_id,
                        "date": f"{pub_dt.year}/{pub_dt.month}/{pub_dt.day} {pub_dt.strftime('%H:%M')} " + 
                                ["周一","周二","周三","周四","周五","周六","周日"][pub_dt.weekday()],
                        "duration": duration,
                        "tags": tags,
                        "body": desc[:1000],
                        "marketDate": f"{pub_dt.strftime('%Y-%m-%d')}（交易日）",
                        "market": {
                            "上证指数": [0, 0],
                            "深成指": [0, 0],
                            "创业板指": [0, 0],
                            "科创50": [0, 0]
                        },
                        "source_url": video_url,
                    }
                    
                    if likes:
                        card["stats"] = {"likes": likes}
                    
                    new_cards.append(card)
                    print(f"  ✅ 新视频: {card_id} - {desc[:50]}...")
                    
                except Exception as e:
                    print(f"  ❌ 访问视频失败: {e}")
                    continue
                
                # 避免频繁访问
                time.sleep(2)

        except Exception as e:
            print(f"[Playwright] 爬取出错: {e}")
        finally:
            browser.close()

    return new_cards


# ==================== 爬取策略2: 手动数据导入 ====================
def import_manual_entries() -> list[dict]:
    """从 data/manual_entries.json 读取手动添加的数据"""
    data = load_json(MANUAL_FILE)
    entries = data if isinstance(data, list) else data.get("entries", [])

    new_cards = []
    for entry in entries:
        date_str = entry["date"].split(" 周")[0].strip()
        for fmt in ["%Y/%m/%d %H:%M:%S", "%Y/%m/%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M"]:
            try:
                dt = datetime.strptime(date_str, fmt)
                entry["id"] = dt.strftime("%Y%m%d-%H%M%S")
                break
            except ValueError:
                continue
        if "id" not in entry:
            entry["id"] = datetime.now().strftime("%Y%m%d-%H%M%S")
        entry["duration"] = entry.get("duration", "0s")
        new_cards.append(entry)

    return new_cards


# ==================== 主流程 ====================
def main():
    print("=" * 60)
    print(f"模型先生逐字稿爬虫 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    # 切换到仓库根目录
    os.chdir(Path(__file__).parent.parent)

    existing = load_json(TRANSCRIPTS_FILE)
    existing_ids = get_existing_ids(existing)
    print(f"现有数据: {len(existing_ids)} 条逐字稿")

    all_new_cards = []

    # 策略2: 手动数据（最可靠，优先处理）
    if MANUAL_FILE.exists():
        manual_cards = import_manual_entries()
        print(f"手动数据: {len(manual_cards)} 条")
        all_new_cards.extend(manual_cards)

    # 策略1: Playwright 自动爬取
    playwright_cards = fetch_douyin_playwright()
    if playwright_cards:
        print(f"Playwright数据: {len(playwright_cards)} 条")
        all_new_cards.extend(playwright_cards)

    # 去重
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
    existing["meta"]["stats"]["transcripts"] = sum(
        1 for c in existing["cards"] if c.get("body") and c["body"] != "（该视频无音轨）"
    )
    existing["meta"]["last_updated"] = datetime.now(
        timezone(timedelta(hours=8))
    ).isoformat()

    # 更新覆盖时段
    dates = [c.get("id", "")[:8] for c in existing["cards"] if c.get("id")]
    if dates:
        min_d, max_d = min(dates), max(dates)
        existing["meta"]["period"] = (
            f"{min_d[:4]}/{min_d[4:6]}/{min_d[6:8]} ~ "
            f"{max_d[:4]}/{max_d[4:6]}/{max_d[6:8]}"
        )

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
            [sys.executable, str(Path(__file__).parent / "build_static.py")],
            capture_output=True, text=True
        )
        print(result.stdout.strip())
        if result.returncode != 0:
            print(f"⚠️ 构建失败: {result.stderr}")

    return len(unique_new)


if __name__ == "__main__":
    sys.exit(main())
