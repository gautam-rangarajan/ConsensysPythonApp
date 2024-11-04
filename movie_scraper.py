from imdb import Cinemagoer
import json
import pandas as pd
from pathlib import Path
import requests
from tenacity import retry, stop_after_attempt, wait_fixed
import time
import timeit
from supabase import create_client, Client


# Given a date range, fetch all the movies that were released during that period.
# Additional filters like language/minimum vote count can also be specified

class MovieScraper:
    MINIMUM_VOTE_COUNT = 100
    LANGUAGES = ["en"]
    CACHE_FILE = Path("bin/movie_synopsis_cache.json")
    SUPABASE_CLIENT: Client = None
    TABLE_NAME = "movies_raw_data"
    
    def __init__(self):
        url = "https://qamoyltkfqipmyolhfat.supabase.co"
        key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFhbW95bHRrZnFpcG15b2xoZmF0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcxNDEwMjA2MCwiZXhwIjoyMDI5Njc4MDYwfQ.sNrXGQLpZEKcV0kBZ7tv669Yj8YDxKFBRN00VKNHMqA"
        self.SUPABASE_CLIENT = create_client(url, key)

    def get_tmdb_movies_in_range(self, start, end):
        api_key = '0b2cc6b5655e6c00206bd71118d1156f'
        languages = ",".join(self.LANGUAGES)
        url = f'https://api.themoviedb.org/3/discover/movie?api_key={api_key}&primary_release_date.gte={start}&primary_release_date.lte={end}&include_adult=false&include_video=false&with_original_language={languages}&page=1&sort_by=popularity.desc&vote_count.gte={self.MINIMUM_VOTE_COUNT}'
        response = requests.get(url)
        data = response.json()
        total_pages = data["total_pages"]
        total_results = data["total_results"]
        movies_in_date_range = []
        print(f"total_results: {total_results}")

        for page in range(total_pages):
            try:
                url = f'https://api.themoviedb.org/3/discover/movie?api_key={api_key}&primary_release_date.gte={start}&primary_release_date.lte={end}&include_adult=false&include_video=false&with_original_language={languages}&page={page+1}&sort_by=popularity.desc'
                response = requests.get(url)
                data = response.json()
                movies_in_date_range.extend(data["results"])
            except Exception as e:
                print(e)
                time.sleep(.1)
        print(f"total_results extracted: {len(movies_in_date_range)}")
        return movies_in_date_range

    def get_imdb_ids_for_tmdb_movies_in_range(self, start, end):
        api_key = '0b2cc6b5655e6c00206bd71118d1156f'

        movies = self.get_tmdb_movies_in_range(start, end)
        imdb_ids = []
        found_movies = []
        low_votes_movies = []
        missing_movies = []
        for movie in movies:
            try:
                id = movie["id"]
                url = f"https://api.themoviedb.org/3/movie/{id}/external_ids?api_key={api_key}"
                response = requests.get(url)
                data = response.json()
                imdb_id = data["imdb_id"]
                if imdb_id is not None:
                    if int(movie["vote_count"]) >= self.MINIMUM_VOTE_COUNT:
                        imdb_ids.append(imdb_id)
                        found_movies.append((id, movie["original_title"], movie["vote_count"]))
                    else:
                        low_votes_movies.append((id, movie["original_title"], movie["vote_count"]))
                else:
                    missing_movies.append((id, movie["original_title"], movie["vote_count"]))
            except Exception as e:
                print(e)
                time.sleep(1)
        print(f"Number of imdb ids extracted: {len(imdb_ids)}")
        print(f"Missing movies: {missing_movies}")
        print(f"Low votes movies: {low_votes_movies}")
        print(f"Found movies: {found_movies}")
        return imdb_ids

    # Function to load cache data from a file
    def load_cache(self):
        if self.CACHE_FILE.is_file() and self.CACHE_FILE.stat().st_size > 0:
            with open(self.CACHE_FILE, 'r') as file:
                try:
                    return json.load(file)
                except json.JSONDecodeError:
                    return {}
        return {}

    # Function to save cache data to a file
    def save_cache(self, cache):
        with open(self.CACHE_FILE, 'w') as file:
            json.dump(cache, file, indent=4)

    # Create methods to fetch movie details given a list of imdb movie ids
    def get_movie_details(self, imdb_id):
        cache = self.load_cache()
        cg = Cinemagoer()

        # Check if the movie data is in cache
        if imdb_id in cache:
            print("Retrieved from cache.")
            return cache[imdb_id]

        # If not in cache, get movie data
        start = timeit.default_timer()
        cg_imdb_id = imdb_id.replace("tt", "")
        movie = cg.get_movie(cg_imdb_id)
        end = timeit.default_timer()
        print("get_movie_details took {} seconds to run".format(end - start))
        result = {}

        keys = ["title", "genres", "runtimes", "original air date", "rating", "votes", "imdbID", "language codes", "year", "director", "cast"]
        for key in keys:
            if key not in movie:
                result[key] = None
            elif key == "cast":
                result[key] = [c.personID for c in movie[key][:5]]
            elif key == "director":
                result[key] = [c.personID for c in movie[key]]
            else:
                result[key] = movie.get(key, None)

        synopsis_present = True if "synopsis" in movie and len(movie["synopsis"]) > 0 else False
        plot_present = True if "plot" in movie and len(movie["plot"]) > 0 else False
        if synopsis_present and plot_present:
            result["synopsis"] = movie["synopsis"][0]
            result["plot"] = movie["plot"][0]
        elif synopsis_present:
            result["synopsis"] = movie["synopsis"][0]
            result["plot"] = movie["synopsis"][0]
        elif plot_present:
            result["synopsis"] = movie["plot"][0]
            result["plot"] = movie["plot"][0]
        else:
            result["synopsis"] = ""
            result["plot"] = ""

        # Save the new data to cache
        print("trying to save ", imdb_id)
        cache[imdb_id] = result
        self.save_cache(cache)
        return result

    @retry(stop=stop_after_attempt(3), wait=wait_fixed(1))  # Retries up to 3 times with a 1-second wait between tries
    def get_movie_details_with_retry(self, imdb_id):
        return self.get_movie_details(imdb_id)

    def get_movie_details_as_data_frame(self, imdb_ids):
        all_movie_details = {}
        for movie in imdb_ids:
            all_movie_details[movie] = self.get_movie_details_with_retry(movie)
        all_movie_details = [all_movie_details[movie] for movie in imdb_ids if movie in all_movie_details]
        return pd.json_normalize(all_movie_details)

    def break_into_batches(self, input_list, batch_size):
        batches = []
        # Iterate over the input_list in steps of batch_size
        for i in range(0, len(input_list), batch_size):
            # Append a batch to the batches list
            batches.append(input_list[i:i + batch_size])
        return batches

    def get_unscraped_imdb_ids(self, imdb_movie_ids):
        print("Ignoring movies that have already been scraped...")
        # Alternately, try this - https://medium.com/p/ab7da7d3df5f
        imdb_movie_ids_as_integers = [int(imdb_id.replace("tt", "")) for imdb_id in imdb_movie_ids]
        imdb_movie_ids_as_integers_batches = self.break_into_batches(imdb_movie_ids_as_integers, 1000)
        scraped_movies = []
        for imdb_movie_ids_as_integers_batch in imdb_movie_ids_as_integers_batches:
            response = self.SUPABASE_CLIENT.table(self.TABLE_NAME).select("imdb_id").in_("imdb_id", imdb_movie_ids_as_integers_batch).execute()
            scraped_movies.extend(["tt" + str(entry["imdb_id"]) for entry in response.data])
        return list(set(imdb_movie_ids) - set(scraped_movies))

    def get_movies_with_details_in_range(self, start, end):
        imdb_movie_ids = self.get_imdb_ids_for_tmdb_movies_in_range(start, end)
        imdb_movie_ids = self.get_unscraped_imdb_ids(imdb_movie_ids)
        print(f'Number of movies to scrape: { len(imdb_movie_ids)}')

        movie_details_df = self.get_movie_details_as_data_frame(imdb_movie_ids)
        if not movie_details_df.empty:
            movie_details_df.rename(columns={'imdbID': 'imdb_id', 'original air date': 'air_date', 'language codes': 'languages'}, inplace=True)
            movie_details_df['runtimes'] = movie_details_df['runtimes'].apply(lambda x: int(x[0]) if x and len(x) > 0 else None)
        return movie_details_df
    
    def scrape_and_save(self, start, end):
        print('Scraping movies...')
        movie_details_df = self.get_movies_with_details_in_range(start, end)
        if movie_details_df.empty:
            print('No movies to save. Job completed.')

        print('Saving movies...')
        movie_details_list = movie_details_df.to_dict(orient='records')
        movie_details_list_batches = self.break_into_batches(movie_details_list, 1000)
        try:
            for movie_details_list_batch in movie_details_list_batches:
                response = self.SUPABASE_CLIENT.table(self.TABLE_NAME).upsert(movie_details_list_batch).execute()
            print('Saved movies successfully!')
        except Exception as e:
            print('Error while saving movies to supabase!')
            print(e)


start = "2022-01-01"
end = "2023-12-31"
movie_scraper = MovieScraper()
response = movie_scraper.scrape_and_save(start, end)
# print(response)