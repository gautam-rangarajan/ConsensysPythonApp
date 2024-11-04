import psycopg2
import numpy as np
import random

class MovieVectorGenerator:
    def __init__(self, embedding_length=None, db_name="pgvector_demo", db_user="gautam", db_password=""):
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.vector_table_name = "movie_vectors"
        if embedding_length is None:
            self.embedding_length = self.fetch_embedding_length()
        else:
            self.embedding_length = embedding_length
        print(f"Embedding length: {self.embedding_length}")

    def fetch_embedding_length(self):
        conn = self.connect_to_db()
        cur = conn.cursor()
        try:
            cur.execute(f"SELECT vector FROM {self.vector_table_name} LIMIT 1")
            result = cur.fetchone()
            if result:
                 # Remove square brackets and split by comma
                vector_values = result[0].strip('[]').split(',')
                # Convert to float and create numpy array
                vector = np.array([float(x.strip()) for x in vector_values])
                return vector.shape[0]  # Assuming the vector is stored as a list
            else:
                raise ValueError("No vectors found in the database.")
        finally:
            cur.close()
            conn.close()

    def connect_to_db(self):
        return psycopg2.connect(f"dbname={self.db_name} user={self.db_user} password={self.db_password}")

    def insert_vector(self, cur, id, embedding, movie_title):
        cur.execute(f"INSERT INTO {self.vector_table_name} (id, vector, movie_title) VALUES (%s, %s::vector, %s)", 
                    (id, embedding.tolist(), movie_title))

    def insert_vectors(self, vectors_data, cur=None):
        if cur is None:
            conn = self.connect_to_db()
            cur = conn.cursor()
            should_close = True
        else:
            should_close = False

        print(f"Inserting vectors with length {self.embedding_length}")
        for id, vector, movie_title in vectors_data:
            self.insert_vector(cur, id, vector, movie_title)
        print(f"Done inserting vectors.")

        if should_close:
            conn.commit()
            cur.close()
            conn.close()

    def find_similar_vectors(self, query_vector, num_recommendations):
        conn = self.connect_to_db()
        cur = conn.cursor()

        results = self._find_similar_vectors(cur, query_vector, num_recommendations)

        cur.close()
        conn.close()

        return results

    def _find_similar_vectors(self, cur, query, num_recommendations):
        query_list = query.tolist()
        cur.execute(f"""
            SELECT id, vector, movie_title,
                    1 - (vector <=> %s::vector) as similarity
            FROM {self.vector_table_name}
            ORDER BY similarity DESC
            LIMIT %s
        """, (query_list, num_recommendations))
        return cur.fetchall()

    def get_updated_embeddings(self, cur, new_dimension):
        try:
            cur.execute(f"SELECT id, vector, movie_title FROM {self.vector_table_name}")
            existing_data = cur.fetchall()
            
            new_embeddings = []
            for id, vector, movie_title in existing_data:
                vector = np.array(vector.strip('[]').split(','), dtype=float)
                current_length = len(vector)
                if new_dimension > current_length:
                    new_vector = np.pad(vector, (0, new_dimension - current_length))
                else:
                    new_vector = vector[:new_dimension]
                new_embeddings.append((id, new_vector, movie_title))
            
            print(f"Created {len(new_embeddings)} new embeddings with dimension {new_dimension}")
            return new_embeddings
        except Exception as e:
            print(f"Error changing vector dimension: {e}")
            return None

    def change_vector_dimension(self, new_dimension):
        conn = self.connect_to_db()
        cur = conn.cursor()

        try:
            new_embeddings = self.get_updated_embeddings(cur, new_dimension)
            
            if new_embeddings:
                self.embedding_length = new_dimension
                self.reset_table(cur)
                self.insert_vectors(new_embeddings, cur)
                print(f"Updated {self.vector_table_name} with new embeddings")

            conn.commit()
        finally:
            cur.close()
            conn.close()

    def reset_table(self, cur=None):
        if cur is None:
            conn = self.connect_to_db()
            cur = conn.cursor()
            should_close = True
        else:
            should_close = False

        cur.execute(f"DROP TABLE IF EXISTS {self.vector_table_name}")
        cur.execute("CREATE EXTENSION IF NOT EXISTS vector")
        cur.execute(f"""
        CREATE TABLE {self.vector_table_name} (
            id INTEGER PRIMARY KEY,
            vector vector({self.embedding_length}),
            movie_title TEXT
        )
        """)

        if should_close:
            conn.commit()
            cur.close()
            conn.close()

    def get_vector_by_id(self, movie_id):
        conn = self.connect_to_db()
        cur = conn.cursor()

        try:
            cur.execute(f"""
                SELECT vector
                FROM {self.vector_table_name}
                WHERE id = %s
            """, (movie_id,))
            result = cur.fetchone()

            if result:
                vector_str = result[0]
                # Remove square brackets and split by comma
                vector_values = vector_str.strip('[]').split(',')
                # Convert to float and create numpy array
                return np.array([float(x.strip()) for x in vector_values])
            else:
                print(f"No vector found for movie ID {movie_id}")
                return None
        except Exception as e:
            print(f"Error retrieving vector: {e}")
            return None
        finally:
            cur.close()
            conn.close()

    def get_random_movies(self, num_movies):
        conn = self.connect_to_db()
        cur = conn.cursor()

        try:
            cur.execute(f"""
                SELECT id, movie_title
                FROM {self.vector_table_name}
                ORDER BY RANDOM()
                LIMIT %s
            """, (num_movies,))
            return cur.fetchall()
        except Exception as e:
            print(f"Error retrieving random movies: {e}")
            return []
        finally:
            cur.close()
            conn.close()

# Example usage
if __name__ == "__main__":
    initial_embedding_length = 384
    new_embedding_length = 512

    # Generate sample data (in a real scenario, this would be your actual data)
    sample_data = [
        (1, np.random.rand(initial_embedding_length), "The Shawshank Redemption"),
        (2, np.random.rand(initial_embedding_length), "The Godfather"),
        (3, np.random.rand(initial_embedding_length), "The Dark Knight"),
        (4, np.random.rand(initial_embedding_length), "Pulp Fiction"),
        (5, np.random.rand(initial_embedding_length), "Forrest Gump"),
    ]

    mvg = MovieVectorGenerator(initial_embedding_length)
    
    # Explicitly reset the table before inserting vectors
    mvg.reset_table()
    mvg.insert_vectors(sample_data)

    # Find similar vectors
    # query_vector = np.random.rand(initial_embedding_length)  # Example query vector
    query_vector = sample_data[0][1]
    similar_vectors = mvg.find_similar_vectors(query_vector, 5)

    print("\nSimilar vectors:")
    for id, vector, movie_title, similarity in similar_vectors:
        print(f"ID: {id}, Movie: {movie_title}, Similarity: {similarity:.4f}")

    print(f"\nChanging embedding length from {initial_embedding_length} to {new_embedding_length}")
    mvg.change_vector_dimension(new_embedding_length)

    # Find similar vectors after changing dimension
    query_vector_new = np.random.rand(new_embedding_length)  # New example query vector
    similar_vectors_new = mvg.find_similar_vectors(query_vector_new, 5)

    print("\nSimilar vectors after changing dimension:")
    for id, vector, movie_title, similarity in similar_vectors_new:
        print(f"ID: {id}, Movie: {movie_title}, Similarity: {similarity:.4f}")