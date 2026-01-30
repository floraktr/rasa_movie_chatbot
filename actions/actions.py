from typing import Any, Text, Dict, List
import os
import csv
import re
from pathlib import Path
from difflib import SequenceMatcher

import requests
from rasa_sdk import Action, Tracker
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.events import SlotSet


def get_project_root() -> Path:
    """
    This function helps us find the root directory of our project
    so we can locate the data folder and the csv files.
    """
    return Path(__file__).resolve().parent.parent


def similarity(a: str, b: str) -> float:
    """
    This is a helper function to calculate how similar two strings are.
    It helps us find titles even if the user makes a typo.
    """
    return SequenceMatcher(None, a, b).ratio()


def extract_title_from_text(text: str) -> str:
    """
    This function tries to clean the user's input to find the title.
    It removes common phrases to isolate the name of the movie.
    """
    text = text.lower().strip()
    quoted = re.findall(r'"([^"]+)"', text)
    if quoted:
        return quoted[0].strip()

    phrases = [
        "tell me about", "what is", "info for", "details for",
        "plot of", "duration of", "story of", "how long is"
    ]
    cleaned = text
    for p in phrases:
        if cleaned.startswith(p):
            cleaned = cleaned.replace(p, "", 1)
    return cleaned.strip(" ?!., sync'\"")


def normalize_title(title: str) -> str:
    """
    This function normalizes the titles for easier comparison.
    """
    if not title: return ""
    t = title.lower().strip()
    t = re.sub(r"[^a-z0-9\s]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    return t


def get_row_value_case_insensitive(row: Dict[str, Any], key: str) -> str:
    """
    Safely gets a value from a CSV row regardless of header casing.
    """
    key_lower = key.lower()
    for k, v in row.items():
        if str(k).lower() == key_lower:
            return "" if v is None else str(v)
    return ""


_DATASET_CACHE: Dict[str, Any] = {}


def build_dataset_index(dataset_path: Path) -> Dict[Text, Any]:
    """
    This function builds an index for the CSV data for fast lookup.
    """
    cache_key = str(dataset_path.resolve())
    if cache_key in _DATASET_CACHE:
        return _DATASET_CACHE[cache_key]

    rows_by_norm: Dict[str, Dict[str, Any]] = {}
    titles_set: set[str] = set()

    with dataset_path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = get_row_value_case_insensitive(row, "title").strip()
            if not name: continue
            n = normalize_title(name)
            rows_by_norm[n] = row
            titles_set.add(n)

    index = {"rows_by_norm": rows_by_norm, "titles_set": titles_set}
    _DATASET_CACHE[cache_key] = index
    return index


# Scenario 1: Recommendations based on genre (5 movies per genre)
class ActionSuggestMoviesByGenre(Action):
    def name(self) -> Text:
        return "action_suggest_movies_by_genre"

    def run(self, dispatcher, tracker, domain) -> List[Dict]:
        genre = tracker.get_slot("genre")
        movies_by_genre = {
            "comedy": ["Superbad", "The Hangover", "Mean Girls", "Step Brothers", "Booksmart"],
            "action": ["Mad Max: Fury Road", "John Wick", "Gladiator", "Die Hard", "The Dark Knight"],
            "drama": ["Forrest Gump", "The Shawshank Redemption", "Fight Club", "The Godfather", "Parasite"],
            "thriller": ["Se7en", "Gone Girl", "Shutter Island", "The Silence of the Lambs", "Nightcrawler"],
            "horror": ["Get Out", "The Conjuring", "Hereditary", "A Quiet Place", "It"],
            "sci-fi": ["Inception", "Interstellar", "The Matrix", "Blade Runner 2049", "Arrival"]
        }

        if not genre:
            dispatcher.utter_message(response="utter_ask_genre")
            return []

        genre = genre.lower()
        if genre in movies_by_genre:
            movies = ", ".join(movies_by_genre[genre])
            dispatcher.utter_message(text=f"Here are 5 {genre} movies you might like: {movies}.")
        else:
            dispatcher.utter_message(text=f"I don't have 5 suggestions for '{genre}' yet.")
        return []


# Scenario 2: Trending movies from External API (TMDB)
class ActionGetTrendingMovies(Action):
    def name(self) -> Text:
        return "action_get_trending_movies"

    def run(self, dispatcher, tracker, domain) -> List[Dict]:
        api_key = os.getenv("TMDB_API_KEY")
        if not api_key:
            dispatcher.utter_message(text="Trending service is currently unavailable.")
            return []

        url = "https://api.themoviedb.org/3/trending/movie/day"
        try:
            response = requests.get(url, params={"api_key": api_key, "language": "en-US"}, timeout=10)
            results = response.json().get("results", [])[:5]
            movies = [f"{m.get('title')} ({m.get('release_date', '')[:4]})" for m in results]
            dispatcher.utter_message(text="Trending today:\n- " + "\n- ".join(movies))
        except Exception:
            dispatcher.utter_message(text="Error connecting to movie service.")
        return []


# Scenario 3: Detailed info from Dataset with targeted logic
class ActionMovieDetailsFromDataset(Action):
    """
    This action searches our CSV for a specific movie and
    decides whether to show the plot, duration, or a general summary.
    """

    def name(self) -> Text:
        return "action_movie_details_from_dataset"

    def run(self, dispatcher, tracker, domain) -> List[Dict]:
        movie_title_slot = tracker.get_slot("movie_title")
        user_text = tracker.latest_message.get("text", "").lower()
        dataset_path = get_project_root() / "data" / "netflix_titles.csv"

        # Determine title from Slot or raw text
        raw_input = movie_title_slot if movie_title_slot else extract_title_from_text(user_text)
        target_norm = normalize_title(raw_input)

        if not target_norm:
            dispatcher.utter_message(text="Which movie are you interested in?")
            return []

        index = build_dataset_index(dataset_path)
        row = index["rows_by_norm"].get(target_norm)

        # Fuzzy search fallback
        if not row:
            best_match, best_score = None, 0.0
            for db_title_norm in index["titles_set"]:
                score = similarity(target_norm, db_title_norm)
                if score > best_score:
                    best_score, best_match = score, db_title_norm
            if best_score > 0.8:
                row = index["rows_by_norm"].get(best_match)

        if row:
            name = get_row_value_case_insensitive(row, "title")
            duration = get_row_value_case_insensitive(row, "duration")
            plot = get_row_value_case_insensitive(row, "description")
            year = get_row_value_case_insensitive(row, "release_year")

            # Check if user specifically asked for duration
            if any(word in user_text for word in ["long", "duration", "time", "length"]):
                dispatcher.utter_message(text=f"The duration of '{name}' is {duration}.")

            # Check if user specifically asked for plot
            elif any(word in user_text for word in ["plot", "story", "about", "summary"]):
                dispatcher.utter_message(text=f"The plot of '{name}': {plot}")

            # Default to general info
            else:
                dispatcher.utter_message(
                    text=f"{name} ({year})\n- Duration: {duration}\n- Summary: {plot[:120]}..."
                )
        else:
            dispatcher.utter_message(text=f"I couldn't find '{raw_input}' in the dataset.")

        return [SlotSet("movie_title", None)]