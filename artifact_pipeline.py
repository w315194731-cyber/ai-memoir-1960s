"""Batch artifact pipeline: text-to-image -> image-to-3D -> GLB.

Reads memoir-data.json. For every chapter's artifact, in order:
  1. text-to-image  (POST /lux3d/v1/generate/multimodal-to-image/task/create)
  2. poll image task, get image URL (outputs[].content)
  3. image-to-3D    (POST /lux3d/v1/generate/img-to-3d/task/create, version G1-Turbo)
  4. poll model task, get results.zip URL (outputs[].content)
  5. download zip, extract mesh/*.glb into assets/<id>.glb

State is persisted per-artifact in pipeline-state.json after every step.
Ctrl+C is safe: rerunning resumes and NEVER re-submits a task that already
has an id, so it never double-charges. Key is read from env, never printed.

Usage:
    python artifact_pipeline.py --dry-run
    python artifact_pipeline.py              # process all pending artifacts
    python artifact_pipeline.py --chapter ch3-gaokao   # one chapter only
"""
import argparse
import json
import os
import shutil
import sys
import time
import urllib.request
import zipfile
from pathlib import Path
from io import BytesIO

BASE = "https://api.aholo3d.cn"
HERE = Path(__file__).resolve().parent
DATA = HERE / "memoir-data.json"
STATE = HERE / "pipeline-state.json"
ASSETS = HERE / "assets"
ASSETS.mkdir(exist_ok=True)


def api(path, method="GET", body=None, headers=None, timeout=90):
    key = os.environ.get("LUX3D_CN_API_KEY")
    if not key:
        raise RuntimeError("LUX3D_CN_API_KEY is not set")
    data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    h = {"Content-Type": "application/json"}
    h.update(headers or {"Authorization": key})
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def unwrap(d):
    return d.get("d") if isinstance(d.get("d"), dict) else d


def find_content(detail):
    outs = detail.get("outputs")
    if isinstance(outs, str):
        try:
            outs = json.loads(outs)
        except Exception:
            return None
    if isinstance(outs, dict):
        outs = [outs]
    if isinstance(outs, list):
        for o in outs:
            if isinstance(o, dict):
                for k in ("content", "url", "imageUrl", "modelUrl", "glbUrl"):
                    if o.get(k):
                        return o[k]
            elif isinstance(o, str) and o.startswith("http"):
                return o
    return None


def poll(task_id, kind, state, state_key, interval=5, max_n=240):
    """Poll a Lux3D task. status 3 = success, 4/5/6 = fail."""
    if state.get(state_key):
        return state[state_key]
    for _ in range(max_n):
        d = unwrap(api(f"/lux3d/v1/generate/task/get?taskid={task_id}"))
        st = d.get("status")
        print(f"    [{kind}] task {task_id} status={st}", flush=True)
        if st == 3:
            url = find_content(d)
            if not url:
                raise RuntimeError(f"no content url in outputs: {json.dumps(d, ensure_ascii=False)[:500]}")
            state[state_key] = url
            save_state(state)
            return url
        if st in (4, 5, 6):
            raise RuntimeError(f"{kind} task {task_id} failed: status={st}")
        time.sleep(interval)
    raise RuntimeError(f"{kind} task {task_id} polling timeout")


def save_state(state):
    tmp = STATE.with_suffix(".tmp")
    tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, STATE)


def process(chapter, state, dry=False):
    art = chapter["artifact"]
    cid = chapter["id"]
    rec = state.setdefault(cid, {})
    glb = ASSETS / f"{cid}.glb"

    if rec.get("done") and glb.exists():
        print(f"[{cid}] already done, skip", flush=True)
        return

    if dry:
        print(f"[{cid}] DRY-RUN would generate: {art['name']}", flush=True)
        return

    print(f"\n[{cid}] === {art['name']} ===", flush=True)

    # 1) text to image
    if not rec.get("imageTaskId"):
        resp = api("/lux3d/v1/generate/multimodal-to-image/task/create", "POST", {"prompt": art["prompt"]})
        tid = unwrap(resp)
        if not isinstance(tid, int):
            tid = resp.get("d")
        if not isinstance(tid, int):
            raise RuntimeError(f"no image task id: {resp}")
        rec["imageTaskId"] = tid
        save_state(state)
        print(f"    image task submitted: {tid}", flush=True)

    rec["imageUrl"] = poll(rec["imageTaskId"], "image", rec, "imageUrl", interval=5)
    print(f"    image: {rec['imageUrl'][:90]}", flush=True)

    # 2) image to 3D
    if not rec.get("modelTaskId"):
        resp = api("/lux3d/v1/generate/img-to-3d/task/create", "POST", {"version": "G1-Turbo", "img": rec["imageUrl"]})
        d = unwrap(resp)
        tid = d.get("taskId") or d.get("taskid") if isinstance(d, dict) else d
        if not isinstance(tid, int):
            tid = resp.get("d") if isinstance(resp.get("d"), int) else None
        if not isinstance(tid, int):
            raise RuntimeError(f"no model task id: {resp}")
        rec["modelTaskId"] = tid
        save_state(state)
        print(f"    model task submitted: {tid}", flush=True)

    zip_url = poll(rec["modelTaskId"], "model", rec, "zipUrl", interval=8)
    print(f"    model zip: {zip_url[:90]}", flush=True)

    # 3) download zip and extract GLB
    data = urllib.request.urlopen(zip_url, timeout=180).read()
    with zipfile.ZipFile(BytesIO(data)) as z:
        glb_names = [n for n in z.namelist() if n.lower().endswith(".glb")]
        if not glb_names:
            raise RuntimeError(f"no glb in archive: {z.namelist()}")
        target = glb_names[0]
        with z.open(target) as src, open(glb, "wb") as out:
            shutil.copyfileobj(src, out)
    rec["done"] = True
    rec["glb"] = str(glb.relative_to(HERE))
    rec["size"] = glb.stat().st_size
    save_state(state)
    print(f"    DONE: {glb.name} ({rec['size']/1024/1024:.1f} MB)", flush=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--chapter", help="only process this chapter id")
    args = ap.parse_args()

    data = json.loads(DATA.read_text(encoding="utf-8"))
    state = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {}
    chapters = data["chapters"]
    if args.chapter:
        chapters = [c for c in chapters if c["id"] == args.chapter]
        if not chapters:
            print(f"no chapter with id {args.chapter}", file=sys.stderr)
            sys.exit(1)

    print(f"Artifacts: {len(chapters)} to process", flush=True)
    for ch in chapters:
        try:
            process(ch, state, dry=args.dry_run)
        except KeyboardInterrupt:
            save_state(state)
            print("\nInterrupted. Progress saved; rerun to resume.", flush=True)
            sys.exit(130)
        except Exception as e:
            save_state(state)
            print(f"[{ch['id']}] ERROR: {e}", file=sys.stderr, flush=True)
            continue
    print("Pipeline finished.", flush=True)


if __name__ == "__main__":
    main()
