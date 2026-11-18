"""Scene generation queue worker.

Reads generation-queue.json, and for every scene still pending:
  1. uploads its reference image (if any) via the ous upload API
  2. submits POST /world/v1/generations  (one billable call per scene)
  3. polls GET /world/v1/{worldId} until a terminal status
  4. writes the resulting splat URLs back into the queue file and the
     scene's output file, so the web page can pick them up

State is persisted after every step. Interrupting with Ctrl+C is safe:
rerunning resumes from where it stopped and NEVER re-submits a scene that
already has a worldId (so it never double-charges).

Usage:
    python queue_worker.py            # process the whole queue, in order
    python queue_worker.py --dry-run  # show what would be done, no API calls
"""
import argparse
import hashlib
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://api.aholo.cn"
HERE = Path(__file__).resolve().parent
QUEUE = HERE / "generation-queue.json"
RESULTS = HERE / "generation-results.json"

OK_STATUS = "SUCCEEDED"
BAD_STATUS = {"FAILED", "CANCELED", "TIMEOUT", "REJECTED"}
ACTIVE_STATUS = {"PENDING", "PREPROCESSING", "RUNNING"}


def save_json(path, obj):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    os.replace(tmp, path)


def api(path, method="GET", body=None, headers=None, timeout=90):
    key = os.environ.get("AHOLO_API_KEY")
    if not key:
        raise RuntimeError("AHOLO_API_KEY is not set")
    data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    else:
        h["Authorization"] = key
    req = urllib.request.Request(BASE + path, data=data, method=method, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def unwrap(d):
    return d.get("d") if isinstance(d.get("d"), dict) else d


def upload_image(rel_path):
    image = (HERE / rel_path).resolve()
    if not image.exists():
        raise RuntimeError(f"reference image not found: {image}")
    md5_hex = hashlib.md5(image.read_bytes()).hexdigest()
    token = unwrap(api("/asset/v1/token"))
    ous_token, domain = token["ousToken"], token["globalDomain"].rstrip("/")

    boundary = "----aholoUploadBoundary7MA4YWxk"
    parts = [
        f"--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="file"; filename="{image.name}"\r\nContent-Type: image/jpeg\r\n\r\n'.encode(),
        image.read_bytes(),
        f"\r\n--{boundary}\r\n".encode(),
        f'Content-Disposition: form-data; name="md5"\r\n\r\n{md5_hex}\r\n'.encode(),
        f"--{boundary}--\r\n".encode(),
    ]
    req = urllib.request.Request(
        domain + "/ous/api/v2/single/upload",
        data=b"".join(parts),
        method="POST",
        headers={"ous-token-v2": ous_token, "Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        json.loads(r.read().decode())

    for _ in range(60):
        st = unwrap(json_req(domain + "/ous/api/v2/upload/status", headers={"ous-token-v2": ous_token}))
        if st.get("status") == 5:
            url = st.get("url")
            if url and str(url).startswith("http"):
                return url
            raise RuntimeError(f"upload returned no url: {st}")
        if st.get("status") in (6, 8):
            raise RuntimeError(f"upload failed: {st}")
        time.sleep(1)
    raise RuntimeError("upload polling timed out")


def json_req(url, method="GET", body=None, headers=None, timeout=60):
    data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode())


def pick_result(detail):
    assets = detail.get("assets") or {}
    urls = (assets.get("splats") or {}).get("urls") or {}
    imagery = assets.get("imagery") or {}
    meta = assets.get("semanticsMetadata") or {}
    return {
        "sceneUrl": urls.get("spzPath") or urls.get("plyPath") or urls.get("lodMetaPath") or "",
        "plyPath": urls.get("plyPath") or "",
        "panoUrl": imagery.get("panoUrl") or "",
        "upAxis": meta.get("upAxis"),
    }


def write_outputs(scene, result):
    # 1) update generation-results.json (global manifest)
    results = {}
    if RESULTS.exists():
        try:
            results = json.loads(RESULTS.read_text(encoding="utf-8"))
        except Exception:
            results = {}
    results[scene["id"]] = {"name": scene["name"], **result}
    save_json(RESULTS, results)

    # 2) write the per-scene output file (e.g. scene-config.json) if requested
    out = scene.get("output")
    if out:
        path = (HERE / out).resolve()
        cfg = {}
        if path.exists():
            try:
                cfg = json.loads(path.read_text(encoding="utf-8"))
            except Exception:
                cfg = {}
        cfg.pop("_comment", None)
        cfg["sceneUrl"] = result["sceneUrl"]
        cfg["_source"] = {"worldId": scene.get("worldId"), "panoUrl": result["panoUrl"], "plyPath": result["plyPath"]}
        save_json(path, cfg)


def process(scene, queue, dry=False):
    sid = scene["id"]
    status = scene.get("status", "pending")
    if status == "succeeded":
        print(f"[{sid}] already succeeded, skip")
        return
    if status == "failed" and not scene.get("retry"):
        print(f"[{sid}] previously failed, skip (set retry=true to force)")
        return

    # A scene with a worldId is always resumed by polling, never re-submitted.
    if not scene.get("worldId"):
        if dry:
            print(f"[{sid}] DRY-RUN would submit: {scene['name']}")
            return
        img = scene.get("referenceImage")
        if img and not scene.get("uploadedUrl"):
            print(f"[{sid}] uploading reference image...")
            scene["uploadedUrl"] = upload_image(img)
            save_json(QUEUE, queue)
            print(f"[{sid}] uploaded")
        payload = {"name": scene["name"], "prompt": scene["prompt"]}
        if scene.get("uploadedUrl"):
            payload["resources"] = [{"url": scene["uploadedUrl"], "type": "image"}]
        print(f"[{sid}] submitting generation (billable)...")
        resp = api("/world/v1/generations", "POST", payload)
        world_id = unwrap(resp).get("worldId") or resp.get("worldId")
        if not world_id:
            raise RuntimeError(f"no worldId in response: {resp}")
        scene["worldId"] = world_id
        scene["status"] = "submitted"
        scene.pop("retry", None)
        save_json(QUEUE, queue)
        print(f"[{sid}] submitted: {world_id}")

    if dry:
        print(f"[{sid}] DRY-RUN would poll {scene.get('worldId')}")
        return

    wid = scene["worldId"]
    settings = queue.get("settings", {})
    deadline = time.time() + settings.get("maxWaitSeconds", 1800)
    interval = settings.get("pollSeconds", 15)
    print(f"[{sid}] polling {wid}...")
    while time.time() < deadline:
        detail = unwrap(api(f"/world/v1/{wid}"))
        st = detail.get("status")
        prog = detail.get("progress")
        print(f"[{sid}] status={st} progress={prog}", flush=True)
        if st == OK_STATUS:
            result = pick_result(detail)
            if not result["sceneUrl"]:
                raise RuntimeError(f"succeeded but no splat url: {detail}")
            scene["status"] = "succeeded"
            scene["result"] = result
            scene.pop("retry", None)
            save_json(QUEUE, queue)
            write_outputs(scene, result)
            print(f"[{sid}] DONE -> {result['sceneUrl']}")
            return
        if st in BAD_STATUS:
            scene["status"] = "failed"
            save_json(QUEUE, queue)
            raise RuntimeError(f"task ended with status {st}")
        time.sleep(interval)
    raise RuntimeError("polling timed out; rerun to resume (will not re-submit)")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    scenes = queue.get("scenes", [])
    pending = [s for s in scenes if s.get("status") not in ("succeeded",)]
    print(f"Queue: {len(scenes)} scene(s), {len(pending)} to process")

    for scene in scenes:
        try:
            process(scene, queue, dry=args.dry_run)
        except KeyboardInterrupt:
            print("\nInterrupted by user. Progress saved; rerun to resume.")
            sys.exit(130)
        except Exception as exc:
            print(f"[{scene['id']}] ERROR: {exc}", file=sys.stderr, flush=True)
            # continue with the next scene so one bad item doesn't block the queue
            continue
    print("Queue run finished.")


if __name__ == "__main__":
    main()
