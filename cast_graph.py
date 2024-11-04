import networkx as nx
import pandas as pd
import numpy as np
from movie_fetcher import MovieFetcher
from node2vec import Node2Vec
from tqdm.notebook import tqdm
from sklearn.metrics.pairwise import cosine_similarity
import pickle
from imdb import Cinemagoer
import concurrent.futures
from functools import partial

class CastGraph:
    def __init__(self, recompute_all=False):
        self.graph = nx.Graph()
        self.movie_scraper = MovieFetcher()
        self.embeddings = {}
        self.recompute_all = recompute_all
        self.embeddings_generated = False  # New flag to track if embeddings exist

    def fetch_movies(self, years):
        """Fetch movies for the given years."""
        return self.movie_scraper.get_movies_from_years(years)

    def get_person_name(self, imdb_id):
        try:
            ia = Cinemagoer()
            person = ia.get_person(imdb_id)
            return imdb_id, person['name']
        except Exception as e:
            print(f"Error fetching name for {imdb_id}: {e}")
            return imdb_id, f"Unknown (ID: {imdb_id})"

    def build_graph(self, movies_df):
        """Build the graph from a DataFrame of movies."""
        for _, movie in movies_df.iterrows():
            self._add_movie_to_graph(movie)

    def _add_movie_to_graph(self, movie):
        """Add a single movie to the graph. Return True if graph changed, False otherwise."""
        cast = movie['cast']
        directors = movie['director']
        graph_changed = False

        for actor in cast:
            if not self.graph.has_node(actor):
                self.graph.add_node(actor)
                graph_changed = True
            for co_actor in cast:
                if actor != co_actor and not self.graph.has_edge(actor, co_actor):
                    self.graph.add_edge(actor, co_actor)
                    graph_changed = True

        for director in directors:
            if not self.graph.has_node(director):
                self.graph.add_node(director)
                graph_changed = True
            for actor in cast:
                if not self.graph.has_edge(director, actor):
                    self.graph.add_edge(director, actor)
                    graph_changed = True

        return graph_changed

    def generate_embeddings(self):
        """Generate embeddings for the graph if they don't exist."""
        if not self.embeddings_generated:
            node2vec = Node2Vec(self.graph, dimensions=64, walk_length=30, num_walks=200, workers=1)
            model = node2vec.fit(window=10, min_count=1)
            self.embeddings = {node: model.wv[node] for node in self.graph.nodes()}
            self.embeddings_generated = True
        else:
            print("Embeddings already exist. Skipping generation.")

    def save_graph_and_embeddings(self, filename):
        """Save the graph and embeddings to a file."""
        data = {
            'graph': self.graph,
            'embeddings': self.embeddings
        }
        with open(filename, 'wb') as f:
            pickle.dump(data, f)

    def load_graph_and_embeddings(self, filename):
        """Load the graph and embeddings from a file."""
        if self.recompute_all:
            print("Recompute flag is set. Skipping load operation.")
            return

        try:
            with open(filename, 'rb') as f:
                data = pickle.load(f)
            self.graph = data['graph']
            self.embeddings = data['embeddings']
            self.embeddings_generated = True  # Set flag when loading embeddings
            print("Graph and embeddings loaded successfully.")
        except FileNotFoundError:
            print("No saved data found. Starting with an empty graph.")

    def update_with_new_movies(self, new_movies_df, hops=2, regenerate_all_embeddings=False):
        """
        Update the graph and embeddings with new movies.
        
        :param regenerate_all_embeddings: If True, regenerate embeddings for all nodes after updating the graph.
        """
        graph_changed = False
        for _, movie in new_movies_df.iterrows():
            if self._add_movie_to_graph(movie):
                graph_changed = True
                self.embeddings_generated = False

        if graph_changed or regenerate_all_embeddings:
            if regenerate_all_embeddings:
                print("Regenerating embeddings for all nodes...")
                self.generate_embeddings()
            else:
                all_affected_nodes = set()
                for _, movie in new_movies_df.iterrows():
                    affected_nodes = self._get_affected_nodes(movie, hops)
                    all_affected_nodes.update(affected_nodes)

                if all_affected_nodes:
                    new_embeddings = self._generate_subgraph_embeddings(all_affected_nodes)

                    for node in all_affected_nodes:
                        self.embeddings[node] = new_embeddings[node]
                else:
                    print("No nodes affected. Skipping embedding update.")
        else:
            print("No changes to the graph. Skipping update process.")
        self.embeddings_generated = True

    def _get_affected_nodes(self, movie, hops=2):
        """Get affected nodes for a movie within specified hops."""
        affected_nodes = set(movie['cast'] + movie['director'])
        nodes_to_check = list(affected_nodes)

        for _ in range(hops):
            new_neighbors = set()
            for node in nodes_to_check:
                neighbors = set(self.graph.neighbors(node))
                new_neighbors.update(neighbors)
            affected_nodes.update(new_neighbors)
            nodes_to_check = list(new_neighbors)

        return affected_nodes

    def _generate_subgraph_embeddings(self, all_affected_nodes):
        """Generate embeddings for a subgraph."""
        node2vec = Node2Vec(self.graph, dimensions=64, walk_length=30, num_walks=200, workers=1)
        model = node2vec.fit(window=10, min_count=1)
        return {node: model.wv[node] for node in all_affected_nodes}

    def find_similar_actors(self, actor_id, top_n=10):
        """Find the most similar actors/directors to the given actor."""
        if not self.embeddings_generated:
            self.generate_embeddings()
        if actor_id not in self.embeddings:
            raise ValueError(f"Actor/Director '{actor_id}' not found in current embeddings.")

        target_embedding = self.embeddings[actor_id].reshape(1, -1)
        all_embeddings = np.array([self.embeddings[name] for name in self.embeddings if name != actor_id])
        all_names = [name for name in self.embeddings if name != actor_id]

        similarities = cosine_similarity(target_embedding, all_embeddings)[0]
        
        top_indices = similarities.argsort()[-top_n:][::-1]
        return [(all_names[i], similarities[i]) for i in top_indices]

    def get_graph_stats(self):
        """Get basic statistics about the graph."""
        return {
            "nodes": self.graph.number_of_nodes(),
            "edges": self.graph.number_of_edges()
        }

    def get_person_names_batch(self, actor_ids, max_workers=10):
        """Fetch names for a batch of actor IDs in parallel."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            results = list(tqdm(
                executor.map(self.get_person_name, actor_ids),
                total=len(actor_ids),
                desc="Fetching names"
            ))
        return dict(results)



# Initialize the CastGraph
# cast_graph = CastGraph(recompute_all=False)
# cast_graph.load_graph_and_embeddings('cast_graph_data.pkl')

# print("Initial graph stats:", cast_graph.get_graph_stats())

# # 1. Create a graph with an initial set of movies
# # Let's fetch movies from 2022
# initial_movies = cast_graph.fetch_movies([2022])
# cast_graph.build_graph(initial_movies)
# cast_graph.generate_embeddings()

# print("Initial graph stats:", cast_graph.get_graph_stats())

# 2. Get recommendations for a specific actor
# target_actor_id = "0262635"
# similar_actors = cast_graph.find_similar_actors(target_actor_id, top_n=10)

# # Fetch names in batch
# actor_ids = [target_actor_id] + [actor for actor, _ in similar_actors]
# names = cast_graph.get_person_names_batch(actor_ids)

# target_actor_name = names[target_actor_id]
# print(f"\nTop 10 similar actors to {target_actor_name} (ID: {target_actor_id}):")
# for actor_id, similarity in similar_actors:
#     actor_name = names[actor_id]
#     print(f"{actor_name} (ID: {actor_id}): {similarity:.4f}")

# # 3. Update the graph with new movies
# # Let's fetch movies from 2023
# new_movies = cast_graph.fetch_movies([2023])
# cast_graph.update_with_new_movies(new_movies, regenerate_all_embeddings=False)  # Set to True to regenerate all embeddings

# print("\nUpdated graph stats:", cast_graph.get_graph_stats())

# # 4. Get new recommendations
# updated_similar_actors = cast_graph.find_similar_actors(target_actor_id, top_n=10)

# # Fetch updated names in batch
# updated_actor_ids = [target_actor_id] + [actor for actor, _ in updated_similar_actors]
# updated_names = cast_graph.get_person_names_batch(updated_actor_ids)

# print(f"\nUpdated top 10 similar actors to {target_actor_name} (after adding 2023 movies):")
# for actor_id, similarity in updated_similar_actors:
#     actor_name = updated_names[actor_id]
#     print(f"{actor_name} (ID: {actor_id}): {similarity:.4f}")

# # Save the updated graph and embeddings
# cast_graph.save_graph_and_embeddings('cast_graph_data.pkl')