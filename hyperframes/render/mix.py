#!/usr/bin/env python3
"""Audio mix: original avatar narration (normalized to -14 LUFS) + ElevenLabs music bed + frame-synced SFX.
Usage: python3 mix.py <out.wav>
Reads ../cues.json. The narration is the source video's own voice, untouched apart from loudness.
"""
import json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, "..")
cues = json.load(open(os.path.join(ROOT, "cues.json")))
out = sys.argv[1]
voice_src = os.path.join(ROOT, cues["voice"]["source"])
music_src = os.path.join(ROOT, cues["music"]["file"])
DUR = cues["duration"]


def loudness(path, extra=""):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-vn", "-af",
                        f"{extra}loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return json.loads(r[r.rindex("{"):r.rindex("}") + 1])


def peak_db(path):
    r = subprocess.run(["ffmpeg", "-hide_banner", "-i", path, "-af", "volumedetect", "-f", "null", "-"],
                       capture_output=True, text=True).stderr
    return float(re.search(r"max_volume: (-?[\d.]+) dB", r).group(1))


# Voice: two-pass loudnorm to -14 LUFS (linear, so the performance is unchanged).
v = loudness(voice_src)
voice_f = (f"loudnorm=I={cues['voice']['targetLUFS']}:TP=-1.5:LRA=11:measured_I={v['input_i']}:"
           f"measured_TP={v['input_tp']}:measured_LRA={v['input_lra']}:measured_thresh={v['input_thresh']}:"
           f"offset={v['target_offset']}:linear=true,aresample=48000,apad,atrim=end={DUR}")

# Music: bed sits at bedDb LUFS, swells to ctaDb at the CTA, hard-stops on the key warning.
m = cues["music"]
music_lufs = float(loudness(music_src, f"atrim=start={m['trimStart']},")["input_i"])
bed_gain = m["bedDb"] - music_lufs
swell = m["ctaDb"] - m["bedDb"]
expr = f"if(lt(t,{m['ctaAt']}),0,min(1,(t-{m['ctaAt']})/1.5)*{swell})"
if "endLift" in m:   # lift the bed under the end card so the closing chord lands
    e = m["endLift"]; lift = e["db"] - m["bedDb"]
    expr = f"if(lt(t,{e['at']}),{expr},{swell}+min(1,(t-{e['at']})/0.8)*({lift}-{swell}))"
for hs in m["hardStops"]:
    a, b = hs["from"], hs["to"]
    # duck to silence in 0.08 s, hold, then bring the groove back over 0.6 s
    expr = f"if(between(t,{a},{b}),-60*min(1,(t-{a})/0.08),if(between(t,{b},{b}+0.6),-60*(1-(t-{b})/0.6),{expr}))"
music_f = (f"atrim=start={m['trimStart']},asetpts=PTS-STARTPTS,aresample=48000,"
           f"adelay={int(m.get('delay', 0) * 1000)}:all=1,"
           f"volume={bed_gain:.2f}dB,volume='pow(10,({expr})/20)':eval=frame,"
           f"afade=t=in:d=1.2,atrim=end={DUR}")

inputs = ["-i", voice_src, "-i", music_src]
graph = [f"[0:a]{voice_f}[v]", f"[1:a]{music_f}[m]"]
labels = ["[v]", "[m]"]
peaks = {}
for i, s in enumerate(cues["sfx"]):
    p = os.path.join(ROOT, "assets", "sfx", s["file"] + ".mp3")
    peaks.setdefault(p, peak_db(p))
    inputs += ["-i", p]
    gain = s["db"] - peaks[p]                      # normalise each SFX peak, then apply cue level
    rate = s.get("rate", 1.0)
    pitch = f"asetrate=44100*{rate},aresample=48000," if rate != 1.0 else "aresample=48000,"
    ms = int(round(s["t"] * 1000))
    graph.append(f"[{i + 2}:a]{pitch}volume={gain:.2f}dB,adelay={ms}|{ms}[s{i}]")
    labels.append(f"[s{i}]")
graph.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:dropout_transition=0,"
             f"alimiter=limit=0.89:level=false,atrim=end={DUR}[out]")

subprocess.run(["ffmpeg", "-v", "error", "-y", *inputs, "-filter_complex", ";".join(graph),
                "-map", "[out]", "-ac", "2", "-ar", "48000", out], check=True)
print("mixed ->", out)
