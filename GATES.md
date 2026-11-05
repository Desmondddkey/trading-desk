# Gates: 技能庫頁交付

OWNS: docs/skills.html, skills_page.py, build_site.py, scripts/gate_skills.mjs

Scope: 技能庫頁上線，列出全部已安裝 skill，可搜尋、可按分類篩選，每晚自動重掃。

- [x] G1: 技能庫頁列出 ≥100 個 skill，且有搜尋框與分類標籤
  CHECK: node scripts/gate_skills.mjs
  EXPECT: skills page ok
  EVIDENCE: automatic-evidence=v1; definition-sha256=5e4138d37b50dfad8fc2907c95d4359ebea056d25fcb7658e1d060f99ff51dc4; exit=0; EXPECT=matched; output-sha256=9be0ba00488ccab1f731eafccc9d387058e543d8c3012d17f9bfed269310b185; output-bytes=25; shell=C:\Windows\system32\cmd.exe; cwd=C:\Users\rain0\trading-os-web; path=e43ec0339715/51 entries

- [x] G2: 側欄有入口（技能庫 + Luk 手冊），不是孤兒頁
  CHECK: node scripts/gate_nav.mjs
  EXPECT: nav entries ok
  EVIDENCE: automatic-evidence=v1; definition-sha256=c298624a4e88cb27ee1710107ab57824ba412155f79bc94794ab9e37d64b07f4; exit=0; EXPECT=matched; output-sha256=03f6d0605c00dd3ee4cb74b8fdee9eae05e087a08f67f47d884426d49c3e1d08; output-bytes=15; shell=C:\Windows\system32\cmd.exe; cwd=C:\Users\rain0\trading-os-web; path=e43ec0339715/51 entries
