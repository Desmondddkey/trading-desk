# -*- coding: utf-8 -*-
"""驗證 live 網站三個改動。"""
import re
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
B = "https://desmondddkey.github.io/trading-desk/"
for p in ["logbook.html", "index.html", "sectors.html", "dailyscan.html"]:
    try:
        r = urllib.request.Request(
            B + p + "?cb=%d" % time.time(),
            headers={"Cache-Control": "no-cache"})
        h = urllib.request.urlopen(r, timeout=25).read().decode("utf-8", "replace")
        m = re.search(r"<h1>(.*?)</h1>", h, re.S)
        h1 = (m.group(1) if m else "?").strip()
        print("  %-14s h1=%-28s HI!=%-5s lb=%d SECTOR=%-5s STAGE=%s" % (
            p, h1[:28],
            "YES" if "HI! Desmond" in h else "NO",
            h.count("lb-tbl"),
            "YES" if ">SECTOR<" in h else "NO",
            "YES" if ">STAGE<" in h else "NO"))
    except Exception as e:                                   # noqa: BLE001
        print("  %-14s ERR %s" % (p, e))
