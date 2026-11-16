// Render the 9:16 shorts. Usage: node render_shorts.mjs <framesDir> <outDir> <id> [workers=4] [stillsSeconds=comma,list]
import { chromium } from "playwright";
import { spawn } from "node:child_process";
import path from "node:path";
import fs from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";
const here = path.dirname(fileURLToPath(import.meta.url));
const [framesDir, outDir, id, workersArg = "4", stills] = process.argv.slice(2);
const FPS = 25, W = Number(workersArg);
const url = pathToFileURL(path.join(here, "short.html")).href + "?id=" + id;
fs.mkdirSync(outDir, { recursive: true });
const frameFile = t => pathToFileURL(path.join(framesDir, String(Math.round(t * FPS) + 1).padStart(5, "0") + ".jpg")).href;
async function open() {
  const browser = await chromium.launch();
  const p = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  p.on("pageerror", e => console.error("pageerror:", e.message));
  await p.goto(url); await p.evaluate(() => document.fonts.ready);
  return { browser, p };
}
const meta = await (async () => { const { browser, p } = await open(); const m = await p.evaluate(() => window.SHORT); await browser.close(); return m; })();
fs.writeFileSync(path.join(outDir, `short${id}.json`), JSON.stringify(meta));
const TOTAL = Math.round(meta.DUR * FPS);
const srcOf = async (p, f) => { const t = f / FPS; return t < meta.VDUR ? frameFile(await p.evaluate(t => window.SRC(t), t)) : null; };
if (stills) {
  const { browser, p } = await open();
  for (const s of stills.split(",").map(Number)) { const f = Math.round(s * FPS); await p.evaluate(([f, s]) => window.__renderFrame(f, s), [f, await srcOf(p, f)]); await p.screenshot({ path: path.join(outDir, `s${id}_${s}.png`) }); }
  await browser.close(); process.exit(0);
}
async function worker(i) {
  const a = Math.floor(TOTAL * i / W), b = Math.floor(TOTAL * (i + 1) / W);
  const { browser, p } = await open();
  const ff = spawn("ffmpeg", ["-v", "error", "-y", "-f", "image2pipe", "-framerate", String(FPS), "-c:v", "mjpeg", "-i", "-", "-c:v", "libx264", "-preset", "medium", "-crf", "18", "-pix_fmt", "yuv420p", path.join(outDir, `s${id}_seg${i}.mp4`)], { stdio: ["pipe", "inherit", "inherit"] });
  let last = null;
  for (let f = a; f < b; f++) {
    const s = (await srcOf(p, f)) ?? last; last = s;
    await p.evaluate(([f, s]) => window.__renderFrame(f, s), [f, s]);
    const buf = await p.screenshot({ type: "jpeg", quality: 94 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once("drain", r));
  }
  ff.stdin.end(); await new Promise(r => ff.on("close", r)); await browser.close();
}
await Promise.all([...Array(W).keys()].map(worker));
fs.writeFileSync(path.join(outDir, `s${id}_segs.txt`), [...Array(W).keys()].map(i => `file 's${id}_seg${i}.mp4'`).join("\n") + "\n");
console.log("short", id, "frames", TOTAL, "dur", meta.DUR.toFixed(2));
