// Gate: 技能庫頁完整性（讀產物，不讀原始碼）
// 規則：任何一項唔過 → exit 1（gate 才會 FAIL）
import fs from "node:fs";
const html = fs.readFileSync("docs/skills.html", "utf8");
const cards = (html.match(/<details class="skcard"/g) || []).length;
const hasSearch = html.includes('id="skq"');
const hasChips = html.includes("skchip");
const emptyBody = (html.match(/<div class="skbody"><\/div>/g) || []).length;
const problems = [];
if (cards < 100) problems.push(`card count too low: ${cards}`);
if (!hasSearch) problems.push("search input missing");
if (!hasChips) problems.push("category chips missing");
if (emptyBody > 0) problems.push(`empty card bodies: ${emptyBody}`);
if (problems.length) {
  console.log(`skills page FAIL ${problems.join("; ")}`);
  process.exit(1);
}
console.log(`skills page ok ${cards} cards`);
