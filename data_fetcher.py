import heapq
from typing import List, Dict
import pandas as pd
import uuid

class Movie:
    def __init__(
            self,
            title: str,
            description: str,
            year: str,
            genre: List[str] = None,
    ):
        self.id = str(uuid.uuid4()).replace('-', '')[:16]
        self.title = title
        self.genre = genre if genre is not None else []
        self.description = description
        self.year = year

    def __repr__(self):
        return f"({self.id}) {self.title} ({self.year}) - {', '.join(self.genre)}"

    def __lt__(self, other):
        return self.title < other.title

class MovieStack:
    def __init__(self):
        self.movies: Dict[str, Movie] = {}
        self.votes: Dict[str, int] = {}

    def load_movies(self, filename: str):
        df = pd.read_csv(filename)
        for _, row in df.dropna(subset=['original_title', 'overview', 'release_date']).iterrows():
            genres = eval(row['genres'])
            genre_names = [genre['name'] for genre in genres] if genres else []
            movie = Movie(
                title=row['original_title'],
                description=row['overview'],
                year=row['release_date'],
                genre=genre_names,
            )
            self.movies[movie.id] = movie
            self.votes[movie.id] = 0  # initializing votes for each movie to 0

    def get_top_n_movies(self, n: int):
        if n > len(self.movies):
            print("Requested number of movies is greater than the number of movies available.")
            return

        # Convert the dictionary of votes into a list of (vote_count, movie) tuples
        votes_as_tuples = [(-vote_count, movie_id) for movie_id, vote_count in self.votes.items()]

        # Use heapq to find the top n movies based on vote counts
        top_movies = heapq.nsmallest(n, votes_as_tuples)

        # Extract just the movies from the list of tuples
        top_movies = [movie_id for _, movie_id in top_movies]

        return top_movies

    def update_stack(self, movie_id: str, votes: int = 1):
        if movie_id not in self.movies:
            print("Movie not found in the stack.")
            return
        self.votes[movie_id] += votes

    def get_top_movies_str(self, n: int = 100) -> str:
        top_movies = self.get_top_n_movies(n)
        if top_movies:
            top_movies_str = [f"Top {len(top_movies)} Movies:"]
            for i, movie_id in enumerate(top_movies, start=1):
                movie = self.movies[movie_id]
                top_movies_str.append(f"{i}.{movie} (Votes: {self.votes[movie_id]})")
            return "\n".join(top_movies_str)
        else:
            return "No movies to display."

    def print_top_movies(self, n: int = 100):
        top_movies_str = self.get_top_movies_str(n)
        print(top_movies_str)

