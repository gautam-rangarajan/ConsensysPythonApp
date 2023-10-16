import pandas as pd 
import json

#'release_date': str,

#Read CSV
amf = pd.read_csv("amf.csv")

#all movies filtered
#amf = all_movies[['original_title', 'overview', 'adult', 'genres', 'id', 'release_date', 'runtime', 'tagline', 'vote_average', 'vote_count']]
#amf.to_csv("amf.csv")


a = "[{'id': 12, 'name': 'Adventure'}, {'id': 14, 'name': 'Fantasy'}, {'id': 10751, 'name': 'Family'}]"


genres = ['Animation', 'Fantasy', 'Family']
#genres = ['Animation', 'Comedy', 'Crime']

print('genres', genres)
b = a.replace("'", "\"")

c = json.loads(b)

d = [x["name"] for x in c]
print('d', d)

d_set = set(d)
genres_set = set(genres)

inter = d_set.intersection(genres_set)
print(inter)


room_states = {
}
a = 30
room_states[str(a)] = 
print(room_states)