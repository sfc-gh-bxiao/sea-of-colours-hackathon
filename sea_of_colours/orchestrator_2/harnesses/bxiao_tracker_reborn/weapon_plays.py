"""weapon_plays — YOUR agent's weapon moves. This is the only file you edit.

Everything else was installed once by ``forge_install.py``. To add a weapon or
a move, add a ``WeaponPlay`` below. Nothing else in the harness needs touching:
the menu group, the wire move, the replay tag, the doctrine and the rationale
are all derived from what you write here.

Each move is four decisions:

  WHEN           always | redsign_mine | redsign_theirs | other
                 The board condition. ``redsign_mine`` = a pure WE found is
                 live (we are defending it). ``redsign_theirs`` = a rival
                 found it (we are attacking it).

  HOUR           super_early (H1) | early (H1-2) | mid | late | last_night
                 Position in the move list IS the hour, so this is a hard
                 constraint. An 8h EMP cloud past H2 has no night left to use;
                 a chaff has to land on the hour they were going to act.

  COMBINES_WITH  smash_grab | blind_grab | probe | chain | standalone
                 Which existing play this borrows geometry from, so the option
                 has real coordinates rather than invented ones.

  WHY            One sentence: what firing this BUYS. Yours, in your words.
                 The full rationale the model reads is composed from this plus
                 the weapon's mechanics plus the alternative it beats — that
                 last part depends on what else is on tonight's menu, which is
                 why the machinery adds it rather than you.

Name the move whatever you like. It is public: it shows up in the game log as
the night resolves, in the lab's frozen-turn journals and in the season cards.
Be as silly as you like about the TONE and never about the CONTENT — calling a
cautious vision move ``NUKE`` tells the model that option is aggressive, and
that is a bug you will spend an hour not finding.

Check yourself any time with:

    python skills/soc-agent-forge/scripts/check_wiring.py <your_label>
"""

from __future__ import annotations

from typing import Tuple

from .weapon_forge import EconomyPolicy, WeaponPlay


# ── how the weapons get PAID FOR ──────────────────────────────────────────
# The defaults are the conservative reading and are right for most teams:
# fund what you fire, never buy ordnance you have no play for, and never pull
# your last harvester off red to fetch currency.
#
#   soc will buy the cheapest weapon you declared the moment it can afford it,
#   set the stockpile cap to 0 for any weapon you did NOT declare, and ask for
#   blue on any night your rack cannot fire.
#
# Change something only if you mean it. `hold_at={"chaff": 1}` caps the rack at
# one; `seek_blue_when_rack_empty=False` reverts to the baseline's behaviour of
# only topping up when the VAULT is short.
ECONOMY = EconomyPolicy()


PLAYS: Tuple[WeaponPlay, ...] = (
    # ── WET_PAINT · snap · OUR pure is lit ────────────────────────────────
    # A SNAP stamps ONE cell hot for the hour and resolves ABOVE the hour's
    # vision snapshot, so it refuses a LANDING rather than merely a sighting.
    # Fired early on our own redsign it buys the one hour we need to get onto
    # the pure first, and smash_grab supplies the real geometry for that
    # landing rather than an invented coordinate.
    WeaponPlay(
        play_id="WET_PAINT",
        weapon="snap",
        when="redsign_mine",
        hour="early",
        combines_with="smash_grab",
        why=(
            "our pure is lit so a rival will come for it, and one hot square "
            "early refuses their walk-in for exactly the hour we need to land "
            "on the pure ourselves"
        ),
    ),

    # ── LOAD_SHEDDING · emp · a RIVAL's pure is lit ───────────────────────
    # H1 because an 8h cloud fired past H2 has no night left to exploit — the
    # validator rejects mid/late for this weapon outright. Combined with a
    # probe so the denial and our own vision cover the SAME ground: a measured
    # failure on the sibling agent was four salvos aimed at far-off probes,
    # which denied ground we were never going to work.
    WeaponPlay(
        play_id="LOAD_SHEDDING",
        weapon="emp",
        when="redsign_theirs",
        hour="super_early",
        combines_with="probe",
        why=(
            "a rival has just found a pure so they will commit to it at first "
            "light, and eight hours of dark over the ground our own probe is "
            "watching means they cannot work it while we still can"
        ),
    ),
)
