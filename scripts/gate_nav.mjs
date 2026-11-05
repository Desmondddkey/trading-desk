// Gate: 新頁有側欄入口
import fs from "node:fs";
const pages = ["index.html", "skills.html", "lukplaybook.html"];
const need = ["skills.html", "lukplaybook.html"];
const problems = [];
for (const p of pages) {
  const html = fs.readFileSync(`docs/${p}`, "utf8");
  for (const n of need) {
    if (!html.includes(`href="${n}`)) problems.push(`${p} 冇連去 ${n}`);
  }
}
if (problems.length) { console.log(`nav entries FAIL ${problems.join("; ")}`); process.exit(1); }
console.log("nav entries ok");
