import requests
import random
import json
import time
from constants import VoteStatus

BASE_URL = "http://localhost:5000"

def test_enhanced_room():
    # Create room
    response = requests.post(f"{BASE_URL}/api/enhanced/createRoom")
    print(response)
    room_data = response.json()
    room_id = room_data['room_id']
    print(f"Created room: {room_id}")

    # Create users
    users = []
    for i in range(2):
        response = requests.post(
            f"{BASE_URL}/api/enhanced/createUser",
            json={"roomId": room_id, "userName": f"User{i+1}"}
        )
        user_data = response.json()
        users.append(user_data['user_id'])
        print(f"Created user {i+1}: {users[i]}")

    # Seeding phase
    for user_id in users:
        print(f"Seeding for user {user_id}")
        while True:
            # Get next movie
            try:
                response = requests.get(f"{BASE_URL}/api/enhanced/getNextMovie", params={"userId": user_id})
                movie_data = response.json()
                movie_id = movie_data['movie_id']
                
                # Submit vote
                vote_response = requests.post(
                    f"{BASE_URL}/api/enhanced/vote",
                    json={
                        "userId": user_id,
                        "movieId": movie_id,
                        "vote": random.choice(["like", "dislike"])
                    }
                )
                vote_data = vote_response.json()
                
                if vote_data['status'] == VoteStatus.USER_SEEDING_COMPLETE.value:
                    print(f"Seeding complete for user {user_id}")
                    # Test Queue Refill
                    response = requests.get(f"{BASE_URL}/api/enhanced/getNextMovie", params={"userId": user_id})
                    break
                elif vote_data['status'] == VoteStatus.SEEDING_COMPLETE.value:
                    print("All users completed seeding!")
                    # Test Queue Refill
                    response = requests.get(f"{BASE_URL}/api/enhanced/getNextMovie", params={"userId": user_id})
                    
                    # Get recommendations
                    rec_response = requests.get(f"{BASE_URL}/api/enhanced/getRecommendations", params={"userId": user_id})
                    recommendations = rec_response.json()
                    
                    print("\nFinal recommendations:")
                    user_queues = recommendations["userQueues"]
                    top_movies = recommendations["topMovies"]
                    movie_titles = recommendations["movieTitles"]
                    
                    print("\nUser queues:")
                    for uid, queue in user_queues.items():
                        print(f"\nUser {uid} queue:")
                        for movie in queue:
                            print(f'{movie_titles[str(movie)]}: {movie}')

                    print("\nTop movies in the room:")
                    for movie in top_movies:
                        print(f'{movie_titles[str(movie)]}: {movie}')
                    return
                    
            except Exception as e:
                print(f"Error in seeding phase: {e}")
                break

if __name__ == "__main__":
    test_enhanced_room() 