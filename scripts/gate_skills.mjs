// Gate: 技能庫頁完整性（讀產物，不讀原始碼）
import fs from "node:fs";
const html = fs.readFileSync("docs/skills.html", "utf8");
const cards = (html.match(/<details class="skcard"/g) || []).length;
const hasSearch = html.includes('id="skq"');
const hasChips = html.includes("skchip");
if (cards !== 103) { console.log(`skills count FAIL ${cards}`); process.exit(0); }
if (!hasSearch || !hasChips) { console.log("ui controls FAIL"); process.exit(0); }
console.log(`skills page ok ${cards}`);
