"""Weapon-stock awareness for the night phase.

Rung 1 of the weapon-firing progression: the agent cannot choose a
weapon it does not know it owns. This module reads the seat's own
EMP/chaff inventory from the orbit view and the weapon specs so the
prompt can tell the model what is in the rack and what each charge does.

Specs are read from the VIEW first (``orbit.weapon_specs``), falling
back to the engine constants only for stripped test views. Prices are
never copied — they ride on the view.
"""

from __future__ import annotations

from typing import Any, Dict, Mapping


def stock(agent_view: Mapping[str, Any]) -> Dict[str, int]:
    """The seat's weapon inventory: ``{'emp': N, 'chaff': M, 'snap': K}``.

    bxiao_tracker: ``snap`` added for the v1.36 third weapon. It is read the
    same way as the other two and defaults to 0, so a pre-SNAP view (every
    archived season, and every lab board shipped so far) reports no SNAP
    rather than raising -- which is what keeps this safe on old boards.
    """
    orbit = agent_view.get("orbit") or {}
    ws = orbit.get("weapon_stock") or {}
    return {
        "emp": int(ws.get("emp", 0) or 0),
        "chaff": int(ws.get("chaff", 0) or 0),
        "snap": int(ws.get("snap", 0) or 0),
    }


def specs(agent_view: Mapping[str, Any]) -> Dict[str, Any]:
    """EMP weapon specs from the view, with engine-constant fallback."""
    orbit = agent_view.get("orbit") or {}
    sp = (orbit.get("weapon_specs") or {}).get("emp") or {}
    # Read from view first; fall back to the engine constants only
    # when a stripped-down test view omits them.
    radius = int(sp.get("radius", 0) or 0)
    missiles = int(sp.get("missiles_per_launch", 0) or 0)
    cloud_hours = int(sp.get("cloud_hours", 0) or 0)
    if not (radius and missiles and cloud_hours):
        from sea_of_colours.game.weapons import (
            EMP_RADIUS,
            EMP_MISSILES_PER_LAUNCH,
            EMP_CLOUD_HOURS,
        )
        radius = radius or int(EMP_RADIUS)
        missiles = missiles or int(EMP_MISSILES_PER_LAUNCH)
        cloud_hours = cloud_hours or int(EMP_CLOUD_HOURS)
    return {
        "radius": radius,
        "missiles": missiles,
        "cloud_hours": cloud_hours,
    }


def has_emp(agent_view: Mapping[str, Any]) -> bool:
    """True when the seat has at least one EMP charge."""
    return stock(agent_view).get("emp", 0) > 0


#: SNAP radius is 0 by rule (RULEBOOK 4.9.4) -- ONE cell, and the engine
#: refuses a list payload by name. Zero is a legitimate value here, so it
#: cannot use the ``or fallback`` idiom :func:`specs` uses for the EMP:
#: ``0 or 0`` is falsy and would loop forever chasing a truthy radius.
_SNAP_FALLBACK = {"radius": 0, "missiles": 1, "cloud_hours": 1}


def snap_specs(agent_view: Mapping[str, Any]) -> Dict[str, Any]:
    """SNAP specs from the view, with engine-constant fallback.

    Separate from :func:`specs` rather than parameterised, because the two
    weapons do not share a shape: SNAP publishes ``resolves_before_vision``
    and ``missile_speed``, which the EMP has no analogue for, and its radius
    of 0 is a real value the EMP's truthiness fallback would reject.
    """
    orbit = agent_view.get("orbit") or {}
    sp = (orbit.get("weapon_specs") or {}).get("snap") or {}
    out = dict(_SNAP_FALLBACK)
    if "radius" in sp:
        out["radius"] = int(sp.get("radius") or 0)
    if "cloud_hours" in sp:
        out["cloud_hours"] = int(sp.get("cloud_hours") or 0)
    if "missiles_per_launch" in sp:
        out["missiles"] = int(sp.get("missiles_per_launch") or 1)
    # The property the whole weapon is FOR. Absent on a pre-v1.36 view, in
    # which case there is no SNAP to fire anyway and the default is moot.
    out["resolves_before_vision"] = bool(sp.get("resolves_before_vision", True))
    return out


def has_snap(agent_view: Mapping[str, Any]) -> bool:
    """True when the seat has at least one SNAP round."""
    return stock(agent_view).get("snap", 0) > 0
