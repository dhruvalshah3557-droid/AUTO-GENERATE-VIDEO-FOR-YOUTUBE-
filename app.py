from pathlib import Path

from flask import Flask, jsonify, render_template, send_from_directory

from generator.brand import FORMATS, OUTPUT
from generator.campaigns import CAMPAIGNS
from generator.pipeline import generate_brand_video, list_ready_ads

app = Flask(__name__, template_folder="web", static_folder="web/static")


@app.get("/")
def home():
    return render_template(
        "index.html",
        videos=list_ready_ads(),
        campaigns=CAMPAIGNS,
        formats=FORMATS,
    )


@app.get("/api/status")
def status():
    return jsonify({"ads": list_ready_ads(), "campaigns": list(CAMPAIGNS), "formats": FORMATS})


@app.post("/api/generate/<campaign>/<fmt>")
def generate(campaign: str, fmt: str):
    result = generate_brand_video(fmt, campaign)
    result["media_url"] = f"/media/{Path(result['video']).name}"
    return jsonify(result)


@app.get("/media/<path:name>")
def media(name: str):
    return send_from_directory(OUTPUT, name)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5173, debug=False)
