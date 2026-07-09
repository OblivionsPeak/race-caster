"""RaceCaster phrase banks — template commentary with variation.

Slots: {name} {name2} {pos} {pos2} {gap} {lap} {laps_left} {time}
Templates are picked with anti-repetition (never the same line twice in a
row per event type), so the booth doesn't sound like a parrot.
"""

PHRASES = {
    "green_flag": [
        "And we're green! {n_cars} cars streaming into turn one.",
        "Green flag, green flag! The race is on.",
        "Lights out and away we go — {n_cars} starters funneling down to the first corner.",
    ],
    "leader_change": [
        "{name} takes over the lead of this race!",
        "New leader — {name} hits the front.",
        "And it's {name} who now controls this race from the point.",
        "{name} is your new race leader.",
    ],
    "overtake": [
        "{name} makes the move on {name2} for P{pos}!",
        "{name} goes through — that's P{pos}, {name2} has to settle for P{pos2}.",
        "Position change: {name} up to P{pos} at the expense of {name2}.",
        "{name} gets the job done on {name2}, and that's P{pos}.",
    ],
    "overtake_lead": [
        "{name} takes the LEAD from {name2}! What a move!",
        "For the lead of the race — {name} is through on {name2}!",
        "{name} sweeps past {name2} and into first place!",
    ],
    "battle": [
        "Keep an eye on P{pos} — {name2} is all over the back of {name}, just {gap} in it.",
        "A fight is brewing for P{pos}: {name} defending from {name2}, {gap} apart.",
        "{name2} has closed to within {gap} of {name} — this battle for P{pos} is on.",
        "Pressure building on {name} — {name2} now {gap} behind in the fight for P{pos}.",
    ],
    "battle_closing": [
        "{name2} is reeling in {name} for P{pos} — the gap is down to {gap}.",
        "That gap to {name} keeps shrinking: {gap} now for {name2}.",
    ],
    "pit_in": [
        "{name} peels into the pit lane from P{pos}.",
        "Pit stop for {name} — in from P{pos}.",
        "{name} comes to the attention of the pit crew from P{pos}.",
    ],
    "pit_out": [
        "{name} rejoins the race.",
        "Service complete — {name} is back out.",
        "{name} returns to the track after the stop.",
    ],
    "fastest_lap": [
        "Fastest lap of the race — {name} with a {time}!",
        "{name} lights up the timing screens: {time}, fastest of the day.",
        "New benchmark! {name} goes quickest with a {time}.",
    ],
    "white_flag": [
        "White flag — final lap! {name} leads with {name2} chasing.",
        "One lap to go! Can {name} hold on?",
        "Last lap of the race — {name} has one more to survive.",
    ],
    "checkered": [
        "CHECKERED FLAG! {name} wins the race!",
        "And there it is — victory for {name}!",
        "{name} takes the win! What a drive.",
    ],
    "podium": [
        "Your podium: {name} wins it, from {name2} and {name3}.",
        "So the top three: {name}, {name2}, {name3}.",
    ],
    "yellow_flag": [
        "Caution is out — yellow flag flying.",
        "Yellow flag — trouble somewhere on the circuit.",
        "The field is under caution.",
    ],
    "green_restart": [
        "Back to green! Racing resumes.",
        "Green flag once more — back underway.",
    ],
    "leader_pulling_away": [
        "{name} is checking out at the front — the lead is out to {gap}.",
        "Meanwhile {name} has stretched the lead to {gap}.",
    ],
    "halfway": [
        "We're at the halfway mark — {name} leads the way.",
        "Half distance done, and it's {name} controlling things out front.",
    ],
    "color": [
        "{n_cars} cars still running out there.",
        "The leaders continue to trade fast laps.",
        "Track conditions look quick today.",
    ],
}

# priorities: higher interrupts lower when the queue backs up
PRIORITY = {
    "checkered": 100, "overtake_lead": 90, "white_flag": 85, "leader_change": 80,
    "yellow_flag": 75, "green_flag": 75, "green_restart": 70, "podium": 88,
    "overtake": 60, "fastest_lap": 55, "battle": 45, "battle_closing": 45,
    "pit_in": 35, "pit_out": 25, "leader_pulling_away": 30, "halfway": 40,
    "color": 5,
}

# per-event-type seconds before the same type can fire again
COOLDOWN = {
    "overtake": 6, "overtake_lead": 4, "battle": 45, "battle_closing": 30,
    "pit_in": 8, "pit_out": 10, "fastest_lap": 20, "leader_change": 5,
    "leader_pulling_away": 120, "color": 180, "yellow_flag": 20,
    "green_restart": 20, "halfway": 9999, "green_flag": 9999,
    "white_flag": 9999, "checkered": 9999, "podium": 9999,
}
