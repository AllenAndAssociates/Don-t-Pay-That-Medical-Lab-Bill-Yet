# Don't Pay That Medical Lab Bill Yet — HyperFrames composition

Motion-graphics edit of `Stop Paying Fake Medicare Lab Bills_1080p.mp4` (the HeyGen avatar take), built to the
16:9 production blueprint and styled to match the Allen & Associates "16 Things That Quietly Changed in the 2027
Medicare Handbook" video: full-frame avatar that slides left, navy stage panel with gold chapter tabs, white cards,
amber critical-warning banners, a flip-board interstitial and the navy logo end card.

The narration is the original voice from the avatar video (only loudness-normalized to -14 LUFS).
The music bed and sound effects were generated with ElevenLabs.

## Files

| Path | What it is |
| --- | --- |
| `index.html` | The composition (GSAP timeline on `window.__timelines.main`, 1920×1080, 25 fps, 300 s) |
| `cues.json` | Music levels, hard stop, and every sound-effect cue (time, file, level) |
| `assets/clips/` | Official source images shown on screen (see Sources) |
| `assets/music/`, `assets/sfx/` | ElevenLabs music bed and sound effects |
| `assets/logo.jpg` | Allen & Associates logo |
| `render/render.mjs` | Frame-accurate Playwright renderer |
| `render/mix.py` | Audio mix (voice + music + SFX) driven by `cues.json` |

Open `index.html` in a browser and click to preview it in sync with the avatar video.

## Chapter timing (synced to the narration's word timestamps)

| Time | Section |
| --- | --- |
| 0:00 | Hook: $874.46 invoice → "Actual amount owed $0.00" |
| 0:20 | Authority card, then today's breakdown |
| 0:42 | 1 · The Trap: Aug 13 → Aug 21 → Sep 8 timeline |
| 1:16 | Flip board, then 2 · $874 vs $0 |
| 1:56 | 3 · Medicare.gov: real homepage and login screenshots, 4 steps, Golden Rule banner (music hard stop) |
| 2:39 | 4 · The ABN Rule: official CMS-R-131 form with highlights |
| 3:18 | Never-sign-blank warning banner, then owe $0 vs wellness-test exception |
| 3:54 | 5 · Action Plan checklist |
| 4:31 | Remember, then Medicare.gov / Allen & Associates CTA |
| 4:57 | End card (to 5:00) |

## Sources for on-screen material

- `medicare_home.png`, `medicare_login.png`: screenshots of https://www.medicare.gov/ and
  https://www.medicare.gov/account/login, captured 2026-11-16. "Check My Claims" is behind a personal login,
  so it can't be captured publicly; steps 3–4 are shown as checklist text.
- `cms_abn_form.png`: page 1 of the official *Advance Beneficiary Notice of Non-coverage (ABN)*,
  Form CMS-R-131 (Exp. 03/31/2029), from https://www.cms.gov/medicare/forms-notices/beneficiary-notices-initiative/ffs-abn.

## Rebuild

```bash
mkdir -p /tmp/frames && ffmpeg -i "../Stop Paying Fake Medicare Lab Bills_1080p.mp4" -q:v 3 /tmp/frames/%05d.jpg
```

```bash
node render/render.mjs /tmp/frames /tmp/out 4 && (cd /tmp/out && ffmpeg -f concat -safe 0 -i segments.txt -c copy video.mp4)
```

```bash
python3 render/mix.py /tmp/out/mix.wav
```

```bash
ffmpeg -i /tmp/out/video.mp4 -i /tmp/out/mix.wav -map 0:v -map 1:a -c:v copy -c:a aac -b:a 192k -movflags +faststart final.mp4
```

`render.mjs` needs Playwright with Chromium (`render/node_modules/playwright` can be a symlink to a global install).
