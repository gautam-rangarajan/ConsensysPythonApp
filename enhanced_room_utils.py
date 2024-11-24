import numpy as np
import csv
from movie_vector_generator import MovieVectorGenerator
from scipy import sparse
from sklearn.metrics.pairwise import cosine_similarity
from constants import MIN_VOTES_TO_UPDATE, DISLIKE_FACTOR, VoteStatus, SEED_VOTES_REQUIRED

class UserProfileManager:
    def __init__(self, vector_dim, mvg):
        self.user_profiles = {}
        self.user_votes = {}
        self.vector_dim = vector_dim
        self.mvg = mvg

    def add_user(self, user_id):
        if user_id not in self.user_votes:
            self.user_votes[user_id] = {'processed_movies': [], 'processed_votes': [], 'unprocessed_movies': [], 'unprocessed_votes': [], 'unseen_movies': [], 'status': VoteStatus.SEEDING}

    def process_vote(self, user_id, movie_id, vote):
        if user_id not in self.user_votes:
            raise ValueError("User not found")
        
        self.user_votes[user_id]['unprocessed_movies'].append(movie_id)
        self.user_votes[user_id]['unprocessed_votes'].append(vote)
        
        if len(self.user_votes[user_id]['unprocessed_votes']) >= MIN_VOTES_TO_UPDATE:
            self.update_user_profile(user_id)

        if len(set(self.user_votes[user_id]['processed_movies'])) - len(set(self.user_votes[user_id]['unseen_movies'])) >= SEED_VOTES_REQUIRED:
            self.user_votes[user_id]['status'] = VoteStatus.USER_SEEDING_COMPLETE
        
        print(f"Updated votes activity for this user: {self.user_votes[user_id]}")

        # Check if all users have completed seeding
        all_users_complete = all(
            user_votes['status'] == VoteStatus.USER_SEEDING_COMPLETE 
            for user_votes in self.user_votes.values()
        )

        # If all users are complete, update everyone's status to seeding complete
        if all_users_complete:
            for user_votes in self.user_votes.values():
                user_votes['status'] = VoteStatus.SEEDING_COMPLETE
            return VoteStatus.SEEDING_COMPLETE

        # Otherwise return current user's status
        return self.user_votes[user_id]['status']

    def update_user_profile(self, user_id):
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = np.zeros(self.vector_dim)
        
        votes = self.user_votes[user_id]
        for movie_id, vote in zip(votes['unprocessed_movies'], votes['unprocessed_votes']):
            movie_vector = self.mvg.get_vector_by_id(movie_id)
            if vote == 'like':
                self.user_profiles[user_id] += movie_vector
            elif vote == 'dislike':
                self.user_profiles[user_id] -= (DISLIKE_FACTOR * movie_vector)
            elif vote == 'not seen':
                votes['unseen_movies'].append(movie_id)
                continue
        
        votes['processed_movies'].extend(votes['unprocessed_movies'])
        votes['processed_votes'].extend(votes['unprocessed_votes'])
        votes['unprocessed_movies'] = []
        votes['unprocessed_votes'] = []
        
        print(f"Updated user profile for the user: {user_id}")

class RoomProfileManager:
    def __init__(self, vector_dim, mvg):
        self.room_profile = np.zeros(vector_dim)
        self.processed_movies = set()
        self.unseen_movies = set()
        self.mvg = mvg

    def update_room_profile(self, movie_id, vote):
        if movie_id not in self.processed_movies:
            movie_vector = self.mvg.get_vector_by_id(movie_id)
            if vote == 'like':
                self.room_profile += movie_vector
            elif vote == 'dislike':
                self.room_profile -= movie_vector
            elif vote == 'not seen':
                self.unseen_movies.add(movie_id)
                pass
            self.processed_movies.add(movie_id)
            print("Updated room profile")
        print(f"Set size: {len(self.processed_movies)}")

class RecommendationEngine:
    def __init__(self, mvg):
        self.mvg = mvg

    def get_recommendations(self, profile_vector, num_recommendations, exclude_movie_ids=None):
        extra_recommendations = len(exclude_movie_ids) if exclude_movie_ids else 0
        all_recommendations = self.mvg.find_similar_vectors(profile_vector, num_recommendations + extra_recommendations)
        if exclude_movie_ids:
            filtered_recommendations = [rec for rec in all_recommendations if rec[0] not in exclude_movie_ids]
            filtered_recommendations = filtered_recommendations[:num_recommendations]
        else:
            filtered_recommendations = all_recommendations
        return filtered_recommendations

class EnhancedRoomUtils:
    def __init__(self, movie_vector_generator):
        self.mvg = movie_vector_generator
        vector_dim = self.mvg.embedding_length
        self.user_profile_manager = UserProfileManager(vector_dim, self.mvg)
        self.room_profile_manager = RoomProfileManager(vector_dim, self.mvg)
        self.recommendation_engine = RecommendationEngine(self.mvg)

    def accept_user_vote(self, user_vote):
        user_id, movie_id, vote = user_vote
        status = self.user_profile_manager.process_vote(user_id, movie_id, vote)
        self.room_profile_manager.update_room_profile(movie_id, vote)
        return status
    
    def get_user_vote_status(self, user_id: str) -> VoteStatus:
        """Get the current vote status for a user"""
        if user_id not in self.user_profile_manager.user_votes.keys():
            raise ValueError("User not found")
        return self.user_profile_manager.user_votes[user_id]['status']
    
    def seed_user_and_room_profiles(self, user_ids):
        user_queues = {}
        for user_id in user_ids:
            self.user_profile_manager.add_user(user_id)
            random_movies = self.mvg.get_random_movies(MIN_VOTES_TO_UPDATE)
            user_queues[user_id] = [movie[0] for movie in random_movies]  # Assuming movie[0] is the movie ID
        
        return user_queues

    def exclude_movies_from_recommendations(self):
        # TODO: We need to be more inteligent about what movies to exclude from recommendations.
        # For now, we'll just exclude all the movies that have been shown to ANY user.
        # We may need to take room settings into account. Examples:
        # - If the room is set to only show new movies, we should exclude all the movies that have been shown to ANY user.
        # - If the room is set to okay to rewatch, we should exclude movies that the users have disliked.
        # Then we need to make sure these movies are allocated properly. The current logic in get_updated_user_queues assumes
        # every movie has a similarity score for every user, which will not be the case if we start returning movies that some users
        # have seen but others havent. We need to modify get_updated_user_queues to handle this.
        # return self.room_profile_manager.processed_movies - self.room_profile_manager.unseen_movies
        return self.room_profile_manager.processed_movies
    
    def get_updated_user_queues(self, num_recommendations):
        num_users = len(self.user_profile_manager.user_profiles)
        total_movies_shown = len(self.room_profile_manager.processed_movies)
        movie_fetch_size = num_recommendations * num_users

        # Step 1: Get room recommendations
        exclude_movie_ids = self.exclude_movies_from_recommendations()
        print(exclude_movie_ids)
        room_recommendations = self.recommendation_engine.get_recommendations(
            self.room_profile_manager.room_profile, movie_fetch_size, exclude_movie_ids
        )

        # Step 2: Order recommendations
        movie_ids = [rec[0] for rec in room_recommendations]
        movie_vectors = [self.mvg.get_vector_by_id(movie_id) for movie_id in movie_ids]
        
        # Ensure each vector is 2-D
        movie_vectors = [vector.reshape(1, -1) if vector.ndim == 1 else vector for vector in movie_vectors]        
        movie_vectors_sparse = sparse.vstack([sparse.csr_matrix(v) for v in movie_vectors])

        user_ids = list(self.user_profile_manager.user_profiles.keys())
        user_profiles_matrix = sparse.vstack([sparse.csr_matrix(self.user_profile_manager.user_profiles[user_id].reshape(1, -1)) for user_id in user_ids])

        print(movie_vectors_sparse.shape, user_profiles_matrix.shape)
        similarity_scores = cosine_similarity(movie_vectors_sparse, user_profiles_matrix)
        
        user_queues = {user_id: [] for user_id in user_ids}
        mask = np.ones_like(similarity_scores)

        # Step 3: Allocate to users
        for user_column, user_id in enumerate(user_ids):  # We don't expect this to change anything since we're only selecting movies that have NOT been shown to the user
            movie_ids_shown_to_user = self.user_profile_manager.user_votes[user_id]["processed_movies"]
            movie_availability = np.array([0 if movie in movie_ids_shown_to_user else 1 for movie in movie_ids])
            mask[:, user_column] = movie_availability

        while np.any(mask == 1):
            masked_array = np.where(mask, similarity_scores, -np.inf)
            max_index = np.unravel_index(np.argmax(masked_array), masked_array.shape)
            user_queues[user_ids[max_index[1]]].append(movie_ids[max_index[0]])

            mask[max_index[0], :] = 0

            if len(user_queues[user_ids[max_index[1]]]) >= num_recommendations:
                mask[:, max_index[1]] = 0

        # Step 4: Get recommendations for the room in the order of total similarity score (sum of all users)
        total_scores = np.sum(similarity_scores, axis=1)
        top_indices = np.argsort(total_scores)[-movie_fetch_size:][::-1]
        top_movies_in_the_room = [movie_ids[i] for i in top_indices]

        return user_queues, top_movies_in_the_room

    def read_user_votes(self, file_path, title_to_id_dict):
        user_votes = []
        with open(file_path, 'r') as csvfile:
            csvreader = csv.reader(csvfile)
            next(csvreader)  # Skip header row
            for row in csvreader:
                user_id, movie_id, vote = row
                if movie_id in title_to_id_dict:
                    movie_id = title_to_id_dict[movie_id]
                user_votes.append((int(user_id), int(movie_id), vote))
        return user_votes

def get_top_movies_cosine(matrix, vector, titles, n, shouldPrint=False):
    similarities = cosine_similarity(vector, matrix)[0]
    top_indices = similarities.argsort()[-n:][::-1]
    top_movies = [(titles[i], i, similarities[i]) for i in top_indices]

    if shouldPrint:
        print("Top similar movies to the provided movie vector:\n")
        for movie, row, score in top_movies:
            print(f'"{movie}" at ROW {row} with similarity score: {score}')
        print()

    return top_movies