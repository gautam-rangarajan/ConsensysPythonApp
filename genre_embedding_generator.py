import gensim.downloader as api
from sklearn.decomposition import PCA
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
import warnings

class GenreEmbeddingGenerator:
    def __init__(self, model_name='word2vec-google-news-300', pca_components=10):
        print("Initializing GenreEmbeddingGenerator")
        self.model = api.load(model_name)
        self.pca = PCA(n_components=pca_components)
        self.movie_embeddings = {}
        self.genre_cache = {}  # Cache for individual genre embeddings
        
        # Pre-configured genre mappings
        self.genre_mappings = {
            'Sci-Fi': 'scifi'
            # Add more mappings as needed
        }
        print("Done initializing GenreEmbeddingGenerator!")

    def get_embedding(self, word):
        # Apply genre mapping if exists
        word = self.genre_mappings.get(word, word)
        
        if word in self.genre_cache:
            return self.genre_cache[word]
        try:
            embedding = np.array(self.model[word])
            self.genre_cache[word] = embedding  # Cache the embedding
            return embedding
        except KeyError:
            warnings.warn(f"Unidentified genre: '{word}'. Using zero embedding.", UserWarning)
            zero_embedding = np.zeros(self.model.vector_size)
            self.genre_cache[word] = zero_embedding  # Cache the zero embedding
            return zero_embedding

    def aggregate_embeddings(self, tags):
        embeddings = [self.get_embedding(tag) for tag in tags]
        return np.mean(embeddings, axis=0)

    def generate_embeddings(self, movie_details_df):
        all_embeddings = []
        for _, row in movie_details_df.iterrows():
            movie_id = row['imdbID']
            genres = row['genres']
            if genres:
                embedding = self.aggregate_embeddings(genres)
                all_embeddings.append(embedding)
                self.movie_embeddings[movie_id] = embedding
            else:
                self.movie_embeddings[movie_id] = np.zeros(self.model.vector_size)

        # Apply PCA to all embeddings
        reduced_embeddings = self.pca.fit_transform(np.array(all_embeddings))
        
        # Update movie_embeddings with reduced embeddings
        for i, (movie_id, _) in enumerate(self.movie_embeddings.items()):
            self.movie_embeddings[movie_id] = reduced_embeddings[i]

    def get_all_embeddings(self):
        return self.movie_embeddings

    def get_embedding_by_movie_id(self, movie_id):
        return self.movie_embeddings.get(movie_id, None)

    def search_movies(self, query, top_n=10):
        query_embedding = self.aggregate_embeddings(query)
        query_embedding_reshaped = query_embedding.reshape(1, -1)
        reduced_query_embedding = self.pca.transform(query_embedding_reshaped)

        similarities = cosine_similarity(reduced_query_embedding, list(self.movie_embeddings.values()))
        sorted_indices = np.argsort(-similarities[0])

        return [(list(self.movie_embeddings.keys())[i], similarities[0][i]) 
                for i in sorted_indices[:top_n]]

    def clear_cache(self):
        self.genre_cache.clear()


# # Generate embeddings for all movies
# generator.generate_embeddings(movie_details_df)

# # Get all embeddings
# all_embeddings = generator.get_all_embeddings()

# # Get embedding for a specific movie
# movie_embedding = generator.get_embedding_by_movie_id(23561236)
# print(movie_embedding)

# # Search for similar movies
# similar_movies = generator.search_movies([
#   "Action",
#   "Adventure",
#   "Drama",
#   "Family",
#   "Fantasy"
# ], top_n=10)
# print(similar_movies)