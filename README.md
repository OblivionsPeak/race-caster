# RaceCaster — the AI commentary booth for iRacing

RaceCaster watches your iRacing session's telemetry, works out what matters —
overtakes, brewing battles, pit stops, fastest laps, flags — and **speaks
professional play-by-play over your stream** with a neural voice. No cloud
account, no subscription: it runs on your PC next to the sim.

**Landing page:** https://oblivionspeak.github.io/race-caster/

## Hear it in 2 minutes (no iRacing needed)

```bat
setup.bat      :: one-time: venv + dependencies
run-demo.bat   :: the booth commentates a simulated 6-lap sprint
```

## Live mode

```bat
run-live.bat
```

Start it before or during any session — practice, race, or **spectating**
(spectating a league broadcast is where it shines). It waits for the sim,
connects, and starts calling the race.

- Works while *you* race too: it commentates what the timing screens show,
  including your own battles.
- **OBS captions:** point a Text (GDI+) source at `racecaster_caption.txt` —
  it always contains the line currently being spoken.
- To mix the voice into your stream, capture desktop audio (or route Python
  through a virtual cable and add it as a dedicated OBS audio source).

## Options

| Flag | Meaning |
|---|---|
| `--voice en-US-GuyNeural` | any [edge-tts voice](https://gist.github.com/BettyJJ/17cbaa1de96235a7f5773b8690a20462) — Ryan (GB) is the default booth voice |
| `--rate 12` | speech speed offset in % |
| `--caption path.txt` | caption file location |
| `--mute` | console + captions only |
| `--demo --demo-speed 2` | faster demo |

## How it works

A 2 Hz telemetry loop (via `pyirsdk`) ranks the field and computes intervals.
An event engine with priorities, per-event cooldowns, and anti-repetition
phrase banks decides what deserves airtime — so the booth calls the lead
battle, not every midfield twitch, and never says the same sentence twice in
a row. Voice is Microsoft neural TTS via `edge-tts` (free, needs internet),
with an offline SAPI fallback.

## Roadmap

- **Replay narrator** — point it at a saved replay, get a commentated
  highlight reel rendered to video
- **Auto-director pairing** — camera control for spectator/broadcast PCs
- **Second voice** — color commentator with LLM-generated race storylines
- **League mode** — driver nicknames, championship context, team names

## Requirements

Windows, Python 3.10+, iRacing (for live mode). Voice quality needs an
internet connection (falls back to offline SAPI without one).

---

Free and open source. Built by [OblivionsPeak](https://github.com/OblivionsPeak) —
if the booth makes your stream better, tips welcome on
[Ko-fi](https://ko-fi.com/metalprophecymedia). ♥
