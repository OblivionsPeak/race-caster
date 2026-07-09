#!/usr/bin/env python3
"""RaceCaster — the AI commentary booth for iRacing.

Watches live telemetry (or a built-in demo race), detects what matters —
overtakes, battles, pit stops, fastest laps, flags — and SPEAKS professional
play-by-play over your stream with a neural voice.

Usage:
  python racecaster.py            # live: attach to a running iRacing session
  python racecaster.py --demo     # no sim needed: commentate a simulated race
  python racecaster.py --voice en-GB-RyanNeural --caption captions.txt

The caption file always holds the line currently being spoken — point an OBS
Text (GDI+) source at it for on-screen captions.

Everything runs locally. Voice via edge-tts (free Microsoft neural voices,
needs internet) with an offline pyttsx3/SAPI fallback.
"""
import argparse
import asyncio
import queue
import random
import sys
import tempfile
import threading
import time
from pathlib import Path

from phrases import PHRASES, PRIORITY, COOLDOWN

# ---------------------------------------------------------------- speaker

class Speaker:
    """Sequential TTS queue: edge-tts -> mp3 -> pygame; SAPI fallback."""

    def __init__(self, voice, rate, caption_path, mute=False):
        self.voice = voice
        self.rate = rate
        self.caption_path = Path(caption_path) if caption_path else None
        self.mute = mute
        self.q = queue.Queue()
        self.speaking = False
        self.edge_ok = True
        threading.Thread(target=self._worker, daemon=True).start()

    def say(self, text, priority):
        self.q.put((priority, time.time(), text))

    def _caption(self, text):
        if self.caption_path:
            try:
                self.caption_path.write_text(text, encoding="utf-8")
            except OSError:
                pass

    def _worker(self):
        while True:
            priority, born, text = self.q.get()
            try:
                # stale low-priority lines get dropped if the booth is backed up
                if time.time() - born > 12 and priority < 50:
                    continue
                self.speaking = True
                print(f"  [on air]  {text}")
                self._caption(text)
                if not self.mute:
                    self._speak_blocking(text)
                self._caption("")
            except Exception as e:
                # the booth must never die mid-broadcast
                try:
                    print(f"  (speaker hiccup: {e})")
                except Exception:
                    pass
            finally:
                self.speaking = False
                self.q.task_done()   # lets drain() wait for lines to finish airing

    def drain(self):
        """Block until every queued line has fully aired."""
        self.q.join()

    def _speak_blocking(self, text):
        if self.edge_ok:
            try:
                self._edge_speak(text)
                return
            except Exception as e:
                print(f"  (edge-tts unavailable — {e}; falling back to SAPI)")
                self.edge_ok = False
        try:
            import pyttsx3
            eng = pyttsx3.init()
            eng.say(text)
            eng.runAndWait()
        except Exception:
            pass  # mute-equivalent: caption/console already delivered it

    def _edge_speak(self, text):
        import edge_tts
        import pygame
        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            path = tmp.name
        rate_str = f"{'+' if self.rate >= 0 else ''}{self.rate}%"

        async def _save():
            await edge_tts.Communicate(text, self.voice, rate=rate_str).save(path)

        asyncio.run(_save())
        if not pygame.mixer.get_init():
            pygame.mixer.init()
        pygame.mixer.music.load(path)
        pygame.mixer.music.play()
        while pygame.mixer.music.get_busy():
            time.sleep(0.05)
        pygame.mixer.music.unload()
        try:
            Path(path).unlink()
        except OSError:
            pass

# ---------------------------------------------------------------- phrasing

class PhraseEngine:
    def __init__(self):
        self.last_template = {}

    @staticmethod
    def _shorten(name):
        parts = str(name).split()
        return parts[-1] if len(parts) > 1 else str(name)

    def line(self, event, **slots):
        bank = PHRASES.get(event)
        if not bank:
            return None
        options = [t for t in bank if t != self.last_template.get(event)] or bank
        template = random.choice(options)
        self.last_template[event] = template
        for k in ("name", "name2", "name3"):
            if k in slots:
                slots[k] = self._shorten(slots[k])
        try:
            return template.format(**slots)
        except (KeyError, IndexError):
            return None

# ---------------------------------------------------------------- events

class Booth:
    """Turns a stream of race snapshots into prioritized commentary."""

    def __init__(self, speaker):
        self.speaker = speaker
        self.phr = PhraseEngine()
        self.cool = {}
        self.prev = None           # previous snapshot
        self.battle_streak = {}    # pos -> consecutive close-gap samples
        self.best_lap = None
        self.said_half = False
        self.said_white = False
        self.done = False

    def _fire(self, event, **slots):
        now = time.time()
        if now - self.cool.get(event, 0) < COOLDOWN.get(event, 10):
            return
        line = self.phr.line(event, **slots)
        if line:
            self.cool[event] = now
            self.speaker.say(line, PRIORITY.get(event, 10))

    @staticmethod
    def _gap_str(gap):
        return f"{gap:.1f} seconds" if gap >= 1.0 else f"{gap:.1f} of a second".replace("0.", "just 0.")

    def update(self, snap):
        """snap: { order: [names best->worst], gaps: {name: interval-to-car-ahead},
                   onpit: set(names), lastlaps: {name: sec}, state: 'pre|racing|checkered',
                   lap, total_laps, yellow: bool }"""
        if self.done:
            return
        prev = self.prev
        self.prev = snap
        order = snap["order"]

        if prev is None:
            return

        # flags / state transitions
        if prev["state"] == "pre" and snap["state"] == "racing":
            self._fire("green_flag", n_cars=len(order))
        if snap.get("yellow") and not prev.get("yellow"):
            self._fire("yellow_flag")
        if prev.get("yellow") and not snap.get("yellow") and snap["state"] == "racing":
            self._fire("green_restart")
        if snap["state"] == "checkered" and prev["state"] != "checkered":
            self._fire("checkered", name=order[0])
            if len(order) >= 3:
                self._fire("podium", name=order[0], name2=order[1], name3=order[2])
            self.done = True
            return

        if snap["state"] != "racing":
            return

        # leader change / overtakes: compare positions
        pprev = {n: i for i, n in enumerate(prev["order"])}
        for pos_idx, name in enumerate(order[:10]):
            was = pprev.get(name)
            if was is None or was <= pos_idx:
                continue
            # name moved up — who did they displace?
            displaced = prev["order"][pos_idx] if pos_idx < len(prev["order"]) else None
            if displaced is None or displaced == name:
                continue
            # ignore position changes caused by the other car pitting
            if displaced in snap["onpit"]:
                continue
            if pos_idx == 0:
                self._fire("overtake_lead", name=name, name2=displaced)
            else:
                self._fire("overtake", name=name, name2=displaced,
                           pos=pos_idx + 1, pos2=pos_idx + 2)
            break  # one overtake call per tick keeps the booth coherent

        # battles: sustained close gaps in the top 8
        for pos_idx in range(1, min(8, len(order))):
            chaser = order[pos_idx]
            ahead = order[pos_idx - 1]
            gap = snap["gaps"].get(chaser)
            if gap is None or chaser in snap["onpit"] or ahead in snap["onpit"]:
                self.battle_streak[pos_idx] = 0
                continue
            if gap < 0.8:
                self.battle_streak[pos_idx] = self.battle_streak.get(pos_idx, 0) + 1
                if self.battle_streak[pos_idx] == 3:
                    self._fire("battle", name=ahead, name2=chaser,
                               pos=pos_idx, gap=self._gap_str(gap))
            else:
                self.battle_streak[pos_idx] = 0

        # pit lane comings and goings (top 10 only)
        for name in order[:10]:
            pos = order.index(name) + 1
            if name in snap["onpit"] and name not in prev["onpit"]:
                self._fire("pit_in", name=name, pos=pos)
            if name not in snap["onpit"] and name in prev["onpit"]:
                self._fire("pit_out", name=name)

        # fastest lap
        for name, lap_t in snap["lastlaps"].items():
            if lap_t and lap_t > 0 and (self.best_lap is None or lap_t < self.best_lap):
                already = self.best_lap is not None
                self.best_lap = lap_t
                if already:  # don't call the first valid lap of the race
                    m, s = divmod(lap_t, 60)
                    self._fire("fastest_lap", name=name,
                               time=f"{int(m)}:{s:06.3f}" if m else f"{s:.3f}")

        # milestones
        total = snap.get("total_laps") or 0
        if total and not self.said_half and snap["lap"] >= total / 2:
            self.said_half = True
            self._fire("halfway", name=order[0])
        if total and not self.said_white and snap["lap"] >= total and len(order) > 1:
            self.said_white = True
            self._fire("white_flag", name=order[0], name2=order[1])

        # leader stretching away
        if len(order) > 1:
            lead_gap = snap["gaps"].get(order[1])
            if lead_gap and lead_gap > 5.0:
                self._fire("leader_pulling_away", name=order[0],
                           gap=self._gap_str(lead_gap))

# ---------------------------------------------------------------- live source

def live_loop(booth, hz=2.0):
    import irsdk
    ir = irsdk.IRSDK()
    print("Waiting for iRacing…")
    while not (ir.startup() and ir.is_initialized and ir.is_connected):
        time.sleep(2)
    print("Connected. The booth is live.")
    while True:
        try:
            ir.freeze_var_buffer_latest()
            drivers = (ir["DriverInfo"] or {}).get("Drivers", [])
            names = {d.get("CarIdx"): d.get("UserName", f"Car {d.get('CarIdx')}")
                     for d in drivers if d.get("CarIsPaceCar") != 1}
            positions = ir["CarIdxPosition"] or []
            f2 = ir["CarIdxF2Time"] or []
            onpit_arr = ir["CarIdxOnPitRoad"] or []
            lastlap = ir["CarIdxLastLapTime"] or []

            ranked = sorted((p, i) for i, p in enumerate(positions)
                            if p and p > 0 and i in names)
            order = [names[i] for _, i in ranked]
            gaps = {}
            for k in range(1, len(ranked)):
                i_ahead, i_this = ranked[k - 1][1], ranked[k][1]
                if k - 1 < len(f2) and i_this < len(f2) and f2[i_this] and f2[i_ahead] is not None:
                    gaps[names[i_this]] = max(0.0, f2[i_this] - f2[i_ahead])
            onpit = {names[i] for i in names if i < len(onpit_arr) and onpit_arr[i]}
            lastlaps = {names[i]: lastlap[i] for i in names
                        if i < len(lastlap) and lastlap[i] and lastlap[i] > 0}

            state_raw = ir["SessionState"]          # 4 = racing, 6 = checkered
            flags = ir["SessionFlags"] or 0
            state = ("checkered" if state_raw == 6
                     else "racing" if state_raw == 4 else "pre")
            snap = {
                "order": order, "gaps": gaps, "onpit": onpit,
                "lastlaps": lastlaps, "state": state,
                "lap": ir["RaceLaps"] or 0,
                "total_laps": ir["SessionLapsTotal"] if (ir["SessionLapsTotal"] or 0) < 30000 else 0,
                "yellow": bool(flags & 0x4000),      # irsdk_caution
            }
            if order:
                booth.update(snap)
            ir.unfreeze_var_buffer_latest()
        except Exception as e:
            print(f"  (telemetry hiccup: {e})")
        time.sleep(1.0 / hz)

# ---------------------------------------------------------------- demo source

DEMO_DRIVERS = ["Alex Vargas", "R. Davenport", "Maya Chen", "Tom Kowalski",
                "Sofia Ricci", "J. Okafor"]

def demo_loop(booth, speed=1.0):
    """A scripted six-car, six-lap sprint that exercises every event type."""
    print("Demo race: 6 cars, 6 laps. The booth will call it as it happens.\n")
    d = DEMO_DRIVERS
    T = lambda s: time.sleep(s / speed)

    def snap(order, gaps=None, onpit=(), lastlaps=None, state="racing",
             lap=1, yellow=False):
        booth.update({
            "order": list(order), "gaps": gaps or {}, "onpit": set(onpit),
            "lastlaps": lastlaps or {}, "state": state, "lap": lap,
            "total_laps": 6, "yellow": yellow,
        })

    grid = [d[0], d[1], d[2], d[3], d[4], d[5]]
    snap(grid, state="pre"); T(2)
    snap(grid, state="racing", lap=1); T(4)                       # green flag
    # battle builds between P1 and P2
    for gap in (0.7, 0.6, 0.5):
        snap(grid, gaps={d[1]: gap}, lap=1); T(2)                 # battle call
    T(2)
    snap([d[1], d[0], d[2], d[3], d[4], d[5]],
         gaps={d[0]: 0.4}, lap=2); T(4)                           # lead change!
    snap([d[1], d[0], d[2], d[3], d[4], d[5]],
         lastlaps={d[1]: 92.415}, lap=2); T(3)
    snap([d[1], d[0], d[2], d[3], d[4], d[5]],
         lastlaps={d[2]: 91.877}, lap=3); T(4)                    # fastest lap
    snap([d[1], d[0], d[2], d[3], d[4], d[5]],
         onpit=[d[3]], lap=3); T(3)                               # pit in
    snap([d[1], d[0], d[2], d[4], d[3], d[5]], onpit=[d[3]], lap=4); T(2)
    snap([d[1], d[0], d[2], d[4], d[3], d[5]], lap=4); T(3)       # pit out
    snap([d[1], d[0], d[2], d[4], d[3], d[5]], lap=4, yellow=True); T(4)   # caution
    snap([d[1], d[0], d[2], d[4], d[3], d[5]], lap=5); T(4)       # restart
    snap([d[1], d[0], d[4], d[2], d[3], d[5]], lap=5); T(4)       # overtake P3
    snap([d[1], d[0], d[4], d[2], d[3], d[5]], lap=6); T(3)       # white flag
    snap([d[1], d[0], d[4], d[2], d[3], d[5]], lap=6,
         state="checkered"); T(2)                                  # checkers
    # let the booth finish everything still on the rundown
    booth.speaker.drain()
    print("\nDemo complete — that's the booth. Point it at a live session next.")

# ---------------------------------------------------------------- main

def main():
    # Windows consoles often default to cp1252 — never let printing kill us
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
    ap = argparse.ArgumentParser(description="RaceCaster — AI commentary booth for iRacing")
    ap.add_argument("--demo", action="store_true", help="commentate a simulated race (no sim needed)")
    ap.add_argument("--demo-speed", type=float, default=1.0, help="demo time multiplier")
    ap.add_argument("--voice", default="en-GB-RyanNeural",
                    help="edge-tts voice (try en-US-GuyNeural, en-AU-WilliamNeural)")
    ap.add_argument("--rate", type=int, default=8, help="speech rate offset %% (default +8)")
    ap.add_argument("--caption", default="racecaster_caption.txt",
                    help="file that always holds the line being spoken (for OBS)")
    ap.add_argument("--mute", action="store_true", help="captions/console only, no audio")
    args = ap.parse_args()

    speaker = Speaker(args.voice, args.rate, args.caption, mute=args.mute)
    booth = Booth(speaker)
    print("RaceCaster v0.1 — the booth is open.\n")
    if args.demo:
        demo_loop(booth, speed=args.demo_speed)
    else:
        live_loop(booth)

if __name__ == "__main__":
    main()
