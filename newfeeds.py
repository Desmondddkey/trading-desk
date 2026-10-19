# -*- coding: utf-8 -*-
"""newfeeds.py — 四個外部數據源（Desmond 2026-10-19）

1. Market Monitor（Stockbee）  → Google Sheet CSV（209 日 breadth）
2. Stockbee 50                  → Google Sheet CSV（50 隻 × 191 日）
3. Sector Relative Strength     → Google Sheet（★ NSE 印度股）
4. Jeff Sun by momentum         → Google Sheet gviz（61 欄）

★ 全部用 gviz / export CSV，唔需要授權（除咗原本 401 嘅 export 端點）。

快取策略：
  cache/newfeeds/<name>_<YYYYMMDD>.csv
  TTL = 1 日（同日只抓一次）；抓唔到 → 退回最新一份快取並標明日期
  Missing ≠ Zero：完全冇數據 → 該頁顯示 DATA_UNAVAILABLE，唔准扮 0
"""
import datetime
import io
import os
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(HERE, "cache", "newfeeds")

# ── 資料源定義（寫死）
SOURCES = {
    "mm": dict(
        label="Market Monitor",
        icon="🌊",
        url=("https://docs.google.com/spreadsheet/pub?"
             "key=0Am_cU8NLIU20dEhiQnVHN3Nnc3B1S3J6eGhKZFo0N3c&output=csv"),
        note="Stockbee 每日 breadth（升/跌 4%+ 家數、5/10 日比率）",
    ),
    "bee50": dict(
        label="Stockbee 50",
        icon="🐝",
        url=("https://docs.google.com/spreadsheets/d/"
             "1xjbe9SF0HsxwY_Uy3NC2tT92BqK0nhArUaYU16Q0p9M/"
             "gviz/tq?tqx=out:csv&gid=1499398020"),
        note="每日 50 隻最強動能股（日期為欄）",
    ),
    "sectorrs": dict(
        label="Sector RS",
        icon="🏭",
        url=("https://docs.google.com/spreadsheets/d/"
             "1sR0Edn3q5PKEAcaAOSZIAAisn8bvEzzY8EwiKJTIlBQ/"
             "gviz/tq?tqx=out:csv&gid=539776210"),
        note="★ NSE（印度）500 隻 + 相對強度 30 日",
    ),
    "jeffsun": dict(
        label="Jeff Sun Momentum",
        icon="🎯",
        url=("https://docs.google.com/spreadsheets/d/"
             "1TDiU6Wt0YYoJ1YPEtcwqWY4UU8FMj1vLLYFxQitg6oE/"
             "gviz/tq?tqx=out:csv&gid=634720175"),
        note="板塊/ETF 動能：1D/1W/1M/3M/6M/12M、ADR%、距 50SMA",
    ),
}


def _today():
    return datetime.date.today().strftime("%Y%m%d")


def fetch(name, force=False):
    """抓一個源 → (text, asof, from_cache)。失敗回 (None, None, False)。"""
    os.makedirs(CACHE, exist_ok=True)
    day = _today()
    p = os.path.join(CACHE, f"{name}_{day}.csv")

    if os.path.exists(p) and not force:
        try:
            return io.open(p, encoding="utf-8", errors="replace").read(), day, True
        except OSError:
            pass

    url = SOURCES[name]["url"]
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (compatible; trading-desk/1.0)"})
        with urllib.request.urlopen(req, timeout=45) as r:
            raw = r.read()
        # Google 有時回 UTF-8 BOM
        txt = raw.decode("utf-8-sig", errors="replace")
        if not txt.strip():
            raise ValueError("empty body")
        io.open(p, "w", encoding="utf-8").write(txt)
        return txt, day, False
    except Exception:
        # 退回最新快取
        try:
            files = sorted(
                f for f in os.listdir(CACHE)
                if f.startswith(name + "_") and f.endswith(".csv"))
            if files:
                newest = files[-1]
                asof = newest.split("_")[-1].replace(".csv", "")
                txt = io.open(os.path.join(CACHE, newest),
                              encoding="utf-8", errors="replace").read()
                return txt, asof, True
        except OSError:
            pass
        return None, None, False


def parse_mm(txt):
    """Market Monitor CSV → dict（最新一日 + 近 N 日序列）。"""
    import csv
    rows = list(csv.reader(io.StringIO(txt)))
    if len(rows) < 4:
        return None

    def num(v):
        try:
            return float(str(v).replace(",", "").replace("%", "").strip())
        except (TypeError, ValueError):
            return None

    # 找標題行（含 'Date'）
    hi = None
    for i, r in enumerate(rows[:6]):
        if r and str(r[0]).strip().lower().startswith("date"):
            hi = i
            break
    if hi is None:
        return None
    head = [str(c).strip() for c in rows[hi]]

    data = []
    for r in rows[hi + 1:]:
        if not r or not str(r[0]).strip():
            continue
        d = {}
        for j, h in enumerate(head):
            if j < len(r):
                d[h] = r[j]
        data.append(d)
    if not data:
        return None

    latest = data[0]

    def pick(d, *needles):
        for h in head:
            lh = h.lower()
            if all(n in lh for n in needles):
                return num(d.get(h))
        return None

    # 5 日 / 10 日比率 + 升跌 4%+
    return dict(
        date=str(latest.get(head[0], "")),
        up4=pick(latest, "up", "4%"),
        down4=pick(latest, "down", "4%"),
        r5=pick(latest, "5", "day"),
        r10=pick(latest, "10", "day"),
        up25q=pick(latest, "up", "25%"),
        down25q=pick(latest, "down", "25%"),
        series=[dict(date=str(d.get(head[0], "")),
                     up4=num(d.get(head[1])) if len(head) > 1 else None,
                     down4=num(d.get(head[2])) if len(head) > 2 else None)
                for d in data[:60]],
        n_rows=len(data),
        cols=head,
    )


def parse_bee50(txt):
    """Stockbee 50 CSV → 最新一日 50 隻 + 日期清單。"""
    import csv
    rows = list(csv.reader(io.StringIO(txt)))
    if len(rows) < 2:
        return None
    dates = [str(c).strip() for c in rows[0]]
    if not dates or not dates[0]:
        return None
    cols = []
    for j in range(len(dates)):
        col = [r[j].strip() for r in rows[1:] if j < len(r) and r[j].strip()]
        cols.append(col)
    return dict(dates=dates, columns=cols, n_days=len(dates),
                today=cols[0] if cols else [])


def parse_sectorrs(txt):
    """Sector RS → 按 3 個月變動排序（★ RS-30D 欄原表空白，用 %Chg_3M 代替）。"""
    import csv
    rows = list(csv.reader(io.StringIO(txt)))
    if len(rows) < 2:
        return None
    head = [str(c).strip() for c in rows[0]]

    def idx(*names):
        for n in names:
            for j, h in enumerate(head):
                if h.lower() == n.lower():
                    return j
        return None

    i_sym = idx("Symbol")
    i_ex = idx("Exchg")
    i_ltp = idx("Ltp")
    i_chg = idx("%Chg Daily")
    i_rs = idx("Relative Strength - 30D")
    i_1m = idx("%Chg_1M", "%Chg 1M")
    i_3m = idx("%Chg_3M", "%Chg 3M")
    i_6m = idx("%Chg_6M", "%Chg 6M")
    if i_sym is None:
        return None

    def num(v):
        try:
            return float(str(v).replace(",", "").replace("%", "").strip())
        except (TypeError, ValueError):
            return None

    out = []
    for r in rows[1:]:
        if i_sym >= len(r) or not r[i_sym].strip():
            continue
        out.append(dict(
            sym=r[i_sym].strip(),
            exch=r[i_ex].strip() if i_ex is not None and i_ex < len(r) else "",
            ltp=num(r[i_ltp]) if i_ltp is not None and i_ltp < len(r) else None,
            chg=num(r[i_chg]) if i_chg is not None and i_chg < len(r) else None,
            rs30=num(r[i_rs]) if i_rs is not None and i_rs < len(r) else None,
            m1=num(r[i_1m]) if i_1m is not None and i_1m < len(r) else None,
            m3=num(r[i_3m]) if i_3m is not None and i_3m < len(r) else None,
            m6=num(r[i_6m]) if i_6m is not None and i_6m < len(r) else None,
        ))
    exchs = sorted({x["exch"] for x in out if x["exch"]})
    has_rs = sum(1 for x in out if x["rs30"] is not None)
    return dict(rows=out, n=len(out), exchanges=exchs, cols=head,
                has_rs=has_rs)


def parse_jeffsun(txt):
    """Jeff Sun momentum → 位置映射（★ header 只有 3 個標籤，其餘空白）。

    實測欄位位置（2026-10-19）：
      0 空 / 1 RS% / 2 Ticker / 3 Name / 4 ADR% / 5 ? /
      6 1D% / 7 1W% / 8 1M% / 9 3M% / 10 6M% / 11 12M% /
      12 50SMA / 13 14ATR / 15 價格
    """
    import csv
    rows = list(csv.reader(io.StringIO(txt)))
    if len(rows) < 3:
        return None
    head = [str(c).strip() for c in rows[0]]

    # ★ 位置映射（唔靠 header，因為大部分標籤空白）
    POS = dict(rs=1, sym=2, name=3, adr=4, d1=6, w1=7, m1=8,
               m3=9, m6=10, m12=11, sma50=12, atr=13, px=15)

    def num(v):
        try:
            return float(str(v).replace(",", "").replace("%", "")
                         .replace("$", "").strip())
        except (TypeError, ValueError):
            return None

    def cell(r, i):
        return r[i] if i < len(r) else ""

    out = []
    for r in rows[1:]:
        sym = cell(r, POS["sym"]).strip()
        if not sym or sym.lower() in ("nan", "ticker"):
            continue
        out.append(dict(
            sym=sym,
            name=cell(r, POS["name"]).strip(),
            rs=num(cell(r, POS["rs"])),
            adr=num(cell(r, POS["adr"])),
            d1=num(cell(r, POS["d1"])),
            w1=num(cell(r, POS["w1"])),
            m1=num(cell(r, POS["m1"])),
            m3=num(cell(r, POS["m3"])),
            m6=num(cell(r, POS["m6"])),
            m12=num(cell(r, POS["m12"])),
            sma50=num(cell(r, POS["sma50"])),
            atr=num(cell(r, POS["atr"])),
            px=num(cell(r, POS["px"])),
        ))
    return dict(rows=out, n=len(out), cols=head)


def load_all(force=False):
    """抓 + 解析全部四個源。回 dict(name → parsed | None)。"""
    out = {}
    for name in SOURCES:
        txt, asof, cached = fetch(name, force=force)
        if txt is None:
            out[name] = None
            continue
        try:
            if name == "mm":
                d = parse_mm(txt)
            elif name == "bee50":
                d = parse_bee50(txt)
            elif name == "sectorrs":
                d = parse_sectorrs(txt)
            else:
                d = parse_jeffsun(txt)
        except Exception:
            d = None
        if d is not None:
            d["_asof"] = asof
            d["_cached"] = cached
        out[name] = d
    return out
