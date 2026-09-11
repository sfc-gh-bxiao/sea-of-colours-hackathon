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


# ── round-2 targeting predicate ───────────────────────────────────────────
# WHY THIS EXISTS. `targets` has three modes and only ONE of them works in a
# forged fork:
#
#   "pattern"      (default) borrows the seam pattern's wave-1 drop — which is
#                  THE CELL THE FOLLOW-UP LANDS ON. Measured in the armed lab:
#                      {"a": "emp_launch", "at": [15, 22]}
#                      {"a": "drop", "unit": "harvester_p1", "at": [15, 22]}
#                  and (15,22) was OUR pure. Friendly fire is on, so the salvo
#                  denied us the ground we were landing on.
#   "rival_probes" \  both raise
#   "redsign"      /  "needs scorch.py ... and it is not in this fork" and then
#                  return NO OPTION AT ALL. `scorch.py` is not installed by
#                  forge_install.py and is not part of a fresh V12 mint, so
#                  neither mode is available here. Verified by isolating the
#                  three round-2 fields one at a time: every variant carrying
#                  targets="rival_probes" produced no option, with
#                  probe_the_comb and min_targets making no difference.
#
# So the aim points come from a trigger instead, which `when="other"` accepts
# as `Callable[[agent_view], Sequence[Cell]]` — an empty return means "do not
# offer tonight", so this both GATES and AIMS.
def rival_eyes_on_their_pure(view):
    """Aim cells for LOAD_SHEDDING: rival probe cells, when THEIR pure is lit.

    Preserves the original intent of ``when="redsign_theirs"`` — fire only when a
    rival found the pure — while aiming at their EYES rather than at the cell we
    intend to land on. Returns [] when either half is missing, which the forge
    reads as "no option tonight".

    ROUND 3. The first version of this read ``view["rival_probes"]`` (dicts with
    x/y) and ``view["enemy_probes"]`` (dicts with ``at``). **Neither key exists on
    a live agent_view** — they are fixtures invented by
    ``skills/.../check_wiring.py``. So the function returned [] on every real
    night and the option went from offered-twice to offered-never, while still
    passing every fixture check.

    The kit's own reader stitches FOUR channels, none of them those two:
    ``competitor_intel.new_this_day``, ``competitor_intel.persistent_echoes``,
    ``world.echo`` rows with ``via='probe_launch'``, and ``entities.echoes``.
    Reusing it is the whole fix — an accessor the engine maintains cannot drift
    away from the view the engine builds, which is exactly what my hand-rolled
    version did.
    """
    # 1. is a RIVAL redsign live? `mine` is False/absent on a rival smear.
    signs = view.get("redsign") or []
    theirs = [s for s in signs
              if isinstance(s, dict) and not bool(s.get("mine"))]
    if not theirs:
        return []

    # 2. where are their eyes? Use the KIT'S reader, freshest first.
    try:
        from ._v7.probe_hints import _enemy_probe_cells
    except ImportError:                       # pragma: no cover - defensive
        return []

    out, seen = [], set()
    for row in (_enemy_probe_cells(view) or []):
        at = row.get("at") if isinstance(row, dict) else None
        if not (isinstance(at, (list, tuple)) and len(at) >= 2):
            continue
        try:
            cell = (int(at[0]), int(at[1]))
        except (TypeError, ValueError):
            continue
        if cell not in seen:
            seen.add(cell)
            out.append(cell)

    # Fixture compatibility: check_wiring's synthetic board carries only the two
    # invented keys, so without this the wiring check reports a false FAIL.
    if not out:
        for row in (view.get("rival_probes") or []):
            if isinstance(row, dict) and row.get("x") is not None:
                cell = (int(row["x"]), int(row["y"]))
                if cell not in seen:
                    seen.add(cell)
                    out.append(cell)

    return out[:3]          # an EMP carries at most 3 missiles


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
    # probe so the denial and our own vision cover the SAME ground.
    #
    # ROUND 2 (Phase 5). Three fields changed, each on measured evidence from
    # season REBORN_A/B and the armed lab takes:
    #
    #   targets="rival_probes"
    #       Was the DEFAULT "pattern", which the field's own docstring defines
    #       as the seam pattern's wave-1 drop — i.e. THE CELL WE THEN LAND ON.
    #       The lab proved it: the orders read
    #           {"a": "emp_launch", "at": [15, 22]}
    #           {"a": "drop", "unit": "harvester_p1", "at": [15, 22]}
    #       and (15,22) was OUR pure. Friendly fire is on, so that salvo denied
    #       us the very ground we were landing on. Aiming at their freshest eyes
    #       is also what this play's own WHY describes.
    #
    #   probe_the_comb=True
    #       The menu printed its own counter-argument: "yield: unknown (1 blind
    #       fog cell — no probe at all — you walk in blind)" and "~7% chance
    #       this comb CROSSES the pure". Offered twice, chosen zero times. A
    #       probe adjacent to the landing lights the walk so the yield stops
    #       reading as a coin flip.
    #
    #   min_targets=2
    #       A charge fires all its missiles whether or not you aimed them, so a
    #       cloud over one expiring eye wastes 200 blue. This is the forge's own
    #       correction text: "the number that matters is how many of their eyes
    #       sit inside ONE radius-2 diamond: two or more and a single charge
    #       blinds the lot."
    # ROUND 4. combines_with: "probe" -> "standalone". ONE variable changed.
    #
    # Round 3 got the salvo firing in a live season (seed 22, night 5, chosen by
    # the model with no harness guard) but the follow-up walked straight into our
    # own cloud. An EMP at (19,13) with radius 2 darkens x 17-21, y 11-15, and
    # EVERY follow-up order sat inside it:
    #     probe (19,13)   <- ON the blast centre
    #     drop  (19,12) · step (20,12) · step (21,12) · step (21,13)
    # against the doctrine printed in the same prompt: "probes inside die,
    # landings under it are refused ... your own units in the cloud are not
    # immune."
    #
    # Round 2 fixed WHERE the salvo points; it did not stop the fleet following
    # it in. "standalone" removes the follow-up landing entirely, which both ends
    # the self-harm and answers the more interesting question directly: is the
    # denial worth one of 21 shared hours on its own, with no points banked
    # behind it?
    # ROUND 5 — MEASURED, not guessed. For a `when="other"` + trigger play, the
    # builder takes this branch (weapon_forge.py:524):
    #
    #     if p.when == "other" and p.trigger is not None:
    #         aim = list(p.trigger(agent_view) or ())
    #     else:
    #         aim, comb, _notes = _aim_points(...)
    #         if p.probe_the_comb and comb: ...
    #
    # `_aim_points` is NEVER called, so `comb` is ALWAYS empty. Therefore:
    #   * probe_the_comb  — INERT. Proven: the rationale is byte-identical with
    #                       it True or False, and no probe/drop line is ever
    #                       emitted. Left False now so the file stops implying
    #                       a follow-up that cannot exist.
    #   * min_targets     — INERT. It is only read inside `_aim_points` under
    #                       targets="rival_probes", which additionally needs
    #                       scorch.py (absent). Dropped.
    #   * combines_with   — PROSE ONLY. It changes exactly one clause of the
    #                       rationale: "COMPARE: GRAB1 a visible pure/mass grab
    #                       banks the most certain points" (standalone) versus
    #                       "COMPARE: PR1 a bare probe buys vision and banks
    #                       nothing tonight" (probe). 851 chars vs 833. Nothing
    #                       else differs, and it does not depend on whether a
    #                       seam pattern is present.
    #
    # CONSEQUENCE: round 4's change was an 18-character prose edit. It CANNOT
    # explain the drop from 6 offers to 0. That swing was board divergence
    # between two LLM seasons — noise at n=2, not the edit. The gating and the
    # aim of this play live ENTIRELY in `rival_eyes_on_their_pure` above; every
    # other field here is decoration.
    WeaponPlay(
        play_id="LOAD_SHEDDING",
        weapon="emp",
        when="other",                       # gated by the trigger below
        hour="super_early",
        combines_with="standalone",         # prose only — see above
        trigger=rival_eyes_on_their_pure,   # gates AND aims — the only real lever
        probe_the_comb=False,               # inert on this branch; was True
        why=(
            "a rival has just found a pure so they will commit to it at first "
            "light, and eight hours of dark over the ground our own probe is "
            "watching means they cannot work it while we still can"
        ),
    ),
)
