"""
build_corpus.py
===============
Script to fetch Pokemon data from PokeAPI and generate corpus.json.
Fetches all 721 Pokemon from Generations 1 through 6.

Run this script once to build your corpus. It takes about 8-10 minutes
because of API rate limiting.

Usage:
    pip install requests
    python build_corpus.py
"""

import requests
import json
import time
import sys

# Generations 1-6 cover Pokemon IDs 1 through 721
TOTAL_POKEMON = 721

# Category assignment based on Pokedex characteristics
def assign_category(species_data, pokemon_data):
    """Assign a category to a Pokemon based on its characteristics."""
    # Check legendary/mythical status
    if species_data.get("is_legendary", False):
        return "Legendary"
    if species_data.get("is_mythical", False):
        return "Mythical"

    # Check if it is a baby Pokemon
    if species_data.get("is_baby", False):
        return "Baby"

    # Check types for category
    types = [t["type"]["name"] for t in pokemon_data["types"]]

    # Check base stat total for pseudo-legendary (600 BST, not legendary)
    bst = sum(s["base_stat"] for s in pokemon_data["stats"])
    if bst >= 600 and not species_data.get("is_legendary") and not species_data.get("is_mythical"):
        return "Pseudo-Legendary"

    # Check if starter (this is approximate based on known starter IDs)
    starter_ids = [1,2,3,4,5,6,7,8,9,          # Gen 1
                   152,153,154,155,156,157,158,159,160,  # Gen 2
                   252,253,254,255,256,257,258,259,260,  # Gen 3
                   387,388,389,390,391,392,393,394,395,  # Gen 4
                   495,496,497,498,499,500,501,502,503,  # Gen 5
                   650,651,652,653,654,655,656,657,658]  # Gen 6
    if species_data["id"] in starter_ids:
        return "Starter"

    # Assign by primary type
    primary_type = types[0].capitalize()
    return primary_type


def fetch_pokemon_data(pokemon_id):
    """Fetch basic Pokemon data (types, stats, abilities)."""
    url = f"https://pokeapi.co/api/v2/pokemon/{pokemon_id}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def fetch_species_data(pokemon_id):
    """Fetch species data (Pokedex descriptions, generation, etc)."""
    url = f"https://pokeapi.co/api/v2/pokemon-species/{pokemon_id}"
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()


def get_english_flavor_texts(species_data, max_entries=6):
    """Extract unique English flavor text entries from species data."""
    seen = set()
    texts = []
    for entry in species_data.get("flavor_text_entries", []):
        if entry["language"]["name"] == "en":
            text = entry["flavor_text"].replace("\n", " ").replace("\f", " ").strip()
            if text not in seen:
                seen.add(text)
                texts.append(text)
                if len(texts) >= max_entries:
                    break
    return texts


def get_english_genus(species_data):
    """Get the Pokemon's genus in English (e.g. 'Seed Pokemon')."""
    for genus in species_data.get("genera", []):
        if genus["language"]["name"] == "en":
            return genus["genus"]
    return ""


def format_stats(pokemon_data):
    """Format base stats into a readable string."""
    stat_names = {
        "hp": "HP",
        "attack": "Attack",
        "defense": "Defense",
        "special-attack": "Special Attack",
        "special-defense": "Special Defense",
        "speed": "Speed"
    }
    parts = []
    total = 0
    for stat in pokemon_data["stats"]:
        name = stat_names.get(stat["stat"]["name"], stat["stat"]["name"])
        val = stat["base_stat"]
        parts.append(f"{val} {name}")
        total += val
    return ", ".join(parts) + f", giving it a base stat total of {total}"


def format_types(pokemon_data):
    """Extract type names."""
    return [t["type"]["name"].capitalize() for t in pokemon_data["types"]]


def format_abilities(pokemon_data):
    """Format abilities into a readable string."""
    regular = []
    hidden = []
    for ab in pokemon_data["abilities"]:
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


def get_generation_number(species_data):
    """Extract generation number from species data."""
    gen_name = species_data["generation"]["name"]
    roman = gen_name.split("-")[1].upper()
    roman_map = {
        "I": 1, "II": 2, "III": 3, "IV": 4, "V": 5,
        "VI": 6, "VII": 7, "VIII": 8, "IX": 9
    }
    return roman_map.get(roman, 0)


def build_document(pokemon_id, index):
    """Build a single document for the corpus."""
    pokemon_data = fetch_pokemon_data(pokemon_id)
    time.sleep(0.3)

    species_data = fetch_species_data(pokemon_id)
    time.sleep(0.3)

    name = pokemon_data["name"].capitalize()
    types = format_types(pokemon_data)
    generation = get_generation_number(species_data)
    genus = get_english_genus(species_data)
    flavor_texts = get_english_flavor_texts(species_data)
    stats_str = format_stats(pokemon_data)
    abilities_str = format_abilities(pokemon_data)
    category = assign_category(species_data, pokemon_data)

    # Build the full document text
    type_str = " and ".join(types)
    text = f"{name} is a {type_str} type Pokemon introduced in Generation {generation}."
    if genus:
        text += f" It is known as the {genus}."
    text += " " + " ".join(flavor_texts)
    text += f" Its base stats are {stats_str}."
    if abilities_str:
        text += " " + abilities_str

    # Calculate height and weight
    height = pokemon_data["height"] / 10  # decimeters to meters
    weight = pokemon_data["weight"] / 10  # hectograms to kg
    text += f" It stands {height} meters tall and weighs {weight} kilograms."

    doc = {
        "id": index + 1,
        "title": name,
        "type": types,
        "generation": generation,
        "category": category,
        "source": f"https://pokeapi.co/api/v2/pokemon-species/{pokemon_id}",
        "text": text,
    }

    return doc, name


def main():
    print("=" * 55)
    print("  Pokemon Corpus Builder")
    print(f"  Fetching {TOTAL_POKEMON} Pokemon from PokeAPI (Gen 1-6)")
    print("  This will take about 8-10 minutes...")
    print("=" * 55)

    corpus = []
    errors = []

    for i in range(TOTAL_POKEMON):
        pokemon_id = i + 1
        try:
            doc, name = build_document(pokemon_id, i)
            corpus.append(doc)
            word_count = len(doc["text"].split())
            # Show progress
            sys.stdout.write(f"\r  [{pokemon_id}/{TOTAL_POKEMON}] {name:<20s} ({word_count} words)")
            sys.stdout.flush()
        except Exception as e:
            errors.append((pokemon_id, str(e)))
            sys.stdout.write(f"\r  [{pokemon_id}/{TOTAL_POKEMON}] ERROR: {e}")
            sys.stdout.flush()
            time.sleep(1)  # Wait a bit longer on error
            continue

    print(f"\n\n{'=' * 55}")
    print(f"  Done! Saved {len(corpus)} documents to corpus.json")

    if corpus:
        word_counts = [len(d["text"].split()) for d in corpus]
        print(f"  Min words per doc: {min(word_counts)}")
        print(f"  Max words per doc: {max(word_counts)}")
        print(f"  Avg words per doc: {sum(word_counts) // len(word_counts)}")

    if errors:
        print(f"\n  {len(errors)} errors:")
        for pid, err in errors:
            print(f"    Pokemon #{pid}: {err}")

    # Save to corpus.json
    with open("corpus.json", "w", encoding="utf-8") as f:
        json.dump(corpus, f, indent=2, ensure_ascii=False)

    print(f"\n  File saved: corpus.json")
    print("=" * 55)


if __name__ == "__main__":
    main()
