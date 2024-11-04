import numpy as np
import csv
from movie_vector_generator import MovieVectorGenerator
from scipy import sparse
from sklearn.metrics.pairwise import cosine_similarity

class UserProfileManager:
    def __init__(self, vector_dim, mvg):
        self.user_profiles = {}
        self.user_votes = {}
        self.MIN_VOTES_TO_UPDATE = 5
        self.vector_dim = vector_dim
        self.dislike_factor = 1/3
        self.mvg = mvg

    def process_vote(self, user_id, movie_id, vote):
        if user_id not in self.user_votes:
            self.user_votes[user_id] = {'processed_movies': [], 'processed_votes': [], 'unprocessed_movies': [], 'unprocessed_votes': []}
        
        self.user_votes[user_id]['unprocessed_movies'].append(movie_id)
        self.user_votes[user_id]['unprocessed_votes'].append(vote)
        
        if len(self.user_votes[user_id]['unprocessed_votes']) >= self.MIN_VOTES_TO_UPDATE:
            self.update_user_profile(user_id)
        
        print(f"Updated votes activity for this user: {self.user_votes[user_id]}")

    def update_user_profile(self, user_id):
        if user_id not in self.user_profiles:
            self.user_profiles[user_id] = np.zeros(self.vector_dim)
        
        votes = self.user_votes[user_id]
        for movie_id, vote in zip(votes['unprocessed_movies'], votes['unprocessed_votes']):
            movie_vector = self.mvg.get_vector_by_id(movie_id)
            if vote == 'like':
                self.user_profiles[user_id] += movie_vector
            elif vote == 'dislike':
                self.user_profiles[user_id] -= (self.dislike_factor * movie_vector)
        
        votes['processed_movies'].extend(votes['unprocessed_movies'])
        votes['processed_votes'].extend(votes['unprocessed_votes'])
        votes['unprocessed_movies'] = []
        votes['unprocessed_votes'] = []
        
        print(f"Updated user profile for the user: {user_id}")

class RoomProfileManager:
    def __init__(self, vector_dim, mvg):
        self.room_profile = np.zeros(vector_dim)
        self.processed_movies = set()
        self.mvg = mvg

    def update_room_profile(self, movie_id, vote):
        if movie_id not in self.processed_movies:
            movie_vector = self.mvg.get_vector_by_id(movie_id)
            if vote == 'like':
                self.room_profile += movie_vector
            elif vote == 'dislike':
                self.room_profile -= movie_vector
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
        self.user_profile_manager.process_vote(user_id, movie_id, vote)
        self.room_profile_manager.update_room_profile(movie_id, vote)

    def seed_user_and_room_profiles(self, user_ids):
        user_queues = {}
        for user_id in user_ids:
            random_movies = self.mvg.get_random_movies(self.user_profile_manager.MIN_VOTES_TO_UPDATE)
            user_queues[user_id] = [movie[0] for movie in random_movies]  # Assuming movie[0] is the movie ID
        
        return user_queues

    def get_updated_user_queues(self, num_recommendations):
        num_users = len(self.user_profile_manager.user_profiles)
        total_movies_shown = len(self.room_profile_manager.processed_movies)
        movie_fetch_size = total_movies_shown + num_recommendations * num_users

        # Step 1: Get room recommendations
        room_recommendations = self.recommendation_engine.get_recommendations(
            self.room_profile_manager.room_profile, movie_fetch_size, self.room_profile_manager.processed_movies
        )

        # Step 2: Order recommendations
        movie_titles = [rec[0] for rec in room_recommendations]
        movie_vectors = [self.mvg.get_vector_by_id(movie_id) for movie_id in movie_titles]
        
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
        for user_column, user_id in enumerate(user_ids):
            movie_ids_shown_to_user = self.user_profile_manager.user_votes[user_id]["processed_movies"]
            movie_availability = np.array([0 if movie in movie_ids_shown_to_user else 1 for movie in movie_titles])
            mask[:, user_column] = movie_availability

        while np.any(mask == 1):
            masked_array = np.where(mask, similarity_scores, -np.inf)
            max_index = np.unravel_index(np.argmax(masked_array), masked_array.shape)
            user_queues[user_ids[max_index[1]]].append(movie_titles[max_index[0]])

            mask[max_index[0], :] = 0

            if len(user_queues[user_ids[max_index[1]]]) >= num_recommendations:
                mask[:, max_index[1]] = 0

        # Step 4: Handle full queues
        total_scores = np.sum(similarity_scores, axis=1)
        top_indices = np.argsort(total_scores)[-5:][::-1]
        top_movies_in_the_room = [movie_titles[i] for i in top_indices]

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

# def read_user_votes(self, filename):
#         user_votes = []
#         try:
#             with open(filename, newline='', encoding='utf-8') as csvfile:
#                 reader = csv.DictReader(csvfile)
#                 for row in reader:
#                     user_votes.append({'UserId': row['UserId'].strip(), 'Movie': row['Movie'].strip(), 'Vote': row['Vote'].strip()})
#         except FileNotFoundError:
#             print(f"The file {filename} was not found.")
#         except Exception as e:
#             print(f"An error occurred: {e}")
#         return user_votes


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