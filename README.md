# rasa_movie_chatbot
A Task-Oriented Dialog System built with Rasa

This project implements a task-oriented dialogue system using Rasa.
The chatbot helps users with movie-related tasks such as recommendations by genre,
showing trending movies, and providing information about specific titles.

## Domain and Motivation

The chatbot operates in the movie domain.
Movies are a suitable domain for a task-oriented dialogue system because users
naturally ask for recommendations, trending titles, and details about specific movies.
Additionally, this domain allows the combination of simulated actions and real-world data sources.

## Implemented Interaction Scenarios

The chatbot supports three distinct interaction scenarios, each corresponding
to a different user goal.

### Scenario 1: Genre-based Movie Recommendations (Mock Data)

In this scenario, the user asks for movie recommendations based on a specific genre.
The chatbot returns a predefined list of five movies per genre.
This scenario is implemented as a simulated task execution using mock data,
without accessing any external data source.

### Scenario 2: Trending Movies Right Now (TMDB API)

In this scenario, the user asks for movies that are currently popular.
The chatbot retrieves trending movies using the TMDB API and returns the top results.
This scenario demonstrates real-world data integration through an external API.

### Scenario 3: Movie Information from a Local CSV Dataset

In this scenario, the user asks for information about a specific movie,
such as its plot or duration.
The chatbot searches a local CSV file that contains a subset of Netflix titles
and returns the relevant information.

## Data Sources

The chatbot integrates both real-world and simulated data sources.

### TMDB API (Scenario 2)

For the second interaction scenario, the chatbot retrieves trending movies
using The Movie Database (TMDB) API.
This allows the chatbot to dynamically fetch up-to-date information
about movies that are currently popular.

The API key is obtained from:
https://www.themoviedb.org/settings/api

### Local CSV Dataset (Scenario 3)

For the third interaction scenario, the chatbot uses a local CSV file
(`netflix_titles.csv`) that contains a manually created subset of the Netflix titles dataset.
The original dataset was obtained from:
https://github.com/allenkong221/netflix-titles-dataset

The local CSV file includes information such as movie title, release year,
duration, and description, which are used to answer user queries.

## Error Handling and Robustness

The chatbot includes basic mechanisms to handle errors and unexpected situations.

If the TMDB API is unavailable or the API key is missing, the chatbot returns
a meaningful message informing the user that the service is currently unavailable.

For movie queries from the local dataset, the chatbot applies normalization
and fuzzy matching techniques to handle typos or slightly different movie titles.
If no matching movie is found, the user is informed accordingly.

A fallback intent is also used to handle cases where the chatbot
cannot confidently understand the user's input.

## Setup and Running the Chatbot

To run the chatbot locally, follow the steps below.

### 1) Create and activate a virtual environment (Windows)

```bash
python -m venv venv
venv\Scripts\activate
```

### 2) Install dependencies

```bash
pip install rasa rasa-sdk requests
```

### 3) Set the TMDB API key

An environment variable named TMDB_API_KEY must be set.

```bash
set TMDB_API_KEY=YOUR_API_KEY_HERE
```

### 4) Run the chatbot

In one terminal, run the action server:

```bash
rasa run actions
```

In another terminal, train and start the chatbot:

```bash
rasa train
rasa shell
```

## Example Queries

Below are some example user queries that demonstrate the chatbot's functionality:

- suggest a comedy
- recommend an action movie
- what is popular right now?
- show me trending movies
- tell me about Inception
- how long is The Irishman?
- what is the plot of Matilda?
