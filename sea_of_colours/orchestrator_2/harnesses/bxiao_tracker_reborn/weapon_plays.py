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

from typing import List, Tuple

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
# ── ROUND 9: STOP BUYING BLUE WE NEVER SPEND ──────────────────────────────
# Eight rounds of weapon tuning produced a safe weapon and no measurable score
# gain. This round targets a cost that is paid in EVERY season instead of one
# that is paid once in six.
#
# MEASURED, from our seat's orbit cards in R8T22:
#     d02  blue 433      d03  blue 635      d04  blue 435
# We accumulated 635 blue, spent 200 on one EMP, and carried ~435 to the end.
# BLUE DOES NOT SCORE — `session.py:368 compute_player_score` credits shipped
# RED only. So that surplus is harvest capacity converted into a currency that
# never reaches the scoreboard, to fund a charge that has fired 3 times in 27
# seasons.
#
# THE DIAL. `agency._strong_chain_count` (agency.py:596-622) counts juice chains
# banking at least `value_pyramid._STRONG_CHAIN_RED_MIN` red, and its docstring
# states the gate: "blue is only surfaced when the seat has more harvesters than
# strong red chains (a spare unit) or orbital asks for blue."
#
# So LOWERING the threshold makes MORE chains count as strong, which makes
# `harvesters > strong_chains` false more often, which surfaces blue LESS. 60 is
# chosen off the tier table: a vein cell is ~90 and a mass ~300, so at 60 any
# chain that reaches real red outranks a blue run, while a pure trace-scrape
# (~15/cell) still does not.
#
# WHY THIS DOES NOT DISARM US: `blue_also_requested` (weapon_forge.py:1229)
# force-surfaces blue whenever we hold NONE of any declared weapon, and that is
# the "or orbital asks for blue" branch above. The EMP still gets funded — just
# later, and without the 435-blue tail. Arming later is close to free for a
# weapon that fires once in six seasons.
#
# THE RISK, stated honestly: if blue dries up entirely the EMP never arms and
# rounds 1-8 become dead weight. That is exactly what the seasons below measure.
#
# SECOND DIAL, found while verifying the first: `emp_stockpile_cap` was **2**, so
# the seat would happily fund a SECOND charge at another 200 blue. Across 27
# seasons this play has fired 3 times and never twice in one season, so the
# second charge is 200 blue of pure carry. `hold_at={"emp": 1}` caps it.
#
# TWO VARIABLES CHANGED, DELIBERATELY. Normally I would move one at a time, but
# round 5 measured ~±1,400 points of run-to-run variance, so a single-variable
# economy test is not observable at any sample size I can afford here. Both dials
# serve ONE intervention — stop over-funding a rack we do not empty — so they are
# tested as one change and reported as one.
# ── ROUND 13: BUY THE HARVESTER, NOT THE CHARGE ───────────────────────────
# Round 12 read the cards of 4 seasons on one seed and found the first lever with
# a mechanism AND a consistent direction. In both duels we lost we were
# out-dropped:
#
#     season          our drops/steps    theirs        result
#     vs tracker          8 / 29         12 / 42       LOST -432
#     vs v12             11 / 27         12 / 28       LOST -428
#     vs emp_harvest     10 / 25         10 / 33       WON  +153
#     4-seat FFA         10 / 24         11 / 32       WON
#
# Every drop is a landing and every step is a red cell banked, and RED is the only
# thing `compute_player_score` credits. Against tracker they made 50% more
# landings and 45% more steps. That is the 432 points.
#
# THE CAUSE. In that season they built TWO harvesters and we built one. Our orbit
# card says the same thing five times a season:
#
#     deferred harvester build (need 1500c, have 1000c)
#
# The harvester is Priority 2 in orbit_policy — AHEAD of weapons (3) and probes
# (4) — so it is not being outranked. It is unaffordable at the moment it is
# offered, because the PREVIOUS nights' purchases drained the balance. Earlier
# cards show nights at `have 1250c`: ONE skipped 250c purchase is the difference
# between deferring and building.
#
# THE CHANGE. Take the fleet, not the ordnance:
#   * emp  cap 0 — 250 credits a charge, and it has fired 5 times in ~92 seasons
#                  with no measured gain (round 9: FIRED margin +234.3 vs
#                  NOT-fired +268.9).
#   * snap cap 0 — this is NEW spending the round-11 retrofit introduced. Before
#                  it, `orbit_policy` had no `build_snap` at all so WET_PAINT was
#                  free to declare. Now procurement exists and a declared snap
#                  WILL be bought, making the credit squeeze worse, not better.
#   * seek_blue_when_rack_empty=False — REQUIRED, not optional. With both caps at
#                  0 the rack can never fill, and `blue_also_requested` returns
#                  True whenever we hold none of any declared weapon
#                  (weapon_forge.py:1229). Left True we would divert harvesters
#                  to blue every single night for a purchase that can never
#                  happen. This is the interaction that would have quietly
#                  wrecked the experiment.
#
# The PLAYS below stay declared on purpose: the wiring, the trigger and the
# rationale all remain live and verified, so re-arming is one line if the
# harvester turns out not to pay.
#
# HONEST FRAMING: this partially unwinds rounds 1-11. That is what the evidence
# says. The weapon is correct, safe, and has never been shown to earn its cost.
ECONOMY = EconomyPolicy(
    strong_chain_red_min=60,                  # round 9: keep harvesters on red
    # ROUND 14. Chaff only. It is the one weapon that costs 0 CREDITS, so it
    # never competes with the 1500c harvester; emp and snap stay at 0 because
    # 250 credits each is exactly what round 12 found standing between us and
    # the second harvester. They stay DECLARED so re-arming is one number.
    hold_at={"chaff": 1, "emp": 0, "snap": 0},
    # ROUND 14, reversing round 13's False. Chaff needs 300 blue, so we do need
    # to earn some. This is self-limiting rather than open-ended:
    # `blue_also_requested` returns True only while we hold NONE of any declared
    # weapon, so the moment the single chaff lands the request stops. Round 13
    # had to set this False precisely because every cap was 0 and the rack could
    # never fill, which would have chased blue forever.
    seek_blue_when_rack_empty=True,
)


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

    # ── ROUND 7: the smear fallback ───────────────────────────────────────
    # ── ROUND 8: THE RIVAL SMEAR IS AN EXCLUSION ZONE, NOT A TARGET ───────
    # ROUND 7 built this block to AIM at the smear whenever no enemy probe was
    # visible, reasoning that a public redsign tells us the ground they must
    # land on. The reasoning was sound and the conclusion was backwards.
    #
    # It fired for the first time in the final-polish season and self-harmed
    # immediately (REBORN_FINAL d02):
    #
    #     BLIND_AND_GRAB  wave-1 drop   (35,22)
    #     LOAD_SHEDDING   emp_launch    (34,21)   <- one cell diagonal
    #     then: probe (34,21) m=0 · drop (35,22) m=2 · step (34,22) m=1
    #
    # All three follow-ups sat INSIDE our own radius-2 cloud — the probe ON the
    # blast centre, the landing refused. Identical to round 3 (R3B d05). The
    # round-6 rationale says, in the same prompt the model read, "do not plan a
    # landing or a probe inside these clouds this night". It did it anyway.
    # PROSE IS NOT A CONSTRAINT.
    #
    # THE STRUCTURAL REASON: the smear IS the prize. Every seam option the
    # harness offers — BLIND_GRAB, BLIND_AND_GRAB, SMASH_GRAB — lands on it. So
    # bombing the smear guarantees a collision with our own best play of the
    # night. It was not bad luck twice; it was designed in.
    #
    # THE FIX: darken their EYES, never their PRIZE. That is what this play's
    # own `why` always claimed — "eight hours of dark over the ground our own
    # probe is watching" — and it is collision-free by construction, because
    # their outer probes sit away from the seam core that seam options land on.
    #
    # So the smear is now built on EVERY path (the probe path needs the same
    # protection: R3B's aim came from a probe, not from the fallback) and used
    # ONLY to REJECT aim points.
    smear: List[Tuple[int, int]] = []
    _smear_seen: set = set()

    def _put(xf, yf) -> None:
        try:
            cell = (int(round(float(xf))), int(round(float(yf))))
        except (TypeError, ValueError):
            return
        # NOTE: deliberately its OWN set, not the probe-dedup `seen`. Sharing
        # `seen` would silently drop any smear cell that is ALSO a probe cell —
        # exactly the overlap the exclusion below has to catch.
        if cell not in _smear_seen:
            _smear_seen.add(cell)
            smear.append(cell)

    for row in theirs:
        cells = row.get("cells")
        if isinstance(cells, (list, tuple)) and cells:
            for c in cells:
                if isinstance(c, dict):
                    _put(c.get("x"), c.get("y"))
                elif isinstance(c, (list, tuple)) and len(c) >= 2:
                    _put(c[0], c[1])
            continue
        if row.get("x") is not None:                   # legacy flat shape
            _put(row.get("x"), row.get("y"))
            continue
        centre = row.get("center") or row.get("at")
        if isinstance(centre, (list, tuple)) and len(centre) >= 2:
            _put(centre[0], centre[1])

    # blast radius 2 + one cell of slack, so no cloud we place can touch a
    # smear cell that a seam option might land on.
    _KEEP_CLEAR = 3
    if smear:
        # Refusing to offer is a REAL answer. A salvo that blinds them and also
        # refuses our own landing costs 200 blue, an hour-slot, a probe AND the
        # grab. Two of the three firings this agent has ever made did that.
        out = [c for c in out
               if all(abs(c[0] - s[0]) + abs(c[1] - s[1]) > _KEEP_CLEAR
                      for s in smear)]

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
        # ── ROUND 6: PERSUASION ───────────────────────────────────────────
        # Rounds 1-5 fixed the wiring. It works: offered on 4 / 2 / 4 nights of
        # 7 across three seasons, correct aim, correct one-move salvo. And the
        # model took it ZERO times. So the remaining problem is the argument,
        # not the plumbing.
        #
        # GROUND TRUTH from the live card (REBORN_R5X d03_p1_planning.md:55-58),
        # which is what the model actually reads:
        #
        #   [LOAD_SHEDDING] ... Costs 200 blue and one hour-slot.  - no probe
        #        WHY: WHY: a rival has just found a pure ...
        #        yield: red ~+0 - blue 0 - green 0
        #        crush: none - collision risk: LOW (no cell you touch is under
        #                                           enemy vision)
        #
        # Two corrections to my earlier reading:
        #  * collision risk is **LOW**, not HIGH. The HIGH / "~7% chance this
        #    comb CROSSES the pure" text I blamed belongs to GRAB1's annotation
        #    further down the same card. Geometry was never the objection.
        #  * The objection is the line above it: **yield: red ~+0**. Directly
        #    beneath sits `[GRAB1] ... yield: red ~+292`, under doctrine that
        #    says take the red first. A rational reader picks +292 over +0 every
        #    single night, and it did.
        #
        # An empty `rationale` is composed as
        #     f"WHY: {p.why...}" + _MECHANICS + cost + COMPARE + THE COST IS REAL
        # which ALSO produces the duplicated "WHY: WHY:" visible above (a real
        # forge defect). Overriding `rationale` replaces the whole string, so
        # this both fixes that and lets the denial be priced in the model's own
        # currency.
        #
        # Everything asserted below is taken from the same card, not invented:
        # the card itself says "a pure is worth ~+765, so the swing is ~1530",
        # and the mechanics line is the forge's own `_MECHANICS["emp"]`. The
        # cost stays stated in full — the skill is explicit that an option which
        # hides its cost is worse than no option.
        rationale=(
            "READ THE YIELD LINE CORRECTLY: this option banks +0 red BY DESIGN. "
            "It is not a harvest and it does not compete with GRAB on points "
            "tonight. Its return is measured on the RIVAL's column, not ours. "
            "THE TRADE: a rival has just lit a pure and will commit to it at "
            "first light. This card prices a pure at ~+765, and says the swing "
            "on one is ~1530. One launch puts up to 3 radius-2 clouds over the "
            "exact cells their eyes are sitting on, for 8 hours from hour 1 — "
            "probes inside die, and they cannot drop into cells they cannot "
            "see, so the landing is REFUSED rather than delayed. They do not "
            "get a slower run at that pure; they get no run at it, and our own "
            "probe keeps watching ground they can no longer work. "
            "WHY IT IS CHEAP TONIGHT: collision risk on this play is LOW — no "
            "cell we touch is under enemy vision — and it needs NO probe, so it "
            "does not compete with the probe budget that gates the grabs. It "
            "costs 200 blue and one hour-slot. "
            "COMPARE: GRAB* banks certain red tonight and leaves their night "
            "completely untouched — take one of those FIRST, it is not either/or. "
            "BLIND_GRAB is the closer rival: it spends a probe to blind the "
            "finder and banks points itself, but it removes ONE eye for ONE "
            "hour and they can still act from another, whereas this refuses "
            "every landing under each cloud it puts up, for eight hours. "
            "Pick BLIND_GRAB if you "
            "want the halo; pick this if their pure is the thing beating us. "
            "THE COST IS REAL: friendly fire is ON, so do not plan a landing or "
            "a probe inside these clouds this night; they are OUR no-go ground "
            "for 8 hours too. The hour-slot is one a harvester did not walk. "
            "WHAT IS GUARANTEED: these aim cells are their PROBES, and every "
            "one is at least 4 cells clear of the broadcast smear, so no cloud "
            "here can cover the seam itself. Your GRAB, BLIND_GRAB or SMASH on "
            "that seam stays legal tonight — this does not block your own "
            "landing on the pure. Take the red AND take this. "
            "TAKE IT WHEN: their pure is fresh, and we "
            "already have a red grab banked elsewhere in the plan — this is the "
            "move that stops them out-scoring us, not the move that scores."
        ),
    ),
    # ── ROUND 14 · EGRESS_JAM · chaff · a RIVAL's pure is lit ──────────────
    # WHY THIS PLAY EXISTS. Round 13 stripped the rack to nothing and the two
    # regimes came apart on one seed:
    #     three duels      throughput UP (steps 29->46, 27->45, 25->32), our
    #                      score UP +840 / +746 / +1089
    #     4-seat FFA       3570 -> 620, LAST of four, 49 loss-mentions to the
    #                      winner's 32
    # An empty rack costs nothing measurable in a duel and looks fatal in a
    # crowd: we cannot jam an egress or refuse a landing, so three rivals
    # contest our ground for free. The kit says it in its own orbit comment —
    # "chaff leads the always-build band because an empty rack loses the egress
    # jam, and the jam is the cheapest denial in the game."
    #
    # WHY CHAFF SPECIFICALLY, AND NOT THE EMP BACK. Read off the engine, not
    # guessed (game.weapons.CREDIT_COST_BY_KIND):
    #     chaff  300 blue   0 credits
    #     emp    200 blue   250 credits
    #     snap   100 blue   250 credits
    # Chaff is the ONLY ordnance that spends no credits, so it cannot compete
    # with the 1500c harvester that round 12 identified as our throughput
    # ceiling. It restores the crowd denial without reopening the credit squeeze
    # round 13 set out to fix. That is the whole design.
    #
    # WHY IT SCALES WITH THE CROWD. `_MECHANICS["chaff"]`: "At the hour it
    # resolves, every OTHER seat's action that hour is cancelled: drops, steps,
    # pickups, probes, even their own launches." In a duel that cancels one
    # rival's hour. On a 4-seat board it cancels THREE. The weapon's value is
    # multiplied by exactly the condition that broke us in round 13.
    #
    # HOUR. `super_early` = H1, which is what the forge's own doctrine
    # prescribes: "firing at H1 leaves you immune that hour (launching IS your
    # move), jams your own house at H2 and H3, and frees you from H4 — exactly
    # when a blind grab lands and lifts. Plan nothing in H2-H3; plan the walk-in
    # after them." Hence combines_with="blind_grab".
    #
    # NO `rationale` OVERRIDE. In round 6 I hand-wrote one because the composed
    # text let `yield: red ~+0` disqualify the play. The retrofitted forge now
    # ships `_DENIAL_VALUE["chaff"]`, which makes that argument better than mine
    # and places it BEFORE the yield line: "THIS IS A THEFT, NOT A DENIAL —
    # score it that way ... Its yield line says 'unknown' because it is
    # measuring the blind cell you land on, not the pure you inherit." Let the
    # kit argue. Overriding would throw away the fix.
    #
    # No trigger: `redsign_theirs` is a built-in `when`, and chaff needs no
    # target cell (`_AIMED["chaff"] == 0`), so there is nothing to aim and
    # nothing to keep clear of.
    WeaponPlay(
        play_id="EGRESS_JAM",
        weapon="chaff",
        when="redsign_theirs",
        hour="super_early",
        combines_with="blind_grab",
        why=("a rival has broadcast a pure so every seat is racing it at first "
             "light, and one flare at H1 cancels that hour for all of them at "
             "no credit cost, leaving the pure unharvested and us free from H4 "
             "to walk in behind them"),
    ),
    # ── ROUND 15 · CROWD_JAM · chaff · ANY night we hold a flare ───────────
    # THE MEASURED FAILURE THIS FIXES. Round 14 won all three duels (+3022 vs
    # tracker, the biggest margin in ~100 seasons) and still came 3rd of 4 in the
    # free-for-all. The reason was not the weapon — it was the GATE:
    #
    #     season          EGRESS_JAM offered   chosen   fired   result
    #     vs tracker              2              1       1     WON +3022
    #     vs v12                  2              1       1     WON +781
    #     4-seat FFA              0              0       0     3rd of 4
    #
    # `when="redsign_theirs"` needs a rival to have broadcast a pure, and on that
    # 4-seat board no such sign reached us. So the crowd denial the play exists
    # for was never even on the menu, while `emp_harvest_test` fired 3 weapons
    # and won with 4404.
    #
    # WHY A SECOND PLAY RATHER THAN WIDENING THE FIRST. EGRESS_JAM is the only
    # play in this build with a proven record — chosen 1 of 2, fired 2 of 2, won
    # both. Widening its `when` would destroy that evidence by changing the thing
    # being measured. This adds the broad case alongside it and leaves the narrow
    # one exactly as validated.
    #
    # WHY `always` IS DEFENSIBLE FOR CHAFF SPECIFICALLY. Every usual reason to
    # gate a weapon narrowly is absent here:
    #   * 0 CREDITS (game.weapons.CREDIT_COST_BY_KIND) — it never competes with
    #     the 1500c harvester, so an unfired charge costs no vision and no unit.
    #   * NO TARGET CELL (`_AIMED["chaff"] == 0`) — it is fired at an HOUR, so
    #     there is no aim to get wrong and nothing to keep clear of. The whole
    #     class of self-harm bugs from rounds 3-8 cannot occur.
    #   * The engine's own hour validator restricts only EMP (weapon_forge:241);
    #     chaff has no restricted hour.
    #   * Its value RISES with rival count: "every OTHER seat's action that hour
    #     is cancelled". One rival in a duel, THREE in the crowd.
    #
    # THE REAL COST, AND WHY THE MODEL MUST WEIGH IT NIGHTLY. `_COSTS["chaff"]`:
    # "Do not pick this if you had a rich walk already queued inside H2-H3 —
    # those hours are yours to lose, and a banked chain you cancel yourself is a
    # worse trade than the pure you are stealing." Firing at H1 jams OUR H2-H3
    # too. That is exactly a per-night judgement, which is why this is offered
    # rather than forced, and why it pairs with `chain` — the option it competes
    # against is the very chain it would cancel, so the menu states the trade.
    #
    # `hour="early"` not `super_early`: H1-2 gives the packager a second slot to
    # place the flare when H1 is already committed, which round 11's
    # `order_for_weapon_hours` hook showed is a real cause of a chosen play never
    # reaching the wire.
    WeaponPlay(
        play_id="CROWD_JAM",
        weapon="chaff",
        when="always",
        hour="early",
        combines_with="chain",
        menu_rank=60,                 # below EGRESS_JAM: the redsign case leads
        why=("on a crowded board every rival spends the same hours we do, and one "
             "flare costs no credits at all yet cancels that hour for EVERY other "
             "seat at once, so the more of them are committed the more it takes "
             "off them for the price of one of our own hours"),
    ),
)
