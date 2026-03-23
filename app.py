"""
Pokemon Search Engine - Web Application
========================================
Flask-based web interface for the Pokemon search engine.
"""

from flask import Flask, render_template, request, jsonify
from search_engine import PokemonSearchEngine
import os

app = Flask(__name__)

# Initialize search engine
engine = PokemonSearchEngine(
    corpus_path=os.path.join(os.path.dirname(__file__), "corpus.json")
)


@app.route("/")
def home():
    """Render the main search page with index statistics."""
    stats = engine.get_stats()
    return render_template("index.html", stats=stats)


@app.route("/search")
def search():
    """Handle search queries and return results page."""
    query = request.args.get("q", "").strip()
    results = engine.search(query)
    stats = engine.get_stats()
    return render_template("index.html", results=results, stats=stats, query=query)


@app.route("/api/search")
def api_search():
    """API endpoint for search (used by JavaScript)."""
    query = request.args.get("q", "").strip()
    results = engine.search(query)
    return jsonify(results)


@app.route("/api/autocomplete")
def api_autocomplete():
    """API endpoint for autocomplete suggestions."""
    prefix = request.args.get("q", "").strip()
    suggestions = engine.get_autocomplete(prefix)
    return jsonify({"suggestions": suggestions, "prefix": prefix})


@app.route("/api/stats")
def api_stats():
    """API endpoint for index statistics."""
    return jsonify(engine.get_stats())


if __name__ == "__main__":
    print("PokeSearch Engine is running!")
    print("Open http://127.0.0.1:5000 in your browser")
    app.run(debug=True, port=5000)
