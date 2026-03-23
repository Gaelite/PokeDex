"""
Pokemon Search Engine
=====================
Custom search engine with BM25 ranking, autocomplete, and spell correction.
Uses NLTK for text processing (tokenization, stop words, stemming).
"""

import json
import math
import re
import time
from collections import defaultdict, Counter

import nltk
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import PorterStemmer

# Download required NLTK data (only runs once)
nltk.download("punkt", quiet=True)
nltk.download("punkt_tab", quiet=True)
nltk.download("stopwords", quiet=True)


# ============================================================
# TEXT PROCESSOR
# ============================================================
class TextProcessor:
    """Handles tokenization, stop word removal, and stemming using NLTK."""

    def __init__(self):
        self.stemmer = PorterStemmer()
        self.stop_words = set(stopwords.words("english"))

    def tokenize(self, text):
        """Tokenize text using NLTK word_tokenize, keeping only alphanumeric tokens."""
        text = text.lower()
        tokens = word_tokenize(text)
        # Keep only alphanumeric tokens
        tokens = [t for t in tokens if t.isalnum()]
        return tokens

    def remove_stop_words(self, tokens):
        """Remove English stop words using NLTK stopwords corpus."""
        return [t for t in tokens if t not in self.stop_words]

    def stem_tokens(self, tokens):
        """Apply Porter stemming using NLTK PorterStemmer."""
        return [self.stemmer.stem(t) for t in tokens]

    def process(self, text):
        """Full pipeline: tokenize -> remove stop words -> stem."""
        tokens = self.tokenize(text)
        tokens = self.remove_stop_words(tokens)
        tokens = self.stem_tokens(tokens)
        return tokens

    def tokenize_no_stem(self, text):
        """Tokenize and remove stop words without stemming (for autocomplete and spell correction)."""
        tokens = self.tokenize(text)
        tokens = self.remove_stop_words(tokens)
        return tokens


# ============================================================
# INVERTED INDEX
# ============================================================
class InvertedIndex:
    """
    Inverted index with posting lists.

    For each term in the corpus, stores a dictionary mapping
    document IDs to term frequencies. This allows fast lookup
    of which documents contain a given term and how many times.

    Example:
        "dragon" -> {5: 3, 9: 2, 11: 5}
        means "dragon" appears 3 times in doc 5, 2 times in doc 9, etc.
    """

    def __init__(self):
        self.index = defaultdict(dict)  # term -> {doc_id: frequency}
        self.doc_lengths = {}            # doc_id -> number of tokens
        self.doc_count = 0
        self.avg_doc_length = 0
        self.vocabulary = set()

    def add_document(self, doc_id, tokens):
        """Add a document's tokens to the index."""
        self.doc_lengths[doc_id] = len(tokens)
        self.doc_count += 1

        # Count term frequencies in this document
        term_freq = Counter(tokens)
        for term, freq in term_freq.items():
            self.index[term][doc_id] = freq
            self.vocabulary.add(term)

        # Update average document length
        self.avg_doc_length = sum(self.doc_lengths.values()) / self.doc_count

    def get_posting_list(self, term):
        """Return posting list for a term: {doc_id: frequency}."""
        return self.index.get(term, {})

    def get_document_frequency(self, term):
        """Return number of documents containing the term."""
        return len(self.index.get(term, {}))

    def get_stats(self):
        """Return index statistics."""
        return {
            "total_documents": self.doc_count,
            "vocabulary_size": len(self.vocabulary),
            "avg_doc_length": round(self.avg_doc_length, 2),
            "total_postings": sum(
                len(postings) for postings in self.index.values()
            )
        }


# ============================================================
# BM25 SCORING
# ============================================================
class BM25:
    """
    BM25 (Best Matching 25) ranking algorithm.

    Scores documents based on:
    - TF (Term Frequency): how often the term appears in the document
    - IDF (Inverse Document Frequency): how rare the term is across all documents
    - Document length normalization: penalizes long documents slightly

    Parameters:
        k1: controls term frequency saturation (default 1.5)
        b:  controls document length normalization (default 0.75)
    """

    def __init__(self, index, k1=1.5, b=0.75):
        self.index = index
        self.k1 = k1
        self.b = b

    def _idf(self, term):
        """Calculate Inverse Document Frequency for a term."""
        N = self.index.doc_count
        df = self.index.get_document_frequency(term)
        if df == 0:
            return 0
        return math.log((N - df + 0.5) / (df + 0.5) + 1)

    def score(self, query_terms, doc_id):
        """Calculate BM25 score for a single document given query terms."""
        total_score = 0
        doc_len = self.index.doc_lengths.get(doc_id, 0)
        avg_dl = self.index.avg_doc_length

        for term in query_terms:
            tf = self.index.get_posting_list(term).get(doc_id, 0)
            if tf == 0:
                continue

            idf = self._idf(term)
            numerator = tf * (self.k1 + 1)
            denominator = tf + self.k1 * (1 - self.b + self.b * (doc_len / avg_dl))
            total_score += idf * (numerator / denominator)

        return total_score

    def search(self, query_terms):
        """Search and rank all matching documents for the query."""
        # Collect all documents that contain at least one query term
        candidates = set()
        for term in query_terms:
            candidates.update(self.index.get_posting_list(term).keys())

        # Score each candidate
        results = []
        for doc_id in candidates:
            s = self.score(query_terms, doc_id)
            if s > 0:
                results.append((doc_id, s))

        # Sort by score descending
        results.sort(key=lambda x: x[1], reverse=True)
        return results


# ============================================================
# SPELL CORRECTION (Levenshtein Distance)
# ============================================================
class SpellCorrector:
    """
    Spell correction using Levenshtein edit distance.

    Compares a misspelled word against the entire vocabulary
    and suggests the closest matches. Edit distance counts
    the minimum number of insertions, deletions, or substitutions
    needed to transform one string into another.

    Example: "pikchu" -> distance 1 to "pikachu" (insert 'a')
    """

    def __init__(self, vocabulary):
        self.vocabulary = vocabulary

    def levenshtein_distance(self, s1, s2):
        """Calculate edit distance between two strings using dynamic programming."""
        if len(s1) < len(s2):
            return self.levenshtein_distance(s2, s1)

        if len(s2) == 0:
            return len(s1)

        prev_row = list(range(len(s2) + 1))

        for i, c1 in enumerate(s1):
            curr_row = [i + 1]
            for j, c2 in enumerate(s2):
                insertions = prev_row[j + 1] + 1
                deletions = curr_row[j] + 1
                substitutions = prev_row[j] + (0 if c1 == c2 else 1)
                curr_row.append(min(insertions, deletions, substitutions))
            prev_row = curr_row

        return prev_row[-1]

    def suggest(self, word, max_distance=2, max_suggestions=3):
        """Find closest words in vocabulary within max_distance edits."""
        if word in self.vocabulary:
            return []

        candidates = []
        for vocab_word in self.vocabulary:
            # Skip words with very different lengths (optimization)
            if abs(len(vocab_word) - len(word)) > max_distance:
                continue
            dist = self.levenshtein_distance(word, vocab_word)
            if 0 < dist <= max_distance:
                candidates.append((vocab_word, dist))

        candidates.sort(key=lambda x: (x[1], x[0]))
        return [w for w, d in candidates[:max_suggestions]]

    def correct_query(self, tokens):
        """Return suggested corrections for misspelled tokens."""
        corrections = {}
        for token in tokens:
            suggestions = self.suggest(token)
            if suggestions:
                corrections[token] = suggestions
        return corrections


# ============================================================
# AUTOCOMPLETE
# ============================================================
class Autocomplete:
    """
    Prefix-based autocomplete.

    Stores sorted vocabulary terms and matches them against
    user input prefixes. Results are ranked by term frequency
    so more common words appear first.
    """

    def __init__(self, vocabulary):
        self.terms = sorted(vocabulary)
        self.term_freq = {}

    def set_frequencies(self, index):
        """Set term frequencies from the inverted index for ranking."""
        for term in self.terms:
            posting = index.get_posting_list(term)
            self.term_freq[term] = sum(posting.values())

    def suggest(self, prefix, max_results=8):
        """Return autocomplete suggestions for a given prefix."""
        if not prefix or len(prefix) < 1:
            return []

        prefix = prefix.lower().strip()
        matches = [t for t in self.terms if t.startswith(prefix)]
        matches.sort(key=lambda t: (-self.term_freq.get(t, 0), t))
        return matches[:max_results]


# ============================================================
# SEARCH ENGINE
# ============================================================
class PokemonSearchEngine:
    """Main search engine that ties all components together."""

    def __init__(self, corpus_path="corpus.json"):
        self.processor = TextProcessor()
        self.index = InvertedIndex()
        self.documents = {}
        self.raw_vocabulary = set()

        # Load and index the corpus
        self._load_corpus(corpus_path)

        # Initialize ranking and enhancement components
        self.bm25 = BM25(self.index)
        self.spell_corrector = SpellCorrector(self.raw_vocabulary)
        self.autocomplete = Autocomplete(self.raw_vocabulary)
        self.autocomplete.set_frequencies(self.index)

    def _load_corpus(self, path):
        """Load documents from corpus.json and build the inverted index."""
        with open(path, "r", encoding="utf-8") as f:
            corpus = json.load(f)

        for doc in corpus:
            doc_id = doc["id"]
            self.documents[doc_id] = doc

            # Combine all searchable fields into one text
            full_text = f"{doc['title']} {doc['text']}"
            if "type" in doc:
                full_text += " " + " ".join(doc["type"])
            if "category" in doc:
                full_text += " " + doc["category"]
            if "genus" in doc:
                full_text += " " + doc.get("genus", "")
            if "abilities" in doc and isinstance(doc["abilities"], list):
                full_text += " " + " ".join(doc["abilities"])
            if "egg_groups" in doc and isinstance(doc["egg_groups"], list):
                full_text += " " + " ".join(doc["egg_groups"])
            if "habitat" in doc:
                full_text += " " + doc.get("habitat", "")
            if "color" in doc:
                full_text += " " + doc.get("color", "")

            # Build raw vocabulary (unstemmed) for spell correction and autocomplete
            raw_tokens = self.processor.tokenize_no_stem(full_text)
            self.raw_vocabulary.update(raw_tokens)

            # Process text and add to inverted index
            tokens = self.processor.process(full_text)
            self.index.add_document(doc_id, tokens)

    def search(self, query):
        """Execute a search query and return ranked results with metadata."""
        start_time = time.time()

        if not query.strip():
            return {"results": [], "query": query, "time": 0, "corrections": {}}

        # Process the query through the same pipeline as documents
        raw_tokens = self.processor.tokenize_no_stem(query)
        query_tokens = self.processor.process(query)

        # Check for spelling mistakes
        corrections = self.spell_corrector.correct_query(raw_tokens)

        # Rank documents using BM25
        ranked = self.bm25.search(query_tokens)

        # Build result objects
        results = []
        for doc_id, score in ranked:
            doc = self.documents[doc_id]
            results.append({
                "id": doc_id,
                "title": doc["title"],
                "type": doc.get("type", []),
                "generation": doc.get("generation", ""),
                "category": doc.get("category", ""),
                "text": doc["text"],
                "score": round(score, 4),
                "source": doc.get("source", "")
            })

        elapsed = time.time() - start_time

        return {
            "results": results,
            "query": query,
            "processed_terms": query_tokens,
            "time": round(elapsed * 1000, 2),
            "corrections": corrections,
            "total_results": len(results)
        }

    def get_autocomplete(self, prefix):
        """Get autocomplete suggestions for a prefix."""
        return self.autocomplete.suggest(prefix)

    def get_stats(self):
        """Get index statistics."""
        stats = self.index.get_stats()
        stats["raw_vocabulary_size"] = len(self.raw_vocabulary)
        return stats
