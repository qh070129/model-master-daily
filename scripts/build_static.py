"""生成纯静态HTML - Python直接渲染所有内容，零JS"""
import json, os, sys

# 切换到脚本所在目录的上级目录（仓库根目录）
os.chdir(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

with open('data/transcripts.json') as f:
    D = json.load(f)

def esc(s):
    """安全转义HTML"""
    return s.replace('&','&amp;').replace('<','&lt;').replace('>','&gt;').replace('"','&quot;')

cards = []
for c in D['cards']:
    tags = ''.join(f'<span class="ct">{esc(t)}</span>' for t in c['tags'])
    market = ''.join(
        f'<div class="mi"><div class="mn">{esc(k)}</div><div class="mv">{v[0]:.2f}</div><div class="mc {"up" if v[1]>=0 else "down"}">{"+" if v[1]>=0 else ""}{v[1]:.2f}%</div></div>'
        for k,v in c['market'].items()
    )
    comments = ''
    if c.get('comments'):
        items = []
        for cm in c['comments']:
            is_auth = cm.get('is_author')
            badge = '<span class="cba">作者</span>' if is_auth else ''
            avatar_cls = 'author' if is_auth else 'user'
            avatar_bg = 'linear-gradient(135deg,#f093fb,#f5576c)' if is_auth else 'linear-gradient(135deg,#667eea,#764ba2)'
            items.append(
                f'<div class="cm"><div class="ca {avatar_cls}" style="background:{avatar_bg}">{esc(cm["user"][0])}</div>'
                f'<div class="cb"><div class="ch2"><span class="cu">{esc(cm["user"])}</span>{badge}</div>'
                f'<div class="ct2">{esc(cm["text"])}</div>'
                f'<div class="cf">👍 {cm["likes"]}</div></div></div>'
            )
        comments = (
            f'<details class="cs"><summary class="ctb">💬 精选评论 ({len(c["comments"])})</summary>'
            f'<div class="cl2">{"".join(items)}</div></details>'
        )
    cards.append(
        f'<div class="card"><div class="chd"><span class="cd">{esc(c["date"])}</span>'
        f'<span class="cdr">{esc(c["duration"])}</span><span class="ctg">{tags}</span></div>'
        f'<div class="cbd">{esc(c["body"])}</div>'
        f'<div class="cf2"><div class="cmd">{esc(c["marketDate"])}</div><div class="cmk">{market}</div></div>'
        f'{comments}</div>'
    )

methods = []
for m in D['methods']:
    methods.append(
        f'<div class="mc2"><div class="mn2">{esc(m["num"])}</div><div class="mb2">'
        f'<h3>{esc(m["title"])}</h3><div class="mq">{esc(m["quote"])}</div>'
        f'<div class="md">{esc(m["desc"])}</div></div></div>'
    )

reviews = []
for r in D['reviews']:
    reviews.append(
        f'<div class="rc"><div class="rd">{esc(r["date"])}</div><div class="rb">'
        f'<div class="rp">{esc(r["predict"])}</div><div class="ra">{esc(r["actual"])}</div>'
        f'<span class="rr {r["cls"]}">{esc(r["result"])}</span></div></div>'
    )

html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1,maximum-scale=1">
<title>模型先生 · 逐字稿精华</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:-apple-system,BlinkMacSystemFont,"PingFang SC","Microsoft YaHei",sans-serif;background:#f8f9fa;color:#1a1a2e;line-height:1.7}}
.hd{{position:sticky;top:0;z-index:100;background:rgba(255,255,255,.85);backdrop-filter:blur(12px);border-bottom:1px solid #e5e7eb;padding:10px 16px;display:flex;align-items:center;justify-content:space-between}}
.hl{{font-weight:700;font-size:16px;display:flex;align-items:center;gap:6px}}
.hr{{font-size:10px;color:#9ca3af}}
.ctr{{max-width:680px;margin:0 auto;padding:16px}}
.hc{{background:#fff;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);padding:24px 20px;margin-bottom:16px;text-align:center;position:relative;overflow:hidden}}
.hc::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;background:linear-gradient(90deg,#10b981,#34d399)}}
.hb{{display:inline-block;background:#d1fae5;color:#10b981;font-size:12px;font-weight:600;padding:3px 10px;border-radius:20px;margin-bottom:6px}}
.ht{{font-size:22px;font-weight:800;margin:8px 0 4px}}
.hs{{font-size:13px;color:#6b7280;margin-bottom:8px}}
.hm{{display:flex;justify-content:center;gap:16px;flex-wrap:wrap;margin-bottom:6px}}
.hmi{{display:flex;flex-direction:column;align-items:center}}
.hmv{{font-size:18px;font-weight:700;color:#10b981}}
.hml{{font-size:11px;color:#9ca3af}}
.hd2{{font-size:11px;color:#9ca3af;margin-top:6px}}
.st{{font-size:18px;font-weight:700;margin-bottom:4px}}
.sd{{font-size:13px;color:#9ca3af;margin-bottom:12px}}
.card{{background:#fff;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);padding:16px;margin-bottom:12px}}
.chd{{display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap}}
.cd{{font-size:13px;font-weight:600}}
.cdr{{font-size:11px;color:#9ca3af;background:#f3f4f6;padding:2px 8px;border-radius:10px}}
.ctg{{display:flex;gap:4px;flex-wrap:wrap}}
.ct{{font-size:10px;padding:2px 8px;border-radius:4px;font-weight:500;background:rgba(16,185,129,.1);color:#10b981}}
.cbd{{font-size:14px;line-height:1.8}}
.cf2{{margin-top:12px;padding-top:10px;border-top:1px solid #e5e7eb}}
.cmd{{font-size:11px;color:#9ca3af;margin-bottom:6px}}
.cmk{{display:grid;grid-template-columns:repeat(4,1fr);gap:4px}}
.mi{{text-align:center;padding:4px}}
.mn{{font-size:10px;color:#9ca3af}}
.mv{{font-size:12px;font-weight:600}}
.mc{{font-size:11px}}
.mc.up{{color:#ef4444}}
.mc.down{{color:#10b981}}
.cs{{margin-top:14px;padding-top:12px;border-top:1px dashed #e5e7eb}}
.ctb{{font-size:12px;color:#10b981;cursor:pointer;padding:4px 10px;display:inline-block}}
.cl2{{margin-top:10px}}
.cm{{display:flex;gap:10px;padding:10px 0;border-bottom:1px solid #e5e7eb}}
.cm:last-child{{border-bottom:none;padding-bottom:0}}
.ca{{width:30px;height:30px;border-radius:50%;flex-shrink:0;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;color:#fff}}
.cb{{flex:1;min-width:0}}
.ch2{{display:flex;align-items:center;gap:6px;margin-bottom:3px}}
.cu{{font-size:12px;font-weight:600}}
.cba{{font-size:10px;padding:1px 6px;border-radius:4px;background:rgba(245,87,108,.12);color:#f5576c;font-weight:500}}
.ct2{{font-size:13px;line-height:1.6;color:#6b7280}}
.cf{{font-size:11px;color:#9ca3af;margin-top:4px}}
.mc2{{background:#fff;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);padding:20px;display:flex;gap:16px;align-items:flex-start;margin-bottom:12px}}
.mn2{{font-size:28px;font-weight:800;color:#10b981;opacity:.4;line-height:1;min-width:36px;text-align:center}}
.mb2 h3{{font-size:16px;font-weight:700;margin-bottom:4px}}
.mq{{font-size:12px;color:#9ca3af;font-style:italic;margin-bottom:6px}}
.md{{font-size:13px;color:#6b7280;line-height:1.7}}
.rc{{background:#fff;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);padding:16px;display:flex;gap:14px;align-items:flex-start;margin-bottom:12px}}
.rd{{font-size:14px;font-weight:700;color:#10b981;min-width:40px;text-align:center}}
.rb{{flex:1}}
.rp{{font-size:14px;margin-bottom:6px}}
.ra{{font-size:12px;color:#6b7280;margin-bottom:4px}}
.rr{{display:inline-block;font-size:11px;font-weight:600;padding:2px 10px;border-radius:10px}}
.rr.correct{{background:rgba(16,185,129,.1);color:#10b981}}
.rr.pending{{background:rgba(245,158,11,.1);color:#f59e0b}}
.rr.wake{{background:rgba(59,130,246,.1);color:#3b82f6}}
.ft{{text-align:center;padding:24px 16px;font-size:12px;color:#9ca3af;line-height:1.8}}
@media(prefers-color-scheme:dark){{
body{{background:#0f172a;color:#e2e8f0}}
.hd{{background:rgba(15,23,42,.85);border-color:#334155}}
.hc,.card,.mc2,.rc{{background:#1e293b;box-shadow:0 1px 3px rgba(0,0,0,.2)}}
.cdr{{background:#334155;color:#94a3b8}}
.cf2,.cm,.cs{{border-color:#334155}}
}}
</style>
</head>
<body>
<div class="hd">
  <span class="hl"><svg viewBox="0 0 24 24" fill="none" width="22" height="22"><rect width="24" height="24" rx="5" fill="url(#g)"/><defs><linearGradient id="g" x1="12" y1="0" x2="12" y2="24"><stop stop-color="#0EC8A9"/><stop offset="1" stop-color="#01C886"/></linearGradient></defs></svg>模型先生</span>
  <span class="hr">{esc(D["meta"]["last_updated"])}</span>
</div>
<div class="ctr">
  <div class="hc">
    <div class="hb">精华精选</div>
    <h1 class="ht">{esc(D["meta"]["title"])}</h1>
    <p class="hs">整理：{esc(D["meta"]["author"])}</p>
    <div class="hm">
      <div class="hmi"><span class="hmv">{D["meta"]["stats"]["videos"]}</span><span class="hml">精选视频</span></div>
      <div class="hmi"><span class="hmv">{D["meta"]["stats"]["transcripts"]}</span><span class="hml">完整逐字稿</span></div>
      <div class="hmi"><span class="hmv">{esc(D["meta"]["period"])}</span><span class="hml">覆盖时段</span></div>
    </div>
    <p class="hd2">{esc(D["meta"]["disclaimer"])}</p>
  </div>

  <!-- 标签导航 -->
  <div style="display:flex;background:#fff;border-radius:12px;box-shadow:0 1px 3px rgba(0,0,0,.06);padding:4px;margin-bottom:16px;gap:4px;position:sticky;top:52px;z-index:99">
    <a href="#track" style="flex:1;padding:10px 8px;border-radius:10px;background:#10b981;color:#fff;font-weight:600;font-size:14px;text-align:center;text-decoration:none">📋 跟踪</a>
    <a href="#method" style="flex:1;padding:10px 8px;border-radius:10px;background:transparent;color:#6b7280;font-size:14px;text-align:center;text-decoration:none">🧠 方法论</a>
    <a href="#review" style="flex:1;padding:10px 8px;border-radius:10px;background:transparent;color:#6b7280;font-size:14px;text-align:center;text-decoration:none">📊 复盘</a>
  </div>

  <div class="st" id="track">📋 每日跟踪</div>
  <div class="sd">最近视频，按时间从新到旧</div>
  {"".join(cards)}

  <div class="st" style="margin-top:20px" id="method">🧠 核心方法论</div>
  <div class="sd">从逐字稿中提炼的6大思维体系</div>
  {"".join(methods)}

  <div class="st" style="margin-top:20px" id="review">📊 判断复盘</div>
  <div class="sd">近期市场判断的验证记录</div>
  {"".join(reviews)}

  <div class="ft">禁止商用转载<br>精华精选整理：{esc(D["meta"]["author"])}<br>完整版请关注抖音「模型先生」</div>
</div>
</body>
</html>'''

with open('app.html', 'w') as f:
    f.write(html)
print(f'Done: {len(html)} bytes, {len(cards)} cards')
