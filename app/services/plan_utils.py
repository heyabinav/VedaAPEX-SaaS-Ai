from __future__ import annotations

from typing import Optional

PAID_PLAN_CODES = {"PRO", "MAX", "ULTRA"}

_PLAN_DISPLAY_NAMES = {
    "free": "Free",
    "pro": "Pro",
    "max": "Max",
    "ultra": "Ultra",
}


def normalize_plan_slug(plan_name: Optional[str]) -> str:
    if not plan_name:
        return "free"

    slug = str(plan_name).strip().lower().replace("_", " ").replace("-", " ")
    if slug.endswith(" plan"):
        slug = slug[:-5].strip()
    slug = slug.replace(" ", "")
    return slug or "free"


def normalize_plan_code(plan_name: Optional[str]) -> str:
    return normalize_plan_slug(plan_name).upper()


def is_paid_plan(plan_name: Optional[str]) -> bool:
    return normalize_plan_code(plan_name) in PAID_PLAN_CODES


def display_plan_name(plan_name: Optional[str]) -> str:
    slug = normalize_plan_slug(plan_name)
    if slug in _PLAN_DISPLAY_NAMES:
        return _PLAN_DISPLAY_NAMES[slug]
    if not plan_name:
        return "Free"
    return str(plan_name).strip().title()