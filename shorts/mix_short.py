#!/usr/bin/env python3
"""Mix one short: original narration segments + ElevenLabs clone CTA + music bed + SFX.
Usage: python3 mix_short.py <meta.json from render_shorts.mjs> <out.wav>"""
import json, os, re, subprocess, sys
HERE = os.path.dirname(os.path.abspath(__file__))
HF = os.path.join(HERE, "..", "hyperframes")
SRC = os.path.join(HERE, "..", "Stop Paying Fake Medicare Lab Bills_1080p.mp4")
meta = json.load(open(sys.argv[1])); out = sys.argv[2]
sid, DUR, CTA_VO, VDUR = meta["id"], meta["DUR"], meta["CTA_VO"], meta["VDUR"]
MUSIC = os.path.join(HF, "assets/music/usafacts-bed-110bpm.mp3")
CTA = os.path.join(HERE, f"assets/cta_vo_{sid}.mp3")

def lufs(path, pre=""):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-vn", "-af", f"{pre}ebur128", "-f", "null", "-"], capture_output=True, text=True).stderr
    return float(re.findall(r"I:\s+(-?[\d.]+) LUFS", r)[-1])
def peak(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "volumedetect", "-f", "null", "-"], capture_output=True, text=True).stderr
    return float(re.search(r"max_volume: (-?[\d.]+) dB", r).group(1))

g = []; ins = ["-i", SRC, "-i", CTA, "-i", MUSIC]
# narration: the EDL segments with 15 ms fades at each cut
segs = []
for i, (a, b) in enumerate(meta["edl"]):
    g.append(f"[0:a]atrim={a}:{b},asetpts=PTS-STARTPTS,aresample=48000,afade=t=in:d=0.015,afade=t=out:st={b-a-0.015:.3f}:d=0.015[n{i}]")
    segs.append(f"[n{i}]")
g.append(f"{''.join(segs)}concat=n={len(segs)}:v=0:a=1[nar]")
voice_gain = -14 - lufs(SRC)  # same gain as the main video's normalisation
g.append(f"[nar]volume={voice_gain:.2f}dB,apad,atrim=end={DUR}[v]")
# CTA voice-over (ElevenLabs clone) matched to -14 LUFS
cta_gain = -14 - lufs(CTA)
ms = int(CTA_VO * 1000)
g.append(f"[1:a]aresample=48000,volume={cta_gain:.2f}dB,adelay={ms}:all=1,apad,atrim=end={DUR}[c]")
# music bed: quiet under speech, lifts on the CTA card, fades out at the end
off = [0, 30, 95, 150, 205][sid]
m_lufs = lufs(MUSIC, f"atrim=start={off}:duration=60,")
bed = -40 - m_lufs
lift = 6
expr = f"if(lt(t,{VDUR:.2f}),0,min(1,(t-{VDUR:.2f})/0.8)*{lift})"
g.append(f"[2:a]atrim=start={off},asetpts=PTS-STARTPTS,aresample=48000,volume={bed:.2f}dB,volume='pow(10,({expr})/20)':eval=frame,"
         f"afade=t=in:d=0.8,afade=t=out:st={DUR-1.4:.2f}:d=1.4,atrim=end={DUR}[m]")
labels = ["[v]", "[c]", "[m]"]
pk = {}
for i, (t, f, db) in enumerate(meta["sfx"]):
    p = os.path.join(HF, "assets/sfx", f + ".mp3"); pk.setdefault(p, peak(p))
    ins += ["-i", p]; ms = int(t * 1000)
    g.append(f"[{i+3}:a]aresample=48000,volume={db - pk[p]:.2f}dB,adelay={ms}:all=1[s{i}]"); labels.append(f"[s{i}]")
g.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0,alimiter=limit=0.89:level=false,atrim=end={DUR}[out]")
subprocess.run(["ffmpeg", "-v", "error", "-y", *ins, "-filter_complex", ";".join(g), "-map", "[out]", "-ac", "2", "-ar", "48000", out], check=True)
print("mixed", out)
