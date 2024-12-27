import pandas as pd
from supabase import create_client, Client
from room_config import RoomConfig


# Fetch movies that have already been scraped
class MovieFetcher:
    SUPABASE_CLIENT: Client = None
    TABLE_NAME = "movies_raw_data"

    def __init__(self):
        url = "https://qamoyltkfqipmyolhfat.supabase.co"
        key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6InFhbW95bHRrZnFpcG15b2xoZmF0Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTcxNDEwMjA2MCwiZXhwIjoyMDI5Njc4MDYwfQ.sNrXGQLpZEKcV0kBZ7tv669Yj8YDxKFBRN00VKNHMqA"
        self.SUPABASE_CLIENT = create_client(url, key)

    def get_movies(self, config: RoomConfig = None, limit=100):
        print(f'Fetching movies{" from years " + str(config.years) if config and config.years else ""}...')

        offset = 0
        got_all_movies = False
        movie_details_list = []

        while not got_all_movies:
            print(f'Fetched {len(movie_details_list)} movies so far. Still fetching...')
            query = self.SUPABASE_CLIENT.table(self.TABLE_NAME).select("*")
            
            if config and config.years:  # Check if config exists and has years specified
                query = query.in_("year", config.years)
            
            response = query.range(offset, offset + limit - 1).execute()

            if len(response.data) == 0:
                got_all_movies = True
                print(f'Fetch complete! Got {len(movie_details_list)} movies.')
            else:
                movie_details_list.extend(response.data)
                offset += limit

        movie_details_df = pd.DataFrame(movie_details_list)
        movie_details_df.rename(
            columns={'imdb_id': 'imdbID', 'air_date': 'original air date', 'languages': 'language codes'}, inplace=True)
        return movie_details_df

# movie_scraper = MovieFetcher()
# movie_details_df = movie_scraper.get_movies_from_years([2023])
#
#
# titles_with_synopsis = movie_details_df['title'].tolist()
# imdb_ids_with_synopsis = movie_details_df['imdbID'].tolist()
# synopsis_list = movie_details_df['synopsis'].tolist()

