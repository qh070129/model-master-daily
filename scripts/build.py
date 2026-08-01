"""
一键构建脚本：读取 transcripts.json → 内嵌到 HTML → 输出 app.html
用法：python3 scripts/build.py
"""
import json
from pathlib import Path

ROOT = Path(__file__).parent.parent
DATA_FILE = ROOT / "data" / "transcripts.json"
TEMPLATE_FILE = ROOT / "index_template.html"
OUTPUT_FILE = ROOT / "app.html"

data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
json_str = json.dumps(data, ensure_ascii=False)

template = TEMPLATE_FILE.read_text(encoding="utf-8")
html = template.replace("__DATA_PLACEHOLDER__", json_str)

OUTPUT_FILE.write_text(html, encoding="utf-8")
print(f"✅ Built {OUTPUT_FILE} ({len(html)} bytes, {len(data['cards'])} cards)")
