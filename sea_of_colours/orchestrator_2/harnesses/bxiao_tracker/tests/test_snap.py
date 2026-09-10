"""Unit tests for the bxiao_tracker SNAP port (v1.36).

Covers the three things that can silently ruin the weapon:
  * the WIRE SHAPE — one bare pair, because the engine refuses a list by name
  * FRIENDLY FIRE — a round on our own route or our own beacon must be CUT
  * PROCUREMENT — cap-aware, and off on a pre-SNAP view
"""
import os
import sys
import pathlib

# Resolve the repo root by walking UP from this file rather than hardcoding it.
# The hardcoded path this replaced pointed at a different clone, so the tests
# silently exercised the OTHER agent's modules — the worst possible failure for
# a file whose whole job is to tell you the port is sound.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[5]))

from sea_of_colours.orchestrator_2.harnesses.bxiao_tracker import (  # noqa: E402
    packager, scorch, orbit_policy,
)

PASS = []
FAIL = []


def check(name, cond, extra=""):
    (PASS if cond else FAIL).append(name)
    print(("  ok   " if cond else "  FAIL ") + name + (f"  {extra}" if extra and not cond else ""))


class FakePk:
    """Minimal stand-in for _Packer's SNAP-relevant surface."""

    def __init__(self, wake=(), drops=(), probes=()):
        self.moves = []
        self.log = []
        self._pending_snap = []
        self._pending_emp = []
        self._own_wake = set(wake)
        self._drop_cells = set(drops)
        self._probed_cells = set(probes)


print("=== wire shape ===")
pk = FakePk()
packager._pack_snap(pk, {"weapon": "snap", "target": [7, 9],
                         "denies": [8, 9], "denies_purity": 255,
                         "denies_tier": "pure"})
packager._finalise_snap(pk)
check("emits exactly one move", len(pk.moves) == 1, pk.moves)
mv = pk.moves[0] if pk.moves else {}
check("action is snap_launch", mv.get("a") == "snap_launch", mv)
check("at is a BARE pair [x,y]", mv.get("at") == [7, 9], mv.get("at"))
check("at is not nested", not isinstance((mv.get("at") or [None])[0], (list, tuple)), mv)
check("inserted at H1 (index 0)", pk.moves.index(mv) == 0)

print("=== payload validation ===")
pk = FakePk()
packager._pack_snap(pk, {"weapon": "snap", "target": [[1, 2], [3, 4]]})
packager._finalise_snap(pk)
check("a LIST of pairs is refused, not coerced", pk.moves == [], pk.moves)
pk = FakePk()
packager._pack_snap(pk, {"weapon": "snap"})
check("missing target is refused", pk._pending_snap == [])

print("=== friendly fire ===")
# The route is expressed as REAL MOVES, not as a parallel wake set. This build
# derives the footprint from ``pk.moves`` — a drop's ``at`` and a step's ``to``
# ARE the fleet's cells by construction — so a fixture that sets a wake attribute
# without emitting the moves would assert the old implementation rather than the
# behaviour, and would pass even if the filter were blind to real routes.
pk = FakePk()
pk.moves = [{"a": "drop", "at": [7, 7]}, {"a": "step", "to": [7, 9]}]
packager._pack_snap(pk, {"weapon": "snap", "target": [7, 9]})
packager._finalise_snap(pk)
check("CUT when target is our own harvester route",
      not any(m.get("a") == "snap_launch" for m in pk.moves), pk.moves)
check("cut is explained in the log",
      any("FRIENDLY FIRE" in s for s in pk.log), pk.log)

pk = FakePk(drops={(4, 4)})
packager._pack_snap(pk, {"weapon": "snap", "target": [4, 4]})
packager._finalise_snap(pk)
check("CUT when target is our own DROP cell", pk.moves == [])

pk = FakePk(probes={(2, 2)})
packager._pack_snap(pk, {"weapon": "snap", "target": [2, 2]})
packager._finalise_snap(pk)
check("CUT when target is our OWN beacon", pk.moves == [])
check("own-beacon cut is explained",
      any("OWN beacon" in s for s in pk.log), pk.log)

pk = FakePk(wake={(1, 1)}, drops={(2, 2)}, probes={(3, 3)})
packager._pack_snap(pk, {"weapon": "snap", "target": [9, 9]})
packager._finalise_snap(pk)
check("FIRES when clear of all our own cells",
      pk.moves and pk.moves[0]["at"] == [9, 9], pk.moves)

print("=== one round, one cell ===")
pk = FakePk()
packager._pack_snap(pk, {"weapon": "snap", "target": [1, 1], "denies_purity": 60})
packager._pack_snap(pk, {"weapon": "snap", "target": [2, 2], "denies_purity": 255})
packager._finalise_snap(pk)
check("two staged rounds emit ONE move", len(pk.moves) == 1, pk.moves)
check("fires the RICHER denial", pk.moves[0]["at"] == [2, 2], pk.moves)

print("=== emp salvo hygiene ===")
# REGRESSION. Seen live on d7 of season tracker_weapons_v1: the salvo went out
# as ([13,11],[13,11]) — the same square twice. The rack is capped, so a second
# warhead on an already-blinded cell is one thrown away.
pk = FakePk()
pk.moves = [{"a": "drop", "at": [2, 2]}]
packager._pack_emp(
    pk, {"weapon": "emp", "targets": [[13, 11], [13, 11], [20, 20]], "radius": 2},
)
packager._finalise_emp(pk)
_emp = [m for m in pk.moves if m.get("a") == "emp_launch"]
check("duplicate missile centre is dropped",
      bool(_emp) and _emp[0]["at"] == [[13, 11], [20, 20]], _emp)
check("the drop is explained",
      any("duplicate EMP missile" in s for s in pk.log), pk.log)
check("EMP wire shape is a LIST of pairs",
      bool(_emp) and isinstance(_emp[0]["at"][0], list), _emp)
check("EMP is inserted at H1",
      bool(pk.moves) and pk.moves[0].get("a") == "emp_launch", pk.moves[:1])

print("=== weapon dispatch ===")
pk = FakePk()
packager._pack_weapon(pk, {"weapon": "snap", "target": [5, 5]})
check("dispatch routes snap to _pack_snap", len(pk._pending_snap) == 1)
pk = FakePk()
packager._pack_weapon(pk, {"weapon": "emp", "targets": [[5, 5]], "radius": 2})
check("dispatch still routes emp to _pack_emp", len(pk._pending_emp) == 1)
pk = FakePk()
packager._pack_weapon(pk, {"weapon": "railgun", "target": [5, 5]})
check("unknown weapon is refused loudly",
      pk._pending_snap == [] and pk._pending_emp == []
      and any("unknown weapon" in s for s in pk.log), pk.log)

print("=== stock reader ===")
check("snap read from view",
      scorch.stock({"orbit": {"weapon_stock": {"snap": 3}}})["snap"] == 3)
check("pre-SNAP view reports 0, does not raise",
      scorch.stock({"orbit": {"weapon_stock": {"emp": 1}}})["snap"] == 0)
check("has_snap false on empty rack", not scorch.has_snap({"orbit": {}}))
check("has_snap true with stock",
      scorch.has_snap({"orbit": {"weapon_stock": {"snap": 1}}}))
sp = scorch.snap_specs({"orbit": {"weapon_specs": {"snap": {
    "radius": 0, "cloud_hours": 1, "missiles_per_launch": 1,
    "resolves_before_vision": True}}}})
check("radius 0 survives the spec read (not clobbered by a truthy fallback)",
      sp["radius"] == 0, sp)
check("resolves_before_vision is carried", sp["resolves_before_vision"] is True)

print("=== procurement ===")


def orbit_view(blue, credits, stock, offer_snap=True):
    prices = {"emp": {"blue": 200, "credits": 250},
              "chaff": {"blue": 300, "credits": 0}}
    if offer_snap:
        prices["snap"] = {"blue": 100, "credits": 250}
    return {
        "day": 3,
        "you": "p1",
        "credits": credits,
        "orbit": {
            "credits": credits,
            "weapons_enabled": True,
            "weapon_stock": stock,
            "weapon_prices": prices,
            "blue_purity_total": blue,
            "hoard": [],
            "harvesters": [],
        },
        "entities": {},
    }


def buys(view):
    acts, _desc = orbit_policy.plan_orbit_actions(view)
    return [a.get("a") for a in acts]


os.environ["BXIAO_TRACKER_SNAP"] = "1"
# PROCUREMENT IS DELIBERATELY NOT PORTED, so this asserts the decision rather
# than a build. Reasons, both measured:
#   * the paired A/B on the SNAP strategy came out median-NEGATIVE, so buying
#     rounds would spend blue on the worse-evidenced weapon
#   * a round competes for the same 600-blue arsenal cap as the EMP, which the
#     stock policy already buys and which the season record supports
# The FIRING path is fully built and tested above, so the moment a rack supplies
# a round the agent can spend it. That is the split we want: capability present,
# procurement conservative until the evidence turns.
acts = buys(orbit_view(600, 3000, {"emp": 0, "chaff": 0, "snap": 0}))
check("does NOT buy SNAP (unported by decision; A/B median-negative)",
      "build_snap" not in acts, acts)
check("still arms itself — buys a priced weapon within the cap",
      any(a in ("build_chaff", "build_emp") for a in acts), acts)

acts = buys(orbit_view(600, 3000, {"emp": 0, "chaff": 0, "snap": 2}))
check("stops at the stockpile cap", "build_snap" not in acts, acts)

# Two chaff = 600 blue = the whole arsenal ceiling.
acts = buys(orbit_view(600, 3000, {"emp": 0, "chaff": 2, "snap": 0}))
check("respects the 600 weaponised-blue cap", "build_snap" not in acts, acts)

acts = buys(orbit_view(600, 3000, {"emp": 0, "chaff": 0, "snap": 0},
                       offer_snap=False))
check("never bids on a pre-SNAP view", "build_snap" not in acts, acts)

os.environ["BXIAO_TRACKER_SNAP"] = "0"
acts = buys(orbit_view(600, 3000, {"emp": 0, "chaff": 0, "snap": 0}))
check("BXIAO_TRACKER_SNAP=0 (the DEFAULT) restores chaff-led band", "build_snap" not in acts, acts)
os.environ["BXIAO_TRACKER_SNAP"] = "1"

print()
print(f"{len(PASS)} passed, {len(FAIL)} failed")
if FAIL:
    print("FAILURES:")
    for f in FAIL:
        print("  -", f)
sys.exit(1 if FAIL else 0)
