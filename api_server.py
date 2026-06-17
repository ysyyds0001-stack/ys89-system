"""YS89 Social Bot - 本地 API Server (Flask)
啟動: python api_server.py
預設 Port: 5566
"""
from flask import Flask, request, jsonify
from flask_cors import CORS
import json, os, sys, traceback, io

# 強制 UTF-8 輸出，避免 Windows cp950 編碼錯誤
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

app = Flask(__name__)
CORS(app)

@app.route("/api/health")
def health():
    return jsonify({"status": "ok", "version": "1.0"})

@app.route("/api/post", methods=["POST"])
def post_all():
    data = request.get_json()
    title   = data.get("title", "")
    summary = data.get("summary", "")
    url     = data.get("url", "")
    tags    = [t.strip() for t in data.get("tags", "").split(",") if t.strip()]
    platforms = data.get("platforms", ["blogger","tumblr","hackmd","telegram"])

    results = {}
    # 換行轉 <p>，保留段落格式
    summary_html = "".join(
        f"<p>{line}</p>" for line in summary.splitlines() if line.strip()
    ) or f"<p>{summary}</p>"
    content_html = f"<h2>{title}</h2>{summary_html}<p><a href='{url}'>原文連結</a></p>"

    if "blogger" in platforms:
        try:
            from blogger_post import post_to_blogger
            r = post_to_blogger(title, content_html, tags)
            results["blogger"] = {"ok": True, "url": r.get("url",""), "id": r.get("id","")}
        except Exception as e:
            results["blogger"] = {"ok": False, "error": str(e)}

    if "tumblr" in platforms:
        try:
            from tumblr_post import post_link as tumblr_link
            r = tumblr_link(title, url, summary, tags)
            pid = r.get("id","")
            results["tumblr"] = {"ok": True, "url": f"https://nightcat-game-notes.tumblr.com/post/{pid}", "id": str(pid)}
        except Exception as e:
            results["tumblr"] = {"ok": False, "error": str(e)}

    if "hackmd" in platforms:
        try:
            from hackmd_post import create_note
            tag_md = " ".join(f"#{t}" for t in tags)
            content_md = f"# {title}\n\n{summary}\n\n[原文連結]({url})\n\n{tag_md}"
            r = create_note(title, content_md, "guest", "owner")
            note_url = r.get("publishLink") or f"https://hackmd.io/{r.get('id','')}"
            results["hackmd"] = {"ok": True, "url": note_url, "id": r.get("id","")}
        except Exception as e:
            results["hackmd"] = {"ok": False, "error": str(e)}

    if "telegram" in platforms:
        try:
            from telegram_post import send_article
            r = send_article(title, summary, url, tags)
            results["telegram"] = {"ok": True, "id": str(r.get("message_id",""))}
        except Exception as e:
            results["telegram"] = {"ok": False, "error": str(e)}

    if "pixnet" in platforms:
        try:
            from pixnet_post import post_article as pixnet_article
            tag_list = [t.strip() for t in data.get("tags", "").split(",") if t.strip()]
            r = pixnet_article(title, content_html, tag_list)
            results["pixnet"] = {"ok": True, "url": r.get("url", "")}
        except Exception as e:
            results["pixnet"] = {"ok": False, "error": str(e)}

    if "reddit" in platforms:
        try:
            from reddit_post import post_link as reddit_link
            r = reddit_link(title, url)
            results["reddit"] = {"ok": True, "url": f"https://reddit.com{r.permalink}", "id": r.id}
        except Exception as e:
            results["reddit"] = {"ok": False, "error": str(e)}

    return jsonify({"results": results})

if __name__ == "__main__":
    print("YS89 Social Bot API Server")
    print("http://localhost:5566/api/health")
    app.run(host="localhost", port=5566, debug=False)
