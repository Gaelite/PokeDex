"""
build_corpus.py
===============
Fetches all Pokemon data from PokeAPI and generates corpus.json.
Downloads comprehensive info: types, stats, abilities, Pokedex descriptions,
evolution chains, moves, egg groups, habitat, shape, color, and more.

Also stores sprite and cry URLs for use in the frontend.

Usage:
    pip install requests
    python build_corpus.py

The script takes about 30-45 minutes for all Pokemon due to API rate limiting.
Progress is saved incrementally - if interrupted, rerun and it will skip
already-fetched Pokemon.
"""

import requests
import json
import time
import sys
import os

# ---------------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------------
OUTPUT_FILE = "corpus.json"
PROGRESS_FILE = "corpus_progress.json"  # Temp file for incremental saving
API_BASE = "https://pokeapi.co/api/v2"
DELAY = 0.3  # seconds between API calls (be nice to the API)

# Sprite and cry URL templates
SPRITE_URL = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{id}.png"
SPRITE_OFFICIAL_URL = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{id}.png"
CRY_URL = "https://raw.githubusercontent.com/PokeAPI/cries/main/cries/pokemon/latest/{id}.ogg"


# ---------------------------------------------------------------------------
# HELPERS
# ---------------------------------------------------------------------------
def api_get(url, retries=3):
    """GET request with retries."""
    for attempt in range(retries):
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            return r.json()
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2)
            else:
                raise e


def get_english_texts(entries, key="flavor_text", max_entries=6):
    """Extract unique English text entries."""
    seen = set()
    texts = []
    for entry in entries:
        if entry.get("language", {}).get("name") == "en":
            text = entry.get(key, "").replace("\n", " ").replace("\f", " ").strip()
            if text and text not in seen:
                seen.add(text)
                texts.append(text)
                if len(texts) >= max_entries:
                    break
    return texts


def get_english_value(entries, key="name"):
    """Get first English value from a list of localized entries."""
    for entry in entries:
        if entry.get("language", {}).get("name") == "en":
            return entry.get(key, "")
    return ""


def get_generation_number(gen_name):
    """Convert generation name to number."""
    roman_map = {
        "i": 1, "ii": 2, "iii": 3, "iv": 4, "v": 5,
        "vi": 6, "vii": 7, "viii": 8, "ix": 9
    }
    parts = gen_name.split("-")
    if len(parts) >= 2:
        return roman_map.get(parts[1].lower(), 0)
    return 0


# ---------------------------------------------------------------------------
# CATEGORY ASSIGNMENT
# ---------------------------------------------------------------------------
STARTER_IDS = set()
for gen_start in [1, 4, 7, 152, 155, 158, 252, 255, 258, 387, 390, 393,
                  495, 498, 501, 650, 653, 656, 722, 725, 728, 810, 813,
                  816, 906, 909, 912]:
    for offset in range(3):  # starter + 2 evolutions
        STARTER_IDS.add(gen_start + offset)


def assign_category(species_data, pokemon_data):
    """Assign a category based on characteristics."""
    if species_data.get("is_legendary"):
        return "Legendary"
    if species_data.get("is_mythical"):
        return "Mythical"
    if species_data.get("is_baby"):
        return "Baby"

    pid = species_data.get("id", 0)
    if pid in STARTER_IDS:
        return "Starter"

    bst = sum(s["base_stat"] for s in pokemon_data.get("stats", []))
    if bst >= 600:
        return "Pseudo-Legendary"

    types = [t["type"]["name"] for t in pokemon_data.get("types", [])]
    if types:
        return types[0].capitalize()
    return "Other"


# ---------------------------------------------------------------------------
# DATA EXTRACTION
# ---------------------------------------------------------------------------
def format_stats(pokemon_data):
    """Format base stats."""
    stat_names = {
        "hp": "HP", "attack": "Attack", "defense": "Defense",
        "special-attack": "Special Attack", "special-defense": "Special Defense",
        "speed": "Speed"
    }
    parts = []
    total = 0
    for stat in pokemon_data.get("stats", []):
        name = stat_names.get(stat["stat"]["name"], stat["stat"]["name"])
        val = stat["base_stat"]
        parts.append(f"{val} {name}")
        total += val
    return ", ".join(parts) + f", giving it a base stat total of {total}"


def format_types(pokemon_data):
    """Extract type names."""
    return [t["type"]["name"].capitalize() for t in pokemon_data.get("types", [])]


def format_abilities(pokemon_data):
    """Format abilities."""
    regular = []
    hidden = []
    for ab in pokemon_data.get("abilities", []):
        name = ab["ability"]["name"].replace("-", " ").title()
        if ab["is_hidden"]:
            hidden.append(name)
        else:
            regular.append(name)
    if not regular and not hidden:
        return ""
    text = "It has the abilities " + " and ".join(regular)
    if hidden:
        text += f", with the hidden ability {hidden[0]}"
    return text + "."


def get_level_up_moves(pokemon_data, max_moves=10):
    """Get notable moves learned by level up."""
    moves = []
    for move_entry in pokemon_data.get("moves", []):
        for version in move_entry.get("version_group_details", []):
            if version.get("move_learn_method", {}).get("name") == "level-up":
                level = version.get("level_learned_at", 0)
                if level > 0:
                    name = move_entry["move"]["name"].replace("-", " ").title()
                    moves.append((level, name))
                break
    moves.sort(key=lambda x: x[0])
    # Take last N moves (the strongest ones learned at higher levels)
    notable = moves[-max_moves:] if len(moves) > max_moves else moves
    return [f"{name} (level {lvl})" for lvl, name in notable]


def get_egg_groups(species_data):
    """Get egg groups."""
    return [eg["name"].replace("-", " ").title() for eg in species_data.get("egg_groups", [])]


def get_evolution_info(species_data):
    """Get basic evolution info from species data."""
    evolves_from = species_data.get("evolves_from_species")
    if evolves_from:
        return f"It evolves from {evolves_from['name'].capitalize()}."
    return ""


# ---------------------------------------------------------------------------
# BUILD DOCUMENT
# ---------------------------------------------------------------------------
def build_document(pokemon_id, index):
    """Build a single document for the corpus."""
    # Fetch pokemon data (types, stats, abilities, moves)
    pokemon_data = api_get(f"{API_BASE}/pokemon/{pokemon_id}")
    time.sleep(DELAY)

    # Fetch species data (descriptions, generation, evolution, egg groups, etc.)
    species_data = api_get(f"{API_BASE}/pokemon-species/{pokemon_id}")
    time.sleep(DELAY)

    name = pokemon_data["name"].replace("-", " ").capitalize()
    types = format_types(pokemon_data)
    generation = get_generation_number(species_data["generation"]["name"])

    # Genus (e.g., "Seed Pokemon")
    genus = get_english_value(species_data.get("genera", []), "genus")

    # Pokedex descriptions
    flavor_texts = get_english_texts(
        species_data.get("flavor_text_entries", []),
        key="flavor_text",
        max_entries=6
    )

    # Stats, abilities, moves
    stats_str = format_stats(pokemon_data)
    abilities_str = format_abilities(pokemon_data)
    level_moves = get_level_up_moves(pokemon_data)

    # Category
    category = assign_category(species_data, pokemon_data)

    # Egg groups
    egg_groups = get_egg_groups(species_data)

    # Evolution info
    evolution_info = get_evolution_info(species_data)

    # Extra species info
    habitat = species_data.get("habitat")
    habitat_name = habitat["name"].capitalize() if habitat else ""
    shape = species_data.get("shape")
    shape_name = shape["name"].replace("-", " ").capitalize() if shape else ""
    color = species_data.get("color", {}).get("name", "").capitalize()
    growth_rate = species_data.get("growth_rate", {}).get("name", "").replace("-", " ").capitalize()
    capture_rate = species_data.get("capture_rate", 0)
    base_happiness = species_data.get("base_happiness", 0)

    # Physical measurements
    height = pokemon_data.get("height", 0) / 10  # decimeters -> meters
    weight = pokemon_data.get("weight", 0) / 10  # hectograms -> kg

    # ---- Build text ----
    type_str = " and ".join(types)
    text = f"{name} is a {type_str} type Pokemon introduced in Generation {generation}."

    if genus:
        text += f" It is known as the {genus}."

    if evolution_info:
        text += f" {evolution_info}"

    text += " " + " ".join(flavor_texts)

    text += f" Its base stats are {stats_str}."

    if abilities_str:
        text += f" {abilities_str}"

    text += f" It stands {height} meters tall and weighs {weight} kilograms."

    if level_moves:
        text += f" Some of its notable moves include {', '.join(level_moves[:6])}."

    if egg_groups:
        text += f" It belongs to the {' and '.join(egg_groups)} egg groups."

    # ---- Build document ----
    doc = {
        "id": index + 1,
        "pokedex_id": pokemon_id,
        "title": name,
        "type": types,
        "generation": generation,
        "category": category,
        "genus": genus,
        "source": f"{API_BASE}/pokemon-species/{pokemon_id}",
        "text": text,
        # Extra structured data for frontend display
        "stats": {s["stat"]["name"]: s["base_stat"] for s in pokemon_data.get("stats", [])},
        "height": height,
        "weight": weight,
        "color": color,
        "shape": shape_name,
        "habitat": habitat_name,
        "growth_rate": growth_rate,
        "capture_rate": capture_rate,
        "base_happiness": base_happiness,
        "egg_groups": egg_groups,
        "abilities": [a["ability"]["name"].replace("-", " ").title()
                      for a in pokemon_data.get("abilities", [])],
        "is_legendary": species_data.get("is_legendary", False),
        "is_mythical": species_data.get("is_mythical", False),
        "is_baby": species_data.get("is_baby", False),
        "evolves_from": species_data.get("evolves_from_species", {}).get("name", "").capitalize()
                        if species_data.get("evolves_from_species") else "",
        "sprite": SPRITE_URL.format(id=pokemon_id),
        "sprite_official": SPRITE_OFFICIAL_URL.format(id=pokemon_id),
        "cry": CRY_URL.format(id=pokemon_id),
    }

    return doc, name


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------
def main():
    # First, find out how many Pokemon exist
    print("Fetching total Pokemon count from PokeAPI...")
    species_list = api_get(f"{API_BASE}/pokemon-species?limit=1")
    total = species_list["count"]
    print(f"Total Pokemon species in PokeAPI: {total}")
    print()

    # Load progress if exists (for resuming interrupted runs)
    corpus = []
    done_ids = set()
    if os.path.exists(PROGRESS_FILE):
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            corpus = json.load(f)
            done_ids = {d["pokedex_id"] for d in corpus}
        print(f"Resuming from progress file: {len(corpus)} Pokemon already fetched")

    print("=" * 60)
    print(f"  Pokemon Corpus Builder")
    print(f"  Fetching {total} Pokemon from PokeAPI")
    print(f"  This will take about 30-45 minutes...")
    print("=" * 60)

    errors = []
    for i in range(total):
        pokemon_id = i + 1

        if pokemon_id in done_ids:
            continue

        try:
            doc, name = build_document(pokemon_id, len(corpus))
            corpus.append(doc)
            word_count = len(doc["text"].split())
            sys.stdout.write(
                f"\r  [{pokemon_id}/{total}] {name:<25s} "
                f"({word_count} words, Gen {doc['generation']}, {doc['category']})"
            )
            sys.stdout.flush()

            # Save progress every 50 Pokemon
            if len(corpus) % 50 == 0:
                with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
                    json.dump(corpus, f, ensure_ascii=False)

        except Exception as e:
            errors.append((pokemon_id, str(e)))
            sys.stdout.write(f"\r  [{pokemon_id}/{total}] ERROR: {e}")
            sys.stdout.flush()
            time.sleep(2)
            continue

    # Re-index all documents sequentially
    for i, doc in enumerate(corpus):
        doc["id"] = i + 1

    # Save final corpus
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(corpus, f, indent=2, ensure_ascii=False)

    # Clean up progress file
    if os.path.exists(PROGRESS_FILE):
        os.remove(PROGRESS_FILE)

    # Print summary
    print(f"\n\n{'=' * 60}")
    print(f"  Done! Saved {len(corpus)} documents to {OUTPUT_FILE}")

    if corpus:
        word_counts = [len(d["text"].split()) for d in corpus]
        gens = {}
        cats = {}
        for d in corpus:
            g = d["generation"]
            c = d["category"]
            gens[g] = gens.get(g, 0) + 1
            cats[c] = cats.get(c, 0) + 1

        print(f"  Min words per doc: {min(word_counts)}")
        print(f"  Max words per doc: {max(word_counts)}")
        print(f"  Avg words per doc: {sum(word_counts) // len(word_counts)}")
        print()
        print("  Pokemon per generation:")
        for g in sorted(gens):
            print(f"    Gen {g}: {gens[g]}")
        print()
        print("  Pokemon per category:")
        for c in sorted(cats):
            print(f"    {c}: {cats[c]}")

    if errors:
        print(f"\n  {len(errors)} errors:")
        for pid, err in errors[:20]:
            print(f"    Pokemon #{pid}: {err}")
        if len(errors) > 20:
            print(f"    ... and {len(errors) - 20} more")

    print(f"\n  File saved: {OUTPUT_FILE}")
    print("=" * 60)


if __name__ == "__main__":
    main()
