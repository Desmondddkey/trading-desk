#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""deploy.py — 把 docs/ 推上 GitHub Pages（Desmond 2026-10-11）

用法：`python deploy.py`
- 前提：`build_site.py` 已經跑完（docs/ 係最新）
- 動作：git add → commit → push（用 gh 嘅 keyring token）
- 冇嘢變 = 唔 commit = 唔 push（乾淨退出）

⚠ gh.exe 喺 `C:\\Users\\rain0\\.local\\gh\\bin\\gh.exe`（可攜版，唔係 PATH 上）。
"""
import datetime
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
GH = r"C:\Users\rain0\.local\gh\bin\gh.exe"


def run(args, cwd=HERE, check=False, timeout=300):
    r = subprocess.run(args, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=cwd, timeout=timeout)
    if check and r.returncode != 0:
        raise RuntimeError(f"{args[0]} rc={r.returncode}: {(r.stderr or r.stdout)[:300]}")
    return r


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    if not os.path.exists(GH):
        print("✗ 搵唔到 gh.exe（可攜版）")
        return 1
    # 1. 有冇嘢變
    r = run(["git", "status", "--porcelain"])
    if not r.stdout.strip():
        print("冇變更，唔 push")
        return 0
    # 2. commit
    msg = f"每日自動更新 {datetime.date.today().isoformat()}"
    run(["git", "add", "-A"], check=True)
    run(["git", "commit", "-m", msg], check=True)
    # 3. push（用 gh 的 token：gh 會讀 keyring）
    run(["git", "push", "origin", "main"], check=True, timeout=600)
    print(f"✓ 已 push（{len(r.stdout.strip().splitlines())} 行變更）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
