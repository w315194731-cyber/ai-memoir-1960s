"""Create one 3DGS classroom with the Aholo World API and write scene-config.json.

Run ONLY after the user has explicitly approved one billable generation:
    python generate_classroom.py

The API key is read from the AHOLO_API_KEY environment variable. It is never
printed, logged, or written into any output file.
"""
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

BASE = "https://api.aholo.cn"
HERE = Path(__file__).resolve().parent
CONFIG = HERE / "scene-config.json"
STATE = HERE / "generation-state.json"

NAME = "梦核旧教室"
PROMPT = (
    "参考上传的照片，还原一间中国上世纪90年代到2000年代初的旧教室室内空间，"
    "真实比例，可漫游。泛黄的旧墙面和绿色墙裙，整齐排列的木质课桌椅，"
    "前方的讲台和绿色黑板，黑板上方挂着标语，右侧墙是带铁栏杆的大窗户，"
    "天花板装有吊扇和日光灯，下午自然光从窗户斜射进来，空气中能看到浮尘，"
    "整体是安静、空无一人、带一点怀旧梦核感的氛围，材质真实，细节清晰，明亮但不刺眼。"
)


def reference_url():
    p = HERE / "reference" / "uploaded-url.json"
    if p.exists():
        return json.loads(p.read_text(encoding="utf-8")).get("url")
    return None
POLL_SECONDS = 15
MAX_WAIT_SECONDS = 30 * 60
TERMINAL_OK = "SUCCEEDED"
TERMINAL_BAD = {"FAILED", "CANCELED", "TIMEOUT", "REJECTED"}


def api(path, method="GET", body=None):
    key = os.environ.get("AHOLO_API_KEY")
    if not key:
        raise RuntimeError("AHOLO_API_KEY is not set in this process")
    data = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    req = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={"Authorization": key, "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", "replace")[:500]
        raise RuntimeError(f"HTTP {e.code} on {path}: {detail}") from None


def pick_scene_url(detail):
    urls = (detail.get("assets") or {}).get("splats") or {}
    urls = urls.get("urls") or {}
    for field in ("spzPath", "plyPath", "lodMetaPath"):
        if urls.get(field):
            return urls[field]
    return None


def main():
    if STATE.exists():
        saved = json.loads(STATE.read_text(encoding="utf-8"))
        world_id = saved.get("worldId")
        if world_id:
            print(f"Resuming existing task: {world_id}")
    else:
        payload = {"name": NAME, "prompt": PROMPT}
        img = reference_url()
        if img:
            payload["resources"] = [{"url": img, "type": "image"}]
            print(f"Using reference image: {img}")
        result = api("/world/v1/generations", "POST", payload)
        world_id = result.get("worldId")
        if not world_id:
            raise RuntimeError(f"Create response has no worldId: {result}")
        STATE.write_text(json.dumps({"worldId": world_id}, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Task created: {world_id}")

    deadline = time.time() + MAX_WAIT_SECONDS
    while time.time() < deadline:
        detail = api(f"/world/v1/{world_id}")
        status = detail.get("status")
        print(f"status={status} progress={detail.get('progress')}")
        if status == TERMINAL_OK:
            url = pick_scene_url(detail)
            config = json.loads(CONFIG.read_text(encoding="utf-8")) if CONFIG.exists() else {}
            config.pop("_comment", None)
            config["embedHtml"] = ""
            config["sceneUrl"] = url or ""
            CONFIG.write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")
            extra = (detail.get("assets") or {}).get("imagery") or {}
            summary = {
                "worldId": world_id,
                "sceneUrl": url,
                "panoUrl": extra.get("panoUrl"),
                "upAxis": ((detail.get("assets") or {}).get("semanticsMetadata") or {}).get("upAxis"),
            }
            print("DONE: " + json.dumps(summary, ensure_ascii=False))
            return
        if status in TERMINAL_BAD:
            raise RuntimeError(f"Task ended with status {status}")
        time.sleep(POLL_SECONDS)

    raise RuntimeError("Polling timed out; rerun this script to resume from generation-state.json")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
