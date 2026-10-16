# -*- coding: utf-8 -*-
"""In-process Qloo Taste Graph mock (offline demo + tests).

Deterministic stand-in so the full agent loop runs with zero setup. The live
client in qloo.py implements the same interface against the real API.
"""
from __future__ import annotations

# anchor -> canonical taste tags (the taste graph's semantic expansion layer)
ANCHOR_TAGS = {
    "jazz": ["jazz", "live-music", "blues", "saxophone", "late-night"],
    "sci-fi": ["sci-fi", "space", "futuristic", "technology"],
    "romantic": ["romance", "intimate", "candlelit", "date-night"],
    "spicy": ["spicy", "sichuan", "hot"],
    "vegan": ["vegan", "plant-based", "healthy"],
    "classical": ["classical", "orchestra", "piano", "calm"],
    "streetwear": ["streetwear", "casual", "sneakers", "urban"],
    "coffee": ["coffee", "cafe", "specialty", "morning"],
    "anime": ["anime", "japanese", "animation"],
    "hiking": ["hiking", "outdoors", "nature", "scenic"],
    "electronic": ["electronic", "dance", "retro"],
}

_ENTITIES = [
    # dining
    {"id": "d_jazz_lounge", "currency": "CNY", "name": "Blue Note Cellar", "domain": "dining",
     "tags": ["jazz", "live-music", "cocktail", "date-night"], "locale": "shanghai",
     "price": 380, "rating": 4.6, "source": "qloo://entity/d_jazz_lounge"},
    {"id": "d_sichuan", "currency": "CNY", "name": "Chuan Yu Hotpot", "domain": "dining",
     "tags": ["spicy", "sichuan", "hot", "chinese"], "locale": "shanghai",
     "price": 130, "rating": 4.4, "source": "qloo://entity/d_sichuan"},
    {"id": "d_vegan", "currency": "CNY", "name": "Green Bowl Kitchen", "domain": "dining",
     "tags": ["vegan", "plant-based", "healthy"], "locale": "shanghai",
     "price": 65, "rating": 4.2, "source": "qloo://entity/d_vegan"},
    {"id": "d_omakase", "currency": "CNY", "name": "Sakura Omakase", "domain": "dining",
     "tags": ["japanese", "omakase", "refined", "date-night"], "locale": "shanghai",
     "price": 680, "rating": 4.8, "source": "qloo://entity/d_omakase"},
    # music
    {"id": "m_kind_of_blue", "name": "Kind of Blue (Miles Davis)", "domain": "music",
     "tags": ["jazz", "classic", "saxophone"], "locale": "global",
     "price": 0, "rating": 4.9, "source": "qloo://entity/m_kind_of_blue"},
    {"id": "m_daft", "name": "Random Access Memories", "domain": "music",
     "tags": ["electronic", "dance", "retro"], "locale": "global",
     "price": 0, "rating": 4.5, "source": "qloo://entity/m_daft"},
    {"id": "m_moonlight", "name": "Clair de Lune (Debussy)", "domain": "music",
     "tags": ["classical", "piano", "calm"], "locale": "global",
     "price": 0, "rating": 4.7, "source": "qloo://entity/m_moonlight"},
    # film
    {"id": "f_mood", "name": "In the Mood for Love", "domain": "film",
     "tags": ["romance", "cantonese", "cinematic", "intimate"], "locale": "global",
     "price": 0, "rating": 4.8, "source": "qloo://entity/f_mood"},
    {"id": "f_interstellar", "name": "Interstellar", "domain": "film",
     "tags": ["sci-fi", "space", "technology"], "locale": "global",
     "price": 0, "rating": 4.7, "source": "qloo://entity/f_interstellar"},
    {"id": "f_yourname", "name": "Your Name", "domain": "film",
     "tags": ["anime", "japanese", "romance"], "locale": "global",
     "price": 0, "rating": 4.6, "source": "qloo://entity/f_yourname"},
    # fashion
    {"id": "fa_street", "currency": "CNY", "name": "Jing'an Streetwear Capsule", "domain": "fashion",
     "tags": ["streetwear", "casual", "urban", "sneakers"], "locale": "shanghai",
     "price": 450, "rating": 4.1, "source": "qloo://entity/fa_street"},
    {"id": "fa_linen", "currency": "CNY", "name": "Quiet Linen Edit", "domain": "fashion",
     "tags": ["minimal", "linen", "refined", "casual"], "locale": "shanghai",
     "price": 520, "rating": 4.3, "source": "qloo://entity/fa_linen"},
    # travel
    {"id": "t_westlake", "name": "West Lake Sunset Walk", "domain": "travel",
     "tags": ["scenic", "nature", "romance", "outdoors"], "locale": "hangzhou",
     "price": 0, "rating": 4.7, "source": "qloo://entity/t_westlake"},
    {"id": "t_hike", "currency": "CNY", "name": "Moganshan Ridge Trail", "domain": "travel",
     "tags": ["hiking", "outdoors", "nature", "scenic"], "locale": "shanghai",
     "price": 120, "rating": 4.4, "source": "qloo://entity/t_hike"},
]


class MockQloo:
    """Deterministic offline stand-in for the Qloo Taste Graph."""

    def __init__(self, entities=None, anchor_tags=None):
        self.entities = [dict(e) for e in entities] if entities is not None \
            else [dict(e) for e in _ENTITIES]
        self.anchor_tags = dict(anchor_tags) if anchor_tags is not None else dict(ANCHOR_TAGS)
        self.calls = 0

    def get_entity(self, entity_id):
        for e in self.entities:
            if e["id"] == entity_id:
                return dict(e)
        return None

    def expand_anchor(self, anchor):
        self.calls += 1
        a = anchor.lower().strip()
        tags = self.anchor_tags.get(a)
        if tags is None:
            for k, v in self.anchor_tags.items():
                if a and (a in k or k in a):
                    tags = v
                    break
        tags = list(tags) if tags else [a]
        related = [e["id"] for e in self.entities
                   if set(t.lower() for t in e["tags"]) & set(t.lower() for t in tags)]
        return {"anchor": a, "tags": tags, "related_entities": related}

    def search(self, domain, tags, locale=None, limit=8):
        self.calls += 1
        want = set(t.lower() for t in tags)
        out = []
        for e in self.entities:
            if e["domain"] != domain:
                continue
            if locale and e.get("locale") not in (locale, "global"):
                continue
            matched = sorted(set(t.lower() for t in e["tags"]) & want)
            if not matched:
                continue
            score = (len(matched) / max(1, len(want))) * 0.7 + (e["rating"] / 5.0) * 0.3
            out.append({"entity": dict(e), "matched_tags": matched, "score": round(score, 4)})
        out.sort(key=lambda r: r["score"], reverse=True)
        return out[:limit]

    def affinity(self, entity_id, profile_tags):
        self.calls += 1
        ent = self.get_entity(entity_id)
        if ent is None:
            return {"entity_id": entity_id, "score": 0.0, "matched_tags": []}
        pt = set(t.lower() for t in profile_tags)
        et = set(t.lower() for t in ent["tags"])
        matched = sorted(pt & et)
        return {"entity_id": entity_id,
                "score": round(len(matched) / max(1, len(pt)), 4),
                "matched_tags": matched}
