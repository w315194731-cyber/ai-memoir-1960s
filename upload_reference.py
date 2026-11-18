"""Upload the reference classroom photo to Aholo's asset store via the ous API.

Uses only the Python standard library. The API key is read from AHOLO_API_KEY
and is never printed or written to disk. On success prints the public URL.
"""
import hashlib
import json
import os
import sys
import time
import urllib.request
from pathlib import Path

BASE = "https://api.aholo.cn"
HERE = Path(__file__).resolve().parent
IMAGE = HERE / "reference" / "ref05.jpg"


def json_req(url, method="GET", body=None, headers=None):
    data = json.dumps(body, ensure_ascii=False).encode() if body is not None else None
    h = {"Content-Type": "application/json"}
    if headers:
        h.update(headers)
    req = urllib.request.Request(url, data=data, method=method, headers=h)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())


def multipart_upload(url, ous_token, file_path, md5_hex):
    boundary = "----aholoUploadBoundary7MA4YWxk"
    name = file_path.name
    content = file_path.read_bytes()
    parts = []
    parts.append(f"--{boundary}\r\n".encode())
    parts.append(
        f'Content-Disposition: form-data; name="file"; filename="{name}"\r\n'
        f"Content-Type: image/jpeg\r\n\r\n".encode()
    )
    parts.append(content)
    parts.append(f"\r\n--{boundary}\r\n".encode())
    parts.append(f'Content-Disposition: form-data; name="md5"\r\n\r\n{md5_hex}\r\n'.encode())
    parts.append(f"--{boundary}--\r\n".encode())
    body = b"".join(parts)
    req = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"ous-token-v2": ous_token, "Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode())


def main():
    key = os.environ.get("AHOLO_API_KEY")
    if not key:
        raise RuntimeError("AHOLO_API_KEY is not set")
    if not IMAGE.exists():
        raise RuntimeError(f"Image not found: {IMAGE}")

    md5_hex = hashlib.md5(IMAGE.read_bytes()).hexdigest()
    token = json_req(BASE + "/asset/v1/token", headers={"Authorization": key})
    ous_token = token["ousToken"]
    domain = token["globalDomain"].rstrip("/")

    multipart_upload(domain + "/ous/api/v2/single/upload", ous_token, IMAGE, md5_hex)

    url = None
    for _ in range(60):
        st = json_req(domain + "/ous/api/v2/upload/status", headers={"ous-token-v2": ous_token})
        payload = st.get("d") if isinstance(st.get("d"), dict) else st
        status = payload.get("status")
        if status == 5:
            url = payload.get("url")
            break
        if status in (6, 8):
            raise RuntimeError(f"Upload failed: {st}")
        time.sleep(1)
    if not url or not str(url).startswith("http"):
        raise RuntimeError(f"No valid URL returned: {st}")

    # Save the URL locally so the generation script can consume it.
    out = HERE / "reference" / "uploaded-url.json"
    out.write_text(json.dumps({"url": url, "source": str(IMAGE.name)}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("UPLOADED_URL=" + url)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)
