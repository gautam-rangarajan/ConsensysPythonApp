import pandas as pd

def load_full_csv(filename):
    amf = pd.read_csv(filename)
    return amf

def get_group_preferences():
    
    group_prefs = {
        'min_year': 2010,
        'max_year': 2023,
        'min_ratings': 6.0,
        'adult_allowed': True,
        'max_runtime':  120,
        'min_runtime': 60,
        'min_popularity':  1000,
        'genres': ['Adventure', 'Fantasy', 'Family']
    }

    return group_prefs

def get_initial_stack(amf, group_prefs):

    print(amf.head(5))
    print(group_prefs)
    min_year = group_prefs['min_year']
    max_year = group_prefs['max_year']
    min_ratings = group_prefs['min_ratings']
    adult_allowed = group_prefs['adult_allowed']
    max_runtime = group_prefs['max_runtime']
    min_runtime = group_prefs['min_runtime']
    min_popularity = group_prefs['min_popularity']
    genres = group_prefs['genres']

    print(min_ratings)
    initial_stack = amf.query('(@min_ratings < vote_average) & (@max_runtime > runtime)')

    return initial_stack


def join_room():

    return 0



def create_room(user_ids, room_ids, new_user_name):

    next_user_id = user_ids['user_id'].max() + 1
    next_room_id = room_ids['room_id'].max() + 1

    room_ids.append({next_room_id,  next_user_id,  new_user_name})
    user_ids.append({next_user_id,  next_room_id, new_user_name, True})

    return user_ids, room_ids

#----MAIN-----
#Get the data

amf = load_full_csv('amf.csv')

room_ids = pd.DataFrame(columns = ['room_id', 'host_user_id', 'host_user_name'])
user_ids = pd.DataFrame(columns = ['user_id', 'room_id', 'user_name', 'is_host'])

group_prefs = []

user_ids, room_ids = create_room(user_ids, room_ids, new_user_name)

group_prefs.append(get_group_preferences())

stack = get_initial_stack(amf, group_prefs)
print(stack)

consensus = True


while(consensus == False):

    user_id, card_id, decision = get_user_input()

    update_tallies(user_input)

    consensus, matches = check_for_consesus()

    update_stacks()

    display_newest_card()
 

# def get_user_input():


# def display_newest_card():


# def update_stacks():


# def check_for_consesus():


# def display_matches():


# def update_tallies():
