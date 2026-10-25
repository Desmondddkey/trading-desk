# -*- coding: utf-8 -*-
"""setupfactory_page.py — Setup Factory（技巧資料庫）

Desmond 2026-10-22：
  「https://lukelwang.github.io/1chartmaster-strategy/
    蒸餾出呢個網站所有內容，附有說明同圖示做法
    之後係我個page 到開一個新page 叫 Setup factory
    我要打做一個做數庫儲存呢d 重要技巧」

━━━ 來源 ━━━
1ChartMaster 策略圖解（lukelwang.github.io/1chartmaster-strategy）
資料範圍 2025-09-04 → 2026-10-06，4,446 條歸檔帖文，9 個精選案例。
本站與作者無隸屬關係。

━━━ 架構 ━━━
每個技巧 = ① 一句定義 ② SVG 圖示 ③ 條件 ④ 失效 ⑤ 我哋系統對應
圖示全部用假設數據畫，只解釋結構，唔係歷史回測。
"""
import io
import os

HERE = os.path.dirname(os.path.abspath(__file__))
TO = r"C:\Users\rain0\trading-os"


def _svg_30m_pivot():
    """30 分鐘反轉 pivot：下跌 → 陽線 → 突破高點 → 止損在陽線低點"""
    return """
<svg viewBox="0 0 520 210" style="width:100%;height:auto;display:block;
 background:rgba(128,140,170,.06);border-radius:8px">
  <defs><marker id="ar30" markerWidth="7" markerHeight="7" refX="6" refY="3"
    orient="auto"><path d="M0,0 L6,3 L0,6 z" fill="#2563eb"/></marker></defs>
  <!-- 下跌段 -->
  <polyline points="30,60 70,72 110,90 150,112 190,128 230,140"
   fill="none" stroke="#dc2626" stroke-width="2.5"/>
  <!-- 陽線（觸發 bar） -->
  <rect x="248" y="118" width="26" height="34" fill="#16a34a" opacity=".85"/>
  <line x1="261" y1="108" x2="261" y2="118" stroke="#16a34a" stroke-width="2"/>
  <line x1="261" y1="152" x2="261" y2="162" stroke="#16a34a" stroke-width="2"/>
  <!-- 陽線高／低水平線 -->
  <line x1="248" y1="108" x2="430" y2="108" stroke="#16a34a"
   stroke-width="1.6" stroke-dasharray="5,4"/>
  <line x1="248" y1="162" x2="430" y2="162" stroke="#dc2626"
   stroke-width="1.6" stroke-dasharray="5,4"/>
  <!-- 突破 -->
  <polyline points="274,132 300,120 326,100 352,88 380,74 410,62 440,52"
   fill="none" stroke="#16a34a" stroke-width="2.5" marker-end="url(#ar30)"/>
  <!-- 標註 -->
  <text x="26" y="46" font-size="11" fill="#dc2626" font-weight="700">
   ① 連續下跌／回調</text>
  <text x="242" y="100" font-size="11" fill="#16a34a" font-weight="700">
   ② 乾淨陽線</text>
  <text x="300" y="106" font-size="10.5" fill="#2563eb">
   ← 下一根越過此高點才觸發</text>
  <text x="300" y="176" font-size="10.5" fill="#dc2626">
   ← 止損：陽線低點下方</text>
  <text x="380" y="46" font-size="10.5" fill="#16a34a">③ 觸發後跟隨</text>
</svg>"""


def _svg_squat_ema():
    """8 週 EMA squat：強勢 → 回落到上升均線 → 收縮 → 續漲"""
    return """
<svg viewBox="0 0 520 210" style="width:100%;height:auto;display:block;
 background:rgba(128,140,170,.06);border-radius:8px">
  <!-- 8 週 EMA（上升） -->
  <line x1="30" y1="170" x2="480" y2="60" stroke="#f59e0b"
   stroke-width="2.4" stroke-dasharray="7,4"/>
  <text x="392" y="52" font-size="10.5" fill="#f59e0b" font-weight="700">
   8 週 EMA（上升）</text>
  <!-- 價格 -->
  <polyline points="30,150 60,110 90,80 120,60 150,52 180,66 210,96
   240,124 270,140 300,132 330,116 360,96 390,76 420,60 450,48 480,40"
   fill="none" stroke="#2563eb" stroke-width="2.6"/>
  <!-- squat 區間 -->
  <rect x="200" y="88" width="130" height="66" fill="#f59e0b" opacity=".16"
   rx="6"/>
  <text x="204" y="82" font-size="11" fill="#f59e0b" font-weight="700">
   SQUAT：觸及上升均線 + 量縮收緊</text>
  <text x="28" y="188" font-size="10.5" fill="#16a34a">
   強勢</text>
  <text x="376" y="188" font-size="10.5" fill="#16a34a">續漲（需觸發確認）</text>
</svg>"""


def _svg_vcp():
    """VCP：波幅逐級收縮 → 量縮 → 放量突破"""
    return """
<svg viewBox="0 0 520 200" style="width:100%;height:auto;display:block;
 background:rgba(128,140,170,.06);border-radius:8px">
  <!-- 收縮三角 -->
  <polyline points="40,60 120,140 200,80 270,120 330,92 380,108"
   fill="none" stroke="#2563eb" stroke-width="2.4"/>
  <!-- 上／下軌 -->
  <line x1="40" y1="50" x2="380" y2="96" stroke="#94a3b8"
   stroke-width="1.2" stroke-dasharray="4,4"/>
  <line x1="40" y1="150" x2="380" y2="112" stroke="#94a3b8"
   stroke-width="1.2" stroke-dasharray="4,4"/>
  <!-- 突破 -->
  <polyline points="380,108 410,86 440,62 470,44"
   fill="none" stroke="#16a34a" stroke-width="2.8"/>
  <line x1="380" y1="96" x2="440" y2="96" stroke="#16a34a"
   stroke-width="1.6" stroke-dasharray="5,4"/>
  <text x="46" y="40" font-size="11" fill="#2563eb" font-weight="700">
   VCP：波幅一級一級收窄</text>
  <text x="46" y="172" font-size="10.5" fill="#94a3b8">
   每次回調幅度細過上一次 ＋ 成交量縮</text>
  <text x="392" y="80" font-size="10.5" fill="#16a34a" font-weight="700">
   ← 放量突破才觸發</text>
</svg>"""


def _svg_rs_first():
    """RS 先創新高，價格未跟上（divergence）"""
    return """
<svg viewBox="0 0 520 190" style="width:100%;height:auto;display:block;
 background:rgba(128,140,170,.06);border-radius:8px">
  <text x="26" y="24" font-size="11" fill="#2563eb" font-weight="700">
   RS 線</text>
  <polyline points="30,60 80,50 130,38 180,26 230,20 280,16"
   fill="none" stroke="#2563eb" stroke-width="2.6"/>
  <circle cx="280" cy="16" r="5" fill="#2563eb"/>
  <text x="292" y="20" font-size="10" fill="#2563eb">新高 ←</text>
  <line x1="30" y1="95" x2="490" y2="95" stroke="#94a3b8"
   stroke-width="1" stroke-dasharray="3,3"/>
  <text x="26" y="118" font-size="11" fill="#16a34a" font-weight="700">
   價格</text>
  <polyline points="30,150 80,138 130,146 180,132 230,140 280,128"
   fill="none" stroke="#16a34a" stroke-width="2.2"/>
  <text x="292" y="132" font-size="10" fill="#94a3b8">
   未創新高（落後）</text>
  <text x="26" y="178" font-size="10.5" fill="#94a3b8">
   RS 是【篩選方向】，不是單獨入場信號 —— 仍要等支撐 + 觸發</text>
</svg>"""


def _svg_trim():
    """冲高減倉：垂直擴張減 1/3，剩餘跟隨趨勢"""
    return """
<svg viewBox="0 0 520 200" style="width:100%;height:auto;display:block;
 background:rgba(128,140,170,.06);border-radius:8px">
  <polyline points="30,160 70,150 110,138 150,120 190,96 230,64 270,36
   310,44 350,68 390,54 430,30 470,18"
   fill="none" stroke="#2563eb" stroke-width="2.6"/>
  <!-- 減倉點 -->
  <circle cx="268" cy="36" r="6" fill="#dc2626"/>
  <text x="196" y="28" font-size="10.5" fill="#dc2626" font-weight="700">
   垂直擴張 → 減 33%</text>
  <line x1="268" y1="36" x2="268" y2="190" stroke="#dc2626"
   stroke-width="1" stroke-dasharray="4,4" opacity=".6"/>
  <!-- 剩餘核心 -->
  <line x1="268" y1="52" x2="470" y2="34" stroke="#16a34a"
   stroke-width="1.4" stroke-dasharray="6,4"/>
  <text x="330" y="120" font-size="10.5" fill="#16a34a" font-weight="700">
   剩餘 67% 跟隨趨勢（10EMA 管理）</text>
  <text x="26" y="184" font-size="10.5" fill="#94a3b8">
   作者常舉 1/3，案例出現過 1/2 同 3/4 —— 比例係對情境嘅反應，唔係固定參數</text>
</svg>"""


SETUP = [
    dict(
        n="01", key="RS 領導股", icon="📈",
        one="先找已經證明強勢嘅股，唔係找便宜股。RS 係篩選方向，唔係入場信號。",
        look=[
            "RS 線有冇【先於】股價創新高（divergence）",
            "板塊有冇帶動作用",
            "有冇財報或產業催化",
        ],
        fail="RS 強但價格冇支撐 → 唔可以追高。RS 高 ≠ 可以買。",
        sys="✅ rs_before_price.py（RS 先創新高但價未跟上）"
            "｜layer2a_rs（RS Rating 0–99）",
        svg=_svg_rs_first,
    ),
    dict(
        n="02", key="強勢後的回撤", icon="↩️",
        one="買「強勢之後嘅弱勢」—— 股票先有動能，然後回調到"
            "缺口／舊 pivot／趨勢線／均線。作者後期特別強調："
            "許多最佳交易係喺突破【之前】嘅回調中建立。",
        look=[
            "回調位置係咪「可解釋嘅支撐」（缺口、舊 pivot、趨勢線、均線）",
            "回調幅度有冇縮（一級比一級細）",
            "成交量有冇縮（供應減少）",
        ],
        fail="回調穿咗結構低點 → 唔係回調，係轉勢。",
        sys="✅ layer2_focus_stalk（pullback 條件）"
            "｜HPAT（H 型態，n=790 EV +0.83R t=+3.55）",
        svg=_svg_squat_ema,
    ),
    dict(
        n="03", key="結構與均線", icon="📐",
        one="8 週 EMA 係重要週線參考；日線常出現 8 日／21 日 EMA "
            "或其他結構支撐。Inside day、旗形、VCP、橫向整理與量縮"
            "用嚟觀察供應減少。",
        look=[
            "8 週 EMA（週線）有冇上升",
            "8 日 / 21 日 EMA 有冇托住",
            "Inside day / VCP / 旗形 —— 波幅逐級收窄",
            "缺口與舊阻力轉支撐（S/R flip）",
        ],
        fail="均線向下 + 波幅放大 = 唔係收縮，係派發。",
        sys="✅ 8/21 EMA 喺 charts 圖｜VCP 部分（setup_alerts 6-setup）"
            "⚠ 8 週 EMA 尚未系統化",
        svg=_svg_vcp,
    ),
    dict(
        n="04", key="30 分鐘 pivot（觸發）", icon="⏱",
        one="喺強勢股下跌或回落至關鍵支撐後，等第一根乾淨嘅"
            "【30 分鐘陽線】收完；下一根越過佢高點才觸發，"
            "止損放喺該陽線低點下方。用支撐位置 + 小週期確認。",
        look=[
            "支撐已經到（位置）",
            "出現一根乾淨 30 分鐘陽線（時機）",
            "下一根越過陽線高點 → 觸發",
            "止損 = 陽線低點下方",
        ],
        fail="跌穿陽線低點 → 呢次反轉失效，即刻走。",
        sys="⚠ 未實作（我哋用日線 pivot，唔係 30 分鐘）"
            "｜ORH 警報部分接近，但係開盤區間唔係反轉 pivot",
        svg=_svg_30m_pivot,
    ),
    dict(
        n="05", key="失效點（先想錯）", icon="🛑",
        one="結構低點或 pivot K 線低點係初始失效參考。"
            "突破觸發後反向跌穿失效點，及時退出；"
            "新信號成立時可以重新評估 —— 唔把一次止損當永久禁買。",
        look=[
            "初始止損喺邊（結構低點 / pivot K 線低點）",
            "距離入場幾多 % / 幾多 ATR",
            "跌穿之後有冇新觸發（可以重入，但要有新信號）",
        ],
        fail="跌穿止損仍然抱住 = 呢個唔係止損，係希望。",
        sys="✅ jeffsun_stop.py（Day 0–2 LoD）"
            "｜LOD ≤ 0.60 ATR 入場閘",
        svg=_svg_30m_pivot,
    ),
    dict(
        n="06", key="冲高減倉", icon="✂️",
        one="喺垂直擴張或供應阻力附近賣出部分，回收風險並降低隔夜"
            "暴露；有利潤墊嘅剩餘倉位繼續跟隨趨勢。作者常舉 1/3，"
            "實際案例有 1/2 同 3/4。",
        look=[
            "有冇垂直擴張（幾日內急升）",
            "接近阻力／供應區",
            "減幾多 —— 1/3 常態，唔夠好嘅入場可以更積極",
        ],
        fail="減倉比例唔係固定參數。把 3/4 宣傳成全策略固定值 = 錯。",
        sys="✅ SOUL §4 分批止賺：2R 減 33% → ATRX>8 再減 33% → 拖 10EMA",
        svg=_svg_trim,
    ),
    dict(
        n="07", key="行情難做時降低參與", icon="🌧",
        one="大盤均線向下、廣度弱或信號缺乏持續性時，減小 swing 暴露、"
            "喺強勢中更積極減倉、減少隔夜風險。連續失敗時停止當日"
            "繼續嘗試，保留資金等更清楚嘅機會。",
        look=[
            "大盤均線向上定向下",
            "廣度（% 股票喺 50MA 上）",
            "連續失敗幾多次",
        ],
        fail="連續失敗仍然加碼 = 報復交易。",
        sys="✅ market_regime.py（Weinstein 四階段 + MMFI）"
            "｜discipline_gate.py（連蝕 3 日停）"
            "｜portfolio_brake.py（連蝕 3 日停手、賺 5 萬鎖半倉）",
        svg=_svg_squat_ema,
    ),
]

CASES = [
    ("NBIS", "30 分鐘反轉", "2025-10-23",
     "連續 7 天下跌回到既定支撐，1:30pm 開始 pivot、2pm 觸發；"
     "買 95.85，止損低於 94.63，100 附近減倉以幫助持有剩餘過夜。",
     "同時學日線位置同 30 分鐘觸發。減倉對應實際管理動作，"
     "後續上漲唔可以全部算已兌現。"),
    ("AMD", "趨勢線回測", "2026-09-19",
     "跳過 9/8 高開突破（風險回報唔理想）；9/14 低開回測 DTL 後，"
     "用 30 分鐘 pivot 487.75 入場、483.49 止損，上漲中減倉。",
     "同一隻股，位置同風險距離會改變交易質量。"
     "週末收 559.82 係後續市價，唔可以當全部賣出價。"),
    ("OII", "8 週支撐", "2026-08-30",
     "假突破後回落到上升 8 週 EMA 嘅 squat，等買方能否承接並開始"
     "真正續漲。呢帖只表達觀察條件，冇已成交買價。",
     "觸及 8 週 EMA 只係觀察區，下一步仍需觸發同失效計劃。"
     "唔可以把觀察帖改寫成成功交易。"),
    ("GH", "收縮突破", "2026-08-28",
     "高位 VCP 與回調量縮，173.10 附近放量突破觸發，"
     "要求成交量超過日均量。",
     "把「形態睇落唔錯」同「入場已經觸發」分開；"
     "呢個係當時條件設置，唔係完整交易結果。"),
    ("CRWV", "HVE 與趨勢線", "2025-09-18",
     "強調 HVE K 線同 9/12 嘅 30 分鐘 pivot，隨後觀察價格測試下降趨勢線。",
     "量能事件、低週期 pivot 同日線阻力可以同時存在；"
     "HVE 唔等於跳過風險檢查直接追高。"),
    ("CDNA", "ORB 與退出", "2026-09-24",
     "30min ORB 58.16 入場，止損低於突破 K 線低點 56.92，"
     "62.39 賣 3/4、餘下繼續 swing；理由係入場唔夠理想，"
     "想在強勢中降低風險。",
     "減倉比例係對情境嘅反應，唔可以把 3/4 或 1/3 "
     "宣傳成全策略固定參數。"),
    ("MP", "失敗與重新入場", "2025-10-08",
     "10/8 回顧：前一天嘗試 ORB 後很快跌破日低而止損。"
     "10/9 更新：前一天收盤前再喺 30 分鐘 pivot 重新進入，次日高開。",
     "止損唔必取消整個觀察清單；重新入場要有新觸發，"
     "唔可以因為唔服氣而取消止損。"),
    ("COUR", "突破失敗", "2025-09-11",
     "提醒：setup 可以靚、觸發並開始向好，隨後仍會被賣壓打回，"
     "所以必須用止損保護資金。呢帖冇個人入場同出場價。",
     "唔可以只展示成功圖。形態同 HVE 係候選依據，"
     "失效退出才係風險管理嘅一半。"),
    ("QQQ", "市場環境", "2026-03-12",
     "QQQ EMA 向下交叉、均線彎頭向下，明確稱自己正在減少隔夜風險。",
     "同一套入場技術，喺缺乏持續性嘅市場需要唔同參與強度；"
     "唔係見到一根 pivot 就必須滿倉。"),
]

TERMS = [
    ("RS / RS Rating / 藍點", "相對市場或基準嘅強弱；藍點常用嚟標示相對強勢新高。"
     "RS 同 RSI 唔同，評分同藍點算法未完整公開。"),
    ("Pivot", "可交易嘅價格關口或反轉觸發。日線 pivot、開盤區間 pivot "
     "同下跌後嘅 30 分鐘反轉 pivot 要按上下文區分。"),
    ("DTL / DTR", "下降趨勢線 / 下降趨勢阻力。作者觀察突破、回測與阻力轉支撐。"),
    ("S/R flip", "原先阻力被突破後，回測時轉為支撐；仍須觀察能否守住。"),
    ("8-week EMA", "週線 8 週指數均線，係作者動能股回調嘅重要參考。"),
    ("Squat", "強勢股回退或橫行喺均線／結構支撐附近，形成收緊嘅待觸發狀態；"
     "唔係所有跌勢都叫 squat。"),
    ("Inside day / week", "當日／當週高低點處於前一週期高低點之內，"
     "用嚟觀察波動收縮同較清楚嘅觸發、失效區間。"),
    ("VCP / HTF", "波動收縮形態 / 高緊旗形。作者觀察強動能之後嘅淺回調、"
     "收緊與量縮，但兩者唔可以隨意互換。"),
    ("HVE / PEG", "歷史最高成交量 / 財報後跳空。HVE 係重要標籤，"
     "仍需結合事件發生喺底部、整理或長上漲後嘅唔同位置。"),
    ("ORB", "開盤區間突破；本檔案多頭例子用開盤第一根 30 分鐘 K 線高點作觸發。"),
    ("Chop / Trim / Core", "賣出部分、減倉與保留嘅核心倉位；"
     "用強勢中嘅兌現支付風險，再讓剩餘繼續跟隨。"),
    ("R / Free trade", "R 係初始計劃風險嘅計量；free trade 係"
     "已兌現利潤覆蓋剩餘計劃虧損嘅管理說法，結果仍取決於實際執行。"),
]

BOUNDARIES = [
    "「乾淨陽線」缺少可編程嘅實體、影線同最小波幅定義",
    "下方緩衝、滑點、訂單類型同頭寸公式未統一",
    "唔可以把每根低位陽線都當成呢個 setup",
    "減倉比例（1/3、1/2、3/4）係情境反應，唔係固定參數",
    "RS 評分同藍點算法未完整公開",
    "觀察帖 ≠ 已成交交易；後續市價 ≠ 賣出價",
]


CSS = """
<style>
.sf-hero{border:1px solid rgba(128,140,170,.28);border-radius:14px;
  padding:16px 18px;margin-bottom:14px;background:rgba(128,140,170,.07)}
.sf-hero h2{margin:0 0 8px;font-size:17px;color:inherit}
.sf-hero p{margin:0;font-size:12.5px;line-height:1.85;
  color:inherit;opacity:.8}
.sf-flow{display:flex;gap:6px;flex-wrap:wrap;margin-top:10px}
.sf-flow span{background:rgba(37,99,235,.16);border:1px solid rgba(37,99,235,.4);
  border-radius:6px;padding:3px 9px;font-size:11.5px;font-weight:700}
.sf-card{border:1px solid rgba(128,140,170,.22);border-radius:10px;
  padding:13px 14px;margin-bottom:12px;background:rgba(128,140,170,.04)}
.sf-h{display:flex;gap:8px;align-items:center;flex-wrap:wrap;
  margin-bottom:9px;font-size:14px;color:inherit}
.sf-n{background:#2563eb;color:#fff;border-radius:6px;padding:1px 7px;
  font-size:11.5px;font-weight:700}
.sf-one{background:rgba(37,99,235,.10);border-left:3px solid #2563eb;
  padding:9px 12px;border-radius:6px;font-size:12.5px;line-height:1.9;
  margin-bottom:10px;color:inherit}
.sf-r{display:flex;gap:8px;font-size:12.5px;line-height:1.8;
  padding:5px 0;border-top:1px dashed rgba(128,140,170,.22);
  flex-wrap:wrap;color:inherit}
.sf-k{flex:0 0 54px;min-width:54px;font-weight:700;opacity:.6}
.sf-v{flex:1;min-width:180px}
.sf-fail{background:rgba(220,38,38,.10);border:1px solid rgba(220,38,38,.35);
  border-radius:8px;padding:8px 12px;margin-top:9px;font-size:12.5px;
  line-height:1.8;color:inherit}
.sf-sys{background:rgba(34,197,94,.10);border:1px solid rgba(34,197,94,.35);
  border-radius:8px;padding:8px 12px;margin-top:7px;font-size:12.5px;
  line-height:1.8;color:inherit}
.dim{opacity:.6}
@media(max-width:700px){
  .sf-k{flex:0 0 100%;min-width:0}
  .sf-v{flex:0 0 100%;min-width:0}
  .sf-hero{padding:14px 13px 11px}
  .sf-card{padding:12px 12px}
}
</style>
"""


LAB_STEPS = [
    ("1", "環境", "先從 RS 候選清單出發，確認佢此前有強勢、"
     "大週期上存在可解釋嘅支撐。",
     "下跌段 + 支撐位置"),
    ("2", "等待", "等回落到支撐，然後觀察有冇收縮、量縮、"
     "波幅一級比一級細。未觸發前唔做嘢。",
     "SQUAT / VCP 區"),
    ("3", "觸發", "出現一根乾淨 30 分鐘陽線並收完；"
     "下一根越過該陽線高點 → 買入觸發。",
     "陽線 + 突破線"),
    ("4", "失效", "初始止損放喺同一根陽線低點下方。"
     "跌穿 = 呢次反轉失效，即刻走，唔等收市。",
     "止損紅線"),
]

REVIEW_STEPS = [
    ("01", "先寫環境",
     "市場同板塊有冇配合？點解呢隻股值得關注？",
     "對應系統：market_regime + sector rotation"),
    ("02", "再畫結構",
     "標記關鍵價位、回撤、收緊同可能嘅失效位置。",
     "對應系統：daily_plan 卡（pivot / 止蝕 / 觸發）"),
    ("03", "區分計劃與執行",
     "當時只係觀察，還是已經入場？邊啲條件真正發生咗？",
     "對應系統：ahead_tree（入場前寫死 10 步樹）"),
    ("04", "記錄反例",
     "失敗、止損、冇觸發嘅形態，同成功案例一樣有價值。",
     "對應系統：chase_audit / stop_counterfactual"),
]


def _lab_block():
    """互動式 Strategy Lab：4 步，純 CSS 切換（無 JS）

    ★ 2026-10-22 修：第一版 radio 藏喺 <label> 內，
      CSS `#sfstep1:checked ~ .sf-panes` 用唔到
      （radio 同 .sf-panes 唔係兄弟）→ 撳完標籤變色但冇內容。
      改為：radio 直接做 .sf-tabs 嘅子元素，label 用 for= 關聯。
    """
    radios = "".join(
        f'<input type="radio" name="sfstep" id="sfstep{n}"'
        f'{" checked" if n == "1" else ""}>'
        for n, _, _, _ in LAB_STEPS)
    btns = "".join(
        f'<label class="sf-lab-btn" for="sfstep{n}">{n} · {t}</label>'
        for n, t, _, _ in LAB_STEPS)
    panes = "".join(
        f'<div class="sf-pane sf-p{n}">'
        f'<div class="sf-paneT">{n} / {t}</div>'
        f'<div class="sf-paneD">{d}</div>'
        f'<div class="sf-paneM dim">圖上重點：{m}</div></div>'
        for n, t, d, m in LAB_STEPS)
    css = """
<style>
.sf-tabs > input{display:none}
.sf-lab-btn{display:inline-block;margin:0 6px 6px 0;cursor:pointer;
  padding:6px 11px;border-radius:8px;font-size:11.5px;font-weight:700;
  border:1px solid rgba(128,140,170,.35);
  background:rgba(128,140,170,.10);color:inherit}
#sfstep1:checked ~ .sf-labbtns label[for="sfstep1"],
#sfstep2:checked ~ .sf-labbtns label[for="sfstep2"],
#sfstep3:checked ~ .sf-labbtns label[for="sfstep3"],
#sfstep4:checked ~ .sf-labbtns label[for="sfstep4"]{
  background:#2563eb;color:#fff;border-color:#2563eb}
.sf-pane{display:none;border:1px solid rgba(128,140,170,.22);
  border-radius:8px;padding:11px 13px;margin-top:9px;
  background:rgba(128,140,170,.05)}
.sf-paneT{font-size:12.5px;font-weight:800;margin-bottom:6px}
.sf-paneD{font-size:12.5px;line-height:1.85}
.sf-paneM{font-size:11.5px;margin-top:7px}
#sfstep1:checked ~ .sf-panes .sf-p1,
#sfstep2:checked ~ .sf-panes .sf-p2,
#sfstep3:checked ~ .sf-panes .sf-p3,
#sfstep4:checked ~ .sf-panes .sf-p4{display:block}
</style>"""
    return (css + '<div class="card"><h2>🧪 Strategy Lab —— '
            '逐步睇一個 setup 點發生</h2><div class="body">'
            '<div class="note">揀一步睇該階段要睇咩。'
            '對應原文「選擇一種形態，逐步查看環境、等待、觸發和失效」。</div>'
            '<div class="sf-tabs">' + radios
            + '<div class="sf-labbtns">' + btns + '</div>'
            '<div class="sf-panes">' + panes + '</div></div>'
            '<div class="note">所有價格為示意，'
            '唔係歷史回測。觸發點同失效位置用嚟說明思路，'
            '唔代表作者固定交易參數。</div></div></div>')


def _review_block():
    rows = "".join(
        f'<div class="sf-r"><span class="sf-k">{n}</span>'
        f'<span class="sf-v"><b>{t}</b><br>{d}'
        f'<br><span class="dim">{s}</span></span></div>'
        for n, t, d, s in REVIEW_STEPS)
    return ('<div class="card"><h2>🔄 由觀察到複盤 '
            '<small>由本站整理，唔係作者原文系統</small></h2>'
            '<div class="body"><div class="note">'
            '一套學習用嘅複盤順序：幫你記錄條件，'
            '唔係宣稱一套交易系統。</div>' + rows + '</div></div>')


def build():
    hero = (
        '<div class="sf-hero">'
        '<h2>🏭 Setup Factory —— 技巧資料庫</h2>'
        '<p><b>一句總結</b>：先找已經證明強勢嘅領導股，等待它回到'
        '可定義風險嘅支撐，再用價格觸發驗證反轉；'
        '喺擴張中兌現部分，保留核心讓趨勢決定後續。<br>'
        '<span class="dim">來源：1ChartMaster 策略圖解（4,446 條歸檔帖文，'
        '2025-09-04 → 2026-10-06，9 個精選案例）。'
        '本站與作者無隸屬關係。</span></p>'
        '<div class="sf-flow">'
        '<span>① 相對強勢</span><span>→</span><span>② 支撐</span>'
        '<span>→</span><span>③ 轉折</span><span>→</span><span>④ 管理</span>'
        '</div></div>')

    cards = []
    for s in SETUP:
        looks = "".join(f'<div>· {x}</div>' for x in s["look"])
        cards.append(
            f'<div class="sf-card">'
            f'<div class="sf-h"><span class="sf-n">{s["n"]}</span>'
            f'{s["icon"]} {s["key"]}</div>'
            f'<div class="sf-one">{s["one"]}</div>'
            f'{s["svg"]()}'
            f'<div class="sf-r" style="margin-top:9px">'
            f'<span class="sf-k">睇咩</span>'
            f'<span class="sf-v">{looks}</span></div>'
            f'<div class="sf-fail">🛑 <b>失效</b>：{s["fail"]}</div>'
            f'<div class="sf-sys">🖥 <b>我哋系統</b>：{s["sys"]}</div>'
            f'</div>')

    case_rows = "".join(
        f'<tr><td class="l"><b>{t}</b><div class="dim" '
        f'style="font-size:10.5px">{k}｜{d}</div></td>'
        f'<td class="l">{v}</td>'
        f'<td class="l dim">{n}</td></tr>'
        for t, k, d, v, n in CASES)

    term_rows = "".join(
        f'<tr><td class="l"><b>{a}</b></td><td class="l">{b}</td></tr>'
        for a, b in TERMS)

    bnds = "".join(f'<div>· {x}</div>' for x in BOUNDARIES)

    return ("Setup Factory", CSS + hero + "".join(cards)
            + _lab_block() + _review_block() + (
        '<div class="card"><h2>🧪 九個真實案例 '
        '<small>計劃 / 觀察 / 成交 / 結果 要分開辨認</small></h2>'
        '<div class="body"><div class="scroll"><table><thead><tr>'
        '<th class="l">股票</th><th class="l">發生咩事</th>'
        '<th class="l">閱讀重點</th></tr></thead><tbody>'
        + case_rows + '</tbody></table></div></div></div>'
        '<div class="card"><h2>⚠ 邊界 —— 唔可以當成完整系統</h2>'
        '<div class="body"><div style="font-size:12.5px;line-height:1.95">'
        + bnds + '</div></div></div>'
        '<div class="card"><h2>📖 術語速查</h2>'
        '<div class="body"><div class="scroll"><table><thead><tr>'
        '<th class="l">術語</th><th class="l">解釋</th></tr></thead><tbody>'
        + term_rows + '</tbody></table></div></div></div>'))
