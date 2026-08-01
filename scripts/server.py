"""
后端 API 服务 - FastAPI 版
启动：python3 scripts/server.py
"""
import json
import os
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

ROOT = Path(__file__).parent.parent
DATA_FILE = ROOT / "data" / "transcripts.json"

app = FastAPI()

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

@app.get("/api/transcripts")
def get_transcripts():
    data = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    # 更新 stats
    data["meta"]["stats"]["videos"] = len(data["cards"])
    data["meta"]["stats"]["transcripts"] = sum(1 for c in data["cards"] if c.get("body") and c["body"] != "（该视频无音轨）")
    return data

@app.get("/api/health")
def health():
    return {"status": "ok", "cards": len(json.loads(DATA_FILE.read_text(encoding="utf-8"))["cards"])}

# 静态文件
app.mount("/", StaticFiles(directory=str(ROOT), html=True), name="static")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
