from enum import Enum

class VoteStatus(Enum):
    SEEDING = "seeding"
    USER_SEEDING_COMPLETE = "user_seeding_complete"
    SEEDING_COMPLETE = "seeding_complete"
    ERROR = "error"

# Constants from EnhancedRoom
SEED_VOTES_REQUIRED = 5  # Number of votes needed per user before recommendations

# Constants from UserProfileManager
MIN_VOTES_TO_UPDATE = 5
DISLIKE_FACTOR = 1/3 