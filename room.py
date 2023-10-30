import uuid
from typing import Optional
from data_fetcher import MovieStack, Movie

class User:
    users_by_id = {}

    def __init__(self, name: str, room_id: str):
        self.id = str(uuid.uuid4()).replace('-', '')[:16]
        self.name = name
        self.room_id = room_id
        User.users_by_id[self.id] = self

    @classmethod
    def get_user_by_id(cls, user_id: str):
        return cls.users_by_id.get(user_id)

    def vote_for_movie(self, movie_id: str):
        room = Room.get_room_by_id(self.room_id)
        if room:
            room.add_vote(self.id, movie_id)
        else:
            print("Room not found.")

    def get_room(self):
        return Room.get_room_by_id(self.room_id)

    def get_movie_stack(self):
        return self.get_room().movie_stack

class Room:
    rooms_by_id = {}

    def __init__(self):
        self.id = str(uuid.uuid4()).replace('-', '')[:16]
        self.movie_stack = MovieStack()
        self.movie_stack.load_movies("amf.csv")
        Room.rooms_by_id[self.id] = self

    @classmethod
    def create_user(cls, user_name: str, room_id: str) -> Optional[User]:
        if room_id in cls.rooms_by_id:
            return User(user_name, room_id)
        else:
            print("Room not found.")
            return None

    @classmethod
    def create_room(cls):
        return Room()

    @classmethod
    def get_room_by_id(cls, room_id: str):
        return cls.rooms_by_id.get(room_id)

    @classmethod
    def delete_room(cls, room_id: str):
        if room_id in cls.rooms_by_id:
            # Optionally: Handle any additional cleanup needed for the room's resources
            del cls.rooms_by_id[room_id]
            print(f"Room {room_id} and its associated resources have been deleted.")
        else:
            print("Room not found.")

    def add_vote(self, user_id: str, movie_id: str):
        self.movie_stack.update_stack(movie_id)
