# PokeSearch Engine

A BM25-powered search engine for Pokemon data, built from scratch in Python with Flask.

## Student Information

- **Full Name:** Eduardo Gael García Zuviría
- **Domain:** Pokemon (Pokedex entries, types, stats, abilities, moves, evolution chains, and lore)
- **Implemented Enhancement:** G - Spell Correction (Levenshtein distance) + C - Autocomplete (prefix-based with frequency ranking)

## Domain Justification

Pokemon is one of the richest and most well-documented fictional universes, with over 1000 creatures each having unique types, abilities, stats, and lore descriptions from multiple game versions. This makes it an ideal domain for a search engine because:

- Each Pokemon entry is a self-contained document with rich, varied text sourced from the PokeAPI
- Users can search by many dimensions: type, ability, generation, legendary status, evolution, habitat, moves, egg groups, and more
- The vocabulary is a mix of standard English and Pokemon-specific terms, making it a good test case for text processing, spell correction, and autocomplete

## Implemented Enhancements

### G - Spell Correction

Uses the Levenshtein edit distance algorithm to detect misspelled words in the query. When a word is not found in the vocabulary, it calculates the minimum number of insertions, deletions, or substitutions needed to match known words and suggests the closest ones. For example, typing "pikchu" suggests "pikachu".

### C - Autocomplete

As the user types in the search bar, prefix-based suggestions appear in real time. The suggestions are ranked by term frequency in the corpus, so more common and relevant words appear first. Supports keyboard navigation with arrow keys.

## Screenshots

### Landing Page

<img width="1193" height="948" alt="Screenshot 2026-03-22 at 10 33 44 p m" src="https://github.com/user-attachments/assets/f8722e1a-cf1a-43d2-803e-ce5b25e5cb68" />

### Search Results

<img width="1528" height="978" alt="Screenshot 2026-03-22 at 10 34 08 p m" src="https://github.com/user-attachments/assets/b3b45cde-2fe2-48f5-a6e4-6819dce0a97a" />

### Autocomplete

<img width="1347" height="349" alt="Screenshot 2026-03-22 at 10 34 36 p m" src="https://github.com/user-attachments/assets/5e2f768c-e69c-4105-96df-5f0515ea4955" />

### Spell Correction

<img width="1328" height="727" alt="Screenshot 2026-03-22 at 10 34 54 p m" src="https://github.com/user-attachments/assets/9a455e43-326e-45cb-b23d-81ad4dc4014a" />

### Detail Modal

<img width="1535" height="953" alt="Screenshot 2026-03-22 at 10 35 17 p m" src="https://github.com/user-attachments/assets/af57496a-145d-48e6-9b39-74ff7e8dc5f4" />

## Instructions to Run Locally

### Prerequisites

- Python 3.8+
- pip

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/Gaelite/PokeDex.git
cd PokeDex

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download NLTK data (run once)
python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('stopwords')"

# 4. Run the application
python app.py

# 5. Open your browser
# Go to http://127.0.0.1:5000
```

If NLTK download fails due to SSL errors on Mac, run this instead for step 3:

```bash
python -c "import ssl; ssl._create_default_https_context = ssl._create_unverified_context; import nltk; nltk.download('punkt'); nltk.download('punkt_tab'); nltk.download('stopwords')"
```

## Project Structure

```
PokeDex/
    README.md              # This file
    corpus.json            # Pokemon documents with sources from PokeAPI
    search_engine.py       # Search engine (text processing, inverted index, BM25, spell correction, autocomplete)
    app.py                 # Flask web server
    templates/
        index.html         # HTML template with Pokemon cards and detail modal
    static/
        style.css          # Dark minimalist styling with retro touches
        app.js             # Autocomplete, highlighting, cry playback, detail modal
    scripts/
        build_corpus.py    # Script to fetch Pokemon data from PokeAPI and generate corpus.json
    requirements.txt       # Python dependencies
```

## Corpus

- Documents sourced from PokeAPI (https://pokeapi.co)
- Each document contains: name, types, generation, Pokedex descriptions from multiple game versions, base stats, abilities, notable moves, egg groups, height, weight, habitat, evolution info, and more
- Every document has 50+ words
- The corpus was generated using `scripts/build_corpus.py` which fetches data directly from the PokeAPI REST endpoints

## Technical Details

### Text Processing Pipeline

1. **Tokenization:** NLTK word_tokenize (with regex fallback)
2. **Lowercase normalization:** All text converted to lowercase
3. **Stop word removal:** NLTK English stopwords (with built-in fallback list)
4. **Stemming:** NLTK Porter Stemmer (with built-in fallback)

### BM25 Parameters

- k1 = 1.5 (term frequency saturation)
- b = 0.75 (document length normalization)

### Spell Correction

- Levenshtein edit distance algorithm implemented from scratch
- Maximum edit distance of 2 for suggestions
- Length-based pre-filtering for efficiency
- Returns up to 3 suggestions per misspelled term

### Autocomplete

- Prefix-based matching against the full unstemmed vocabulary
- Suggestions ranked by term frequency in the corpus
- Debounced API requests (150ms) for performance
- Keyboard navigation support (arrow keys + enter)

### Additional Features

- Pokemon sprite images loaded from PokeAPI sprites repository
- Pokemon cry audio playback from PokeAPI cries repository
- Click on any result card to see full detail modal with stats bars, abilities, evolution info, habitat, and more
- Term highlighting in search results
- Responsive grid layout
