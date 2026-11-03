# Gates: skills 頁交付

OWNS: docs/skills.html, skills_page.py

Scope: 技能庫頁上線，包含全部已安裝 skill 且有搜尋與分類。

- [x] G1: 頁面存在且列出 103 個 skill
  CHECK: node scripts/gate_skills.mjs
  EXPECT: skills page ok
  EVIDENCE: automatic-evidence=v1; definition-sha256=5e4138d37b50dfad8fc2907c95d4359ebea056d25fcb7658e1d060f99ff51dc4; exit=0; EXPECT=matched; output-sha256=982bd5af2e89ba472dc87672e0014bc3c65d851c488f20c3d9a63990f8a9946d; output-bytes=19; shell=C:\Windows\system32\cmd.exe; cwd=C:\Users\rain0\trading-os-web; path=4fce7c4c5438/48 entries

- [x] G2: 頁面有搜尋框同分類標籤
  CHECK: node -e "const s=require('fs').readFileSync('docs/skills.html','utf8');console.log(s.includes('skchip')&&s.includes('id=\"skq\"')?'ui controls ok':'ui controls FAIL')"
  EXPECT: ui controls ok
  EVIDENCE: automatic-evidence=v1; definition-sha256=4371c54d7e3da126bd963d428e8858bfdb44701282453bec137a1f7107ea664a; exit=0; EXPECT=matched; output-sha256=33459c2beb6e3fa3aeec077b3cd764a72cf603e0689eb0f836cf7d5757a9395b; output-bytes=15; shell=C:\Windows\system32\cmd.exe; cwd=C:\Users\rain0\trading-os-web; path=4fce7c4c5438/48 entries
