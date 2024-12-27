from movie_fetcher import MovieFetcher
import random
import uuid
from typing import Dict, List, Optional
from enhanced_room_utils import EnhancedRoomUtils
from movie_vector_generator import MovieVectorGenerator
import pandas as pd
from constants import VoteStatus, SEED_VOTES_REQUIRED
from room_config import RoomConfig

class EnhancedRoom:
    rooms_by_id = {}

    def __init__(self):
        self.id = str(uuid.uuid4()).replace('-', '')[:16]
        
        # Initialize room config
        self.config = RoomConfig(years=[2024])  # Default config
        
        # Initialize components
        self.mvg = MovieVectorGenerator(config=self.config)
        self.room_utils = EnhancedRoomUtils(self.mvg)
        
        # TODO: Instead of getting all movies, only get the ones returned by the recommendation engine. 
        # The other option is to just make sure all the required data is in the vector db.
        movie_fetcher = MovieFetcher()
        self.movies_df = movie_fetcher.get_movies()
        
        # Track users and their votes
        self.users = {}  # user_id -> user_name
        self.seeding_phase = True
        self.movie_queues = {}  # user_id -> list of movie_ids to vote on
        self.voting_started = False  # New field to track if voting has started
        
        EnhancedRoom.rooms_by_id[self.id] = self

    def add_user(self, user_name: str) -> str:
        """Add a user to the room and return their ID"""
        if len(self.users) >= 2:
            raise ValueError("Room is full")

        user_id = str(uuid.uuid4()).replace('-', '')[:16]
        self.users[user_id] = {
            "name": user_name,
            "votes": {}
        }

        self._initialize_voting_queues([user_id])

        return user_id

    def _initialize_voting_queues(self, userids: List[str]):
        user_queues = self.room_utils.seed_user_and_room_profiles(userids)
        for user_id in userids:
            self.movie_queues[user_id] = user_queues[user_id]

    def refill_queue(self, user_id: str) -> None:
        """Refill the movie queue for a user"""
        print(f'Refilling queue for user {user_id}...')
        if user_id not in self.users:
            raise ValueError("User not found")

        if self.room_utils.get_user_vote_status(user_id) == VoteStatus.SEEDING:
            print(f'Seeding incomplete, randomly selecting queue for user {user_id}')
            self._initialize_voting_queues([user_id])
        else:
            recommendations = self.get_recommendations()
            if recommendations["status"] == "error":
                raise ValueError(recommendations["message"])
            self.movie_queues[user_id].extend(recommendations["queues"][user_id])

    def get_movie_to_vote(self, user_id: str) -> Optional[dict]:
        """Get next movie for user to vote on"""
        if user_id not in self.users:
            raise ValueError("User not found")

        if not self.movie_queues[user_id]:
            self.refill_queue(user_id)
        
        if not self.movie_queues[user_id]:
            raise ValueError("No more movies available for this user")
            
        movie_id = self.movie_queues[user_id].pop(0)  # Get and remove first movie from queue
        movie_details = self.movies_df[self.movies_df['imdbID'] == movie_id].iloc[0]
        
        return {
            "movie_id": movie_id,
            "title": movie_details['title'],
            "year": movie_details['year']
        }

    def submit_vote(self, user_id: str, movie_id: str, vote: str) -> VoteStatus:
        """Submit a vote for a movie and return the current voting status"""
        if user_id not in self.users:
            raise ValueError("User not found")

        self.users[user_id]["votes"][movie_id] = vote
        return self.room_utils.accept_user_vote((user_id, movie_id, vote))

    def get_recommendations(self) -> dict:
        """Get recommendations after seeding is complete"""
        # breaking here
        if not all(self.room_utils.get_user_vote_status(user) == VoteStatus.SEEDING_COMPLETE for user in self.users.keys()):
            raise ValueError("Seeding not complete")

        # Get recommendations using EnhancedRoomUtils
        print(f'Getting recommendations...')
        try:
            user_queues, top_movies_in_the_room = self.room_utils.get_updated_user_queues(10)  # Get 10 recommendations per user
        except Exception as e:
            print(f'Error getting recommendations: {e}')
            return {
                "status": "error",
                "message": str(e)
            }

        id_to_title_dict = {movie_id: self.movies_df.loc[self.movies_df['imdbID'] == movie_id, 'title'].values[0]
                    for movie_id in top_movies_in_the_room}

        return {
            "status": "complete",
            "queues": user_queues,
            "top_movies": top_movies_in_the_room,
            "movie_titles": id_to_title_dict
        }

    def update_config(self, years: List[int], genres: Optional[List[str]] = None):
        """Update room configuration and refresh movie data"""
        print(f"Updating room config to years={years}, genres={genres}")
        self.config = RoomConfig(years=years, genres=genres)
        
        # Update MovieVectorGenerator with new config
        self.mvg = MovieVectorGenerator(config=self.config)
        self.room_utils = EnhancedRoomUtils(self.mvg)
        
        # Reset movie queues since we have new data
        self.movie_queues = {}
        for user_id in self.users:
            self._initialize_voting_queues([user_id])

    def get_room_status(self) -> dict:
        """Get current room status including users and configuration"""
        users_list = [
            {"id": user_id, "name": user_data["name"]} 
            for user_id, user_data in self.users.items()
        ]
        
        return {
            "roomId": self.id,
            "users": users_list,
            "config": {
                "years": self.config.years,
                "genres": self.config.genres
            },
            "votingStarted": self.voting_started
        }

    def start_voting(self) -> None:
        """Start the voting phase for this room"""
        self.voting_started = True

    @classmethod
    def get_room_by_id(cls, room_id: str) -> Optional['EnhancedRoom']:
        return cls.rooms_by_id.get(room_id) 