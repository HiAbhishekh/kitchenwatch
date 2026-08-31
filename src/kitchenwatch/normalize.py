from __future__ import annotations

import re

# Small, explicit map. Not a food ontology. Unknown names stay as slugified text.
_SYNONYMS: dict[str, str] = {
    "milk": "milk",
    "whole_milk": "milk",
    "toned_milk": "milk",
    "2_percent_milk": "milk",
    "two_percent_milk": "milk",
    "egg": "eggs",
    "eggs": "eggs",
    "spinach": "spinach",
    "baby_spinach": "spinach",
    "bread": "bread",
    "sliced_bread": "bread",
    "tomato": "tomato",
    "tomatoes": "tomato",
    "onion": "onion",
    "onions": "onion",
    "butter": "butter",
    "oil": "oil",
    "olive_oil": "oil",
    "chicken": "chicken",
    "chicken_breast": "chicken",
}


_NON_ALNUM = re.compile(r"[^a-z0-9]+")


def canonical_item_id(raw: str) -> str:
    text = raw.strip().lower().replace("%", " percent ")
    slug = _NON_ALNUM.sub("_", text).strip("_")
    if not slug:
        raise ValueError("empty item name")
    return _SYNONYMS.get(slug, slug)
