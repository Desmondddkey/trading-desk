# -*- coding: utf-8 -*-
"""tunnel.py — GitHub Pages 故障時嘅臨時公開通道

背景（Desmond 2026-10-20 決定方案 3）：
  平時用 https://desmondddkey.github.io/trading-desk/
  GitHub Pages 壞 → 用本工具開臨時通道頂住，修好就返去。

用法：
  python tunnel.py --start     開 server + tunnel，印出網址
  python tunnel.py --status    睇下仲通唔通
  python tunnel.py --stop      收工

原理：
  ① python -m http.server 8099 服務 C:/Users/rain0/trading-os-web/docs
  ② cloudflared quick tunnel（trycloudflare.com，免帳號、無警告頁）
  ③ 網址寫入 output/tunnel_url.json，下次 --status 用

★ 限制（必須老實講）：
  · 網址係隨機嘅，每次重開會變
  · 依賴本機一直開機 + 有網
  · 所以只係「頂住」，唔可以取代 GitHub Pages
"""
import argparse
import json
import os
import re
import subprocess
import sys
import time
import urllib.request

WEB = r"C:\Users\rain0\trading-os-web"
DOCS = os.path.join(WEB, "docs")
CF = os.path.join(os.path.expanduser("~"), "bin", "cloudflared.exe")
PORT = 8099
STATE = os.path.join(os.path.expanduser("~"), "AppData", "Local", "hermes",
                     "cache", "tunnel_state.json")


def _http(url, timeout=8):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as r:
            return r.status
    except Exception:                                        # noqa: BLE001
        return 0


def _load():
    try:
        with open(STATE, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def _save(d):
    os.makedirs(os.path.dirname(STATE), exist_ok=True)
    with open(STATE, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=1)


def start():
    if not os.path.exists(CF):
        print(f"✗ 搵唔到 cloudflared：{CF}")
        print("  下載：https://github.com/cloudflare/cloudflared/releases")
        return 1
    log = os.path.join(os.path.dirname(CF), "cf.log")

    # ① 本機 server
    if _http(f"http://127.0.0.1:{PORT}/index.html") != 200:
        subprocess.Popen(
            [sys.executable, "-m", "http.server", str(PORT),
             "--bind", "127.0.0.1"],
            cwd=DOCS,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        for _ in range(20):
            time.sleep(0.4)
            if _http(f"http://127.0.0.1:{PORT}/index.html") == 200:
                break
    if _http(f"http://127.0.0.1:{PORT}/index.html") != 200:
        print("✗ 本機 server 起唔到")
        return 1
    print(f"✓ 本機 server  http://127.0.0.1:{PORT}")

    # ② cloudflared
    open(log, "w").close()
    subprocess.Popen(
        [CF, "tunnel", "--url", f"http://127.0.0.1:{PORT}",
         "--no-autoupdate"],
        cwd=os.path.dirname(CF),
        stdout=open(log, "w", encoding="utf-8", errors="replace"),
        stderr=subprocess.STDOUT,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

    url = None
    for _ in range(40):
        time.sleep(1)
        try:
            with open(log, encoding="utf-8", errors="replace") as f:
                m = re.search(r"https://[a-z0-9-]+\.trycloudflare\.com",
                              f.read())
            if m:
                url = m.group(0)
                break
        except OSError:
            pass
    if not url:
        print("✗ 拎唔到 tunnel 網址（睇 ~/bin/cf.log）")
        return 1

    for _ in range(20):
        if _http(url + "/index.html") == 200:
            break
        time.sleep(1)

    _save({"url": url, "started": time.strftime("%Y-%m-%d %H:%M")})
    print(f"✓ 臨時通道  {url}")
    print(f"  （GitHub Pages 修好之後請用返原本網址）")
    return 0


def status():
    d = _load()
    url = d.get("url")
    print(f"  本機 server : {'✓ 200' if _http(f'http://127.0.0.1:{PORT}/index.html') == 200 else '✗ 唔通'}")
    if not url:
        print("  tunnel      : 未開過")
        return 0
    ok = _http(url + "/index.html") == 200
    print(f"  tunnel      : {'✓ 200' if ok else '✗ 唔通'}  {url}")
    print(f"  開於        : {d.get('started')}")
    return 0


def stop():
    for name in ("cloudflared.exe",):
        subprocess.run(["taskkill", "/F", "/IM", name],
                       capture_output=True)
    _save({})
    print("✓ 已收 tunnel（本機 server 可能仍在，重開機會自動清）")
    return 0


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group(required=True)
    g.add_argument("--start", action="store_true")
    g.add_argument("--status", action="store_true")
    g.add_argument("--stop", action="store_true")
    a = ap.parse_args()
    if a.start:
        return start()
    if a.status:
        return status()
    return stop()


if __name__ == "__main__":
    sys.exit(main())
