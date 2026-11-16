// Frame-accurate renderer for the composition.
// Usage: node render.mjs <framesDir> <outDir> [workers=4] [onlyFrames=comma,list]
// framesDir: full 1920x1080 avatar frames extracted from the source video,
//            named 00001.jpg ... (see README for the ffmpeg command).
import { chromium } from "playwright";
import { spawn } from "node:child_process";
import path from "node:path";
import fs from "node:fs";
import { fileURLToPath, pathToFileURL } from "node:url";

const here = path.dirname(fileURLToPath(import.meta.url));
const page = pathToFileURL(path.join(here, "..", "index.html")).href + "?render=1";
const [framesDir, outDir, workersArg = "4", only] = process.argv.slice(2);
const FPS = 25, DUR = 300.0, TOTAL = Math.round(DUR * FPS);
const SRC_N = fs.readdirSync(framesDir).filter(f => f.endsWith(".jpg")).length; // source runs 297.68 s; last frame holds under the end card
const W = Number(workersArg);
fs.mkdirSync(outDir, { recursive: true });
const src = f => pathToFileURL(path.join(framesDir, String(Math.min(f + 1, SRC_N)).padStart(5, "0") + ".jpg")).href;

async function open() {
  const browser = await chromium.launch();
  const p = await browser.newPage({ viewport: { width: 1920, height: 1080 }, deviceScaleFactor: 1 });
  p.on("pageerror", e => console.error("pageerror:", e.message));
  await p.goto(page);
  await p.evaluate(() => document.fonts.ready);
  return { browser, p };
}

if (only) {
  const { browser, p } = await open();
  for (const f of only.split(",").map(Number)) {
    await p.evaluate(([f, s]) => window.__renderFrame(f, s), [f, src(f)]);
    await p.screenshot({ path: path.join(outDir, `still_${String(f).padStart(5, "0")}.png`) });
  }
  await browser.close();
  process.exit(0);
}

async function worker(i) {
  const start = Math.floor((TOTAL * i) / W), end = Math.floor((TOTAL * (i + 1)) / W);
  const { browser, p } = await open();
  const ff = spawn("ffmpeg", ["-v", "error", "-y", "-f", "image2pipe", "-framerate", String(FPS), "-c:v", "mjpeg", "-i", "-",
    "-c:v", "libx264", "-preset", "medium", "-crf", "17", "-pix_fmt", "yuv420p", "-r", String(FPS),
    path.join(outDir, `seg_${i}.mp4`)], { stdio: ["pipe", "inherit", "inherit"] });
  for (let f = start; f < end; f++) {
    await p.evaluate(([f, s]) => window.__renderFrame(f, s), [f, src(f)]);
    const buf = await p.screenshot({ type: "jpeg", quality: 95 });
    if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once("drain", r));
    if ((f - start) % 250 === 0) console.log(`w${i} ${f - start}/${end - start}`);
  }
  ff.stdin.end();
  await new Promise(r => ff.on("close", r));
  await browser.close();
}
await Promise.all([...Array(W).keys()].map(worker));
fs.writeFileSync(path.join(outDir, "segments.txt"), [...Array(W).keys()].map(i => `file 'seg_${i}.mp4'`).join("\n") + "\n");
console.log("done", TOTAL, "frames");
