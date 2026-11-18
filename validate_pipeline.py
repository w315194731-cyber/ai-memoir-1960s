"""TECH VALIDATION: run image->3D for one object (the enamel cup).

Steps: poll the already-submitted text-to-image task -> get image URL ->
submit img-to-3d -> poll -> download GLB. All state is written to
validation-state.json. Uses only stdlib. Key never printed.
"""
import json
import os
import time
import urllib.request
from pathlib import Path

BASE = "https://api.aholo3d.cn"
HERE = Path(__file__).resolve().parent
STATE = HERE / "validation-state.json"
KEY = os.environ.get("LUX3D_CN_API_KEY")
IMG_TASK = 8247945


def req(path, method="GET", body=None, headers=None, timeout=90):
    data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    else:
        h["Authorization"] = KEY
    r = urllib.request.Request(BASE + path, data=data, method=method, headers=h)
    with urllib.request.urlopen(r, timeout=timeout) as resp:
        return json.load(resp)


def save(st):
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=2), encoding="utf-8")


def unwrap(d):
    return d.get("d") if isinstance(d.get("d"), dict) else d


def find_output(detail):
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
                for k in ("url", "content", "imageUrl", "modelUrl", "glbUrl"):
                    if o.get(k):
                        return o[k]
            elif isinstance(o, str) and o.startswith("http"):
                return o
    return None


def main():
    st = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"imageTaskId": IMG_TASK}
    save(st)

    # 1) poll image task
    if not st.get("imageUrl"):
        print("Polling text-to-image task...", flush=True)
        for _ in range(120):
            d = unwrap(req(f"/lux3d/v1/generate/task/get?taskid={IMG_TASK}"))
            status = d.get("status")
            print(f"  image status={status}", flush=True)
            if status == 3:  # success
                url = find_output(d)
                if not url:
                    raise RuntimeError(f"no image url in outputs: {json.dumps(d, ensure_ascii=False)[:800]}")
                st["imageUrl"] = url
                save(st)
                print("IMAGE_URL=" + url, flush=True)
                break
            if status in (4, 5, 6):
                raise RuntimeError(f"image task failed: {status}")
            time.sleep(5)
        else:
            raise RuntimeError("image polling timeout")
    else:
        print("Image already done: " + st["imageUrl"], flush=True)

    # 2) submit img-to-3d
    if not st.get("modelTaskId"):
        payload = {"version": "G1-Turbo", "img": st["imageUrl"]}
        print("Submitting img-to-3d...", flush=True)
        r = req("/lux3d/v1/generate/img-to-3d/task/create", "POST", payload)
        d = unwrap(r)
        tid = d.get("taskId") or d.get("taskid") or (d if isinstance(d, int) else None)
        if not tid:
            tid = r.get("d") if isinstance(r.get("d"), int) else None
        if not tid:
            raise RuntimeError(f"no taskId: {r}")
        st["modelTaskId"] = tid
        save(st)
        print("MODEL_TASK_ID=" + str(tid), flush=True)

    # 3) poll model task
    tid = st["modelTaskId"]
    print("Polling img-to-3d task...", flush=True)
    for _ in range(240):
        d = unwrap(req(f"/lux3d/v1/generate/task/get?taskid={tid}"))
        status = d.get("status")
        print(f"  model status={status}", flush=True)
        if status == 3:
            url = find_output(d)
            st["modelUrl"] = url
            st["status"] = "succeeded"
            save(st)
            print("MODEL_URL=" + str(url), flush=True)
            if url:
                target = HERE / "reference" / "enamel_cup.glb"
                data = urllib.request.urlopen(url, timeout=120).read()
                target.write_bytes(data)
                print(f"GLB_SAVED={target} size={len(data)}", flush=True)
            return
        if status in (4, 5, 6):
            st["status"] = "failed"
            save(st)
            raise RuntimeError(f"model task failed: {status}")
        time.sleep(10)
    raise RuntimeError("model polling timeout")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("ERROR: " + str(e), flush=True)
