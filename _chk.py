# -*- coding: utf-8 -*-
import io
import re
import sys
import time
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")
B = "https://desmondddkey.github.io/trading-desk/"
for p in ["logbook.html", "index.html"]:
    try:
        r = urllib.request.Request(B + p + "?cb=%d" % time.time(),
                                   headers={"Cache-Control": "no-cache"})
        h = urllib.request.urlopen(r, timeout=25).read().decode("utf-8", "replace")
        print("  %-14s live=%7dB  lb-tbl=%d  lb-when=%d" % (
            p, len(h), h.count("lb-tbl"), h.count("lb-when")))
    except Exception as e:
        print("  %-14s ERR %s" % (p, e))

# desk.html 冇 logbook —— 睇下佢係邊種生成方式
d = io.open("docs/desk.html", encoding="utf-8").read()
print("\n  desk.html:", len(d), "B  page()? ",
      "lb-wrap" in d, "| </footer>?", "</footer>" in d)
m = re.search(r"<title>([^<]+)</title>", d)
print("  title:", m.group(1) if m else None)
