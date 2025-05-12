import logging
from fastapi import APIRouter, HTTPException, status
from typing import Dict, List, Literal
from datetime import datetime # Import datetime to get the current hour

# --- Get Logger ---
logger = logging.getLogger(__name__)

# --- API Router ---
router = APIRouter()

# --- Time Context Type ---
# Using Python's Literal for type hinting possible time contexts
TimeContext = Literal['Morning', 'Afternoon', 'Evening', 'Night', 'Default']

# --- Time-Based Contextual Symbol Data (Python Equivalent) ---
# Expanded lists based on the previous request
TIME_CONTEXT_SYMBOLS_DATA: Dict[TimeContext, List[str]] = {
    'Morning': [
        'good morning', 'breakfast', 'eat', 'drink', 'milk', 'cereal', 'toast',
        'brush teeth', 'get dressed', 'school', 'bus', 'play', 'happy', 'sun',
        'wake up', 'juice', 'water', 'bathroom', 'wash hands', 'clothes',
        'school bus', 'backpack', 'coat', 'cold', 'sunny', 'clouds', 'rain',
        'go to school', 'get ready', 'hair', 'shoes', 'socks', 'jacket', 'car',
        'walk', 'run', 'friends', 'teacher', 'classroom', 'book', 'pencil',
        'paper', 'draw', 'write', 'read', 'learn', 'fun', 'awake', 'stretch'
    ],
    'Afternoon': [
        'good afternoon', 'lunch', 'eat', 'drink', 'water', 'sandwich', 'play',
        'outside', 'park', 'swing', 'slide', 'friends', 'home', 'nap', 'snack',
        'book', 'read', 'car', 'walk', 'happy', 'homework', 'bicycle', 'scooter',
        'dog', 'cat', 'birds', 'flowers', 'tree', 'grass', 'sun', 'hot', 'warm',
        'playground', 'run', 'jump', 'climb', 'share', 'listen', 'talk', 'sing',
        'dance', 'quiet time', 'rest', 'tidy up', 'chores', 'help', 'finished',
        'more', 'thirsty', 'hungry', 'tired', 'clean', 'lesson', 'activity'
    ],
    'Evening': [
        'good evening', 'dinner', 'eat', 'drink', 'water', 'family', 'play',
        'bath', 'pajamas', 'book', 'read', 'tired', 'bedtime', 'moon', 'stars',
        'television', 'game', 'finished', 'more', 'hungry', 'story', 'clean teeth',
        'bed', 'soft', 'warm', 'quiet', 'calm', 'hug', 'kiss', 'friend', 'talk',
        'laugh', 'wash face', 'wash body', 'towel', 'sleepy', 'blanket', 'pillow',
        'light off', 'good night', 'dream', 'tomorrow', 'today', 'yesterday',
        'happy', 'sad', 'angry', 'scared', 'love', 'like', 'dislike', 'want', 'need',
        'wind down', 'relax', 'cuddle'
    ],
    'Night': [
        'good night', 'sleep', 'bed', 'tired', 'dark', 'moon', 'stars', 'dream',
        'pajamas', 'book', 'mom', 'dad', 'hug', 'kiss', 'quiet', 'light off',
        'sleepy', 'blanket', 'pillow', 'finished', 'sleep tight', 'warm', 'soft',
        'stuffed animal', 'darkness', 'quiet time', 'calm', 'tomorrow', 'morning',
        'rest', 'snore', 'eyes closed', 'stay in bed', 'wake up', 'dreaming', 'finished',
        'shhh', 'turn over'
    ],
    'Default': [
        'hello', 'goodbye', 'yes', 'no', 'please', 'thank you', 'more', 'finished',
        'help', 'want', 'eat', 'drink', 'play', 'bathroom', 'hurt', 'sad', 'happy',
        'tired', 'mom', 'dad', 'need', 'go', 'stop', 'look', 'listen', 'see', 'hear',
        'feel', 'good', 'bad', 'hungry', 'thirsty', 'angry', 'scared', 'love', 'like',
        'dislike', 'big', 'small', 'sorry', 'excuse me', 'here', 'there', 'up', 'down',
        'in', 'out', 'on', 'off', 'less', 'all done', 'now', 'later', 'today', 'tomorrow',
        'yesterday', 'I', 'you', 'he', 'she', 'it', 'we', 'they', 'my', 'your', 'his',
        'her', 'its', 'our', 'their', 'is', 'am', 'are', 'was', 'were', 'will', 'can',
        'cannot', 'do', 'does', 'did', 'have', 'has', 'had', 'get', 'give', 'take',
        'come', 'go', 'make', 'put', 'run', 'say', 'see', 'send', 'show', 'sit', 'stand',
        'tell', 'think', 'use', 'work', 'write', 'different', 'same' # Added a couple more here too
    ]
}


# --- Function to determine time context (Python Equivalent) ---
def get_current_time_context() -> TimeContext:
    """
    Determines the current time context based on the hour of the day.
    Uses the server's local time.
    """
    hour = datetime.now().hour
    if 5 <= hour < 12:
        return 'Morning'
    if 12 <= hour < 17:
        return 'Afternoon'
    if 17 <= hour < 21:
        return 'Evening'
    # Covers 9 PM onwards and 12 AM to 4:59 AM
    if hour >= 21 or hour < 5:
        return 'Night'
    return 'Default' # Fallback

# --- Function to get symbols based on time context (Python Equivalent) ---
def get_contextual_symbols(context: TimeContext) -> List[str]:
    """
    Retrieves a list of symbols relevant to a given time context.
    Looks up the context in TIME_CONTEXT_SYMBOLS_DATA.
    """
    # Use .get() with a default of the 'Default' list to handle any unexpected context
    return TIME_CONTEXT_SYMBOLS_DATA.get(context, TIME_CONTEXT_SYMBOLS_DATA['Default'])


# --- Mock/Hardcoded Standard Category Data ---
# Focused on daily communication for individuals with autism.
# Keys are lowercase.
# Added a few more items to some lists
MOCK_STANDARD_CATEGORIES_DATA: Dict[str, List[str]] = {
    "core words": [ # Essential high-frequency words
        "yes", "no", "more", "finished", "all done", "help", "want", "need", "like", "don't like",
        "stop", "go", "wait", "my turn", "your turn", "please", "thank you", "mine", "good", "bad",
        "big", "small", "same", "different", "here", "there", "now", "later" # Added more here
    ],
    "social": [ # Greetings, politeness, social interaction
        "hello", "hi", "bye", "goodbye", "good morning", "good night", "how are you?",
        "I'm fine", "sorry", "excuse me", "friend", "play with me", "share", "listen", "look",
        "talk", "laugh", "smile", "wave" # Added more here
    ],
    "food": [
        "eat", "drink", "hungry", "thirsty", "apple", "banana", "bread", "water", "milk", "juice",
        "orange", "pizza", "cookie", "cake", "cheese", "grapes", "strawberry", "carrot",
        "chicken", "fish", "rice", "pasta", "sandwich", "soup", "snack", "breakfast", "lunch", "dinner",
        "yummy", "yucky", "more food", "finished food", "sweet", "salty", "bitter", "sour" # Added more here
    ],
    "drinks": [
        "drink", "thirsty", "water", "milk", "juice", "cup", "bottle", "soda", "tea", "hot chocolate",
        "more drink", "finished drink", "cold drink", "hot drink", "straw" # Added more here
    ],
    "people": [
        "mom", "dad", "teacher", "friend", "boy", "girl", "baby", "me", "you", "doctor",
        "brother", "sister", "grandma", "grandpa", "man", "woman", "he", "she", "they", "we",
        "family", "person", "people" # Added more here
    ],
    "feelings": [
        "happy", "sad", "angry", "scared", "surprised", "tired", "hurt", "sick", "excited", "love",
        "calm", "frustrated", "confused", "worried", "silly", "proud", "okay", "not okay", "feel",
        "better", "worse" # Added more here
    ],
    "actions": [ # Common verbs for requests and descriptions
        "play", "go", "stop", "want", "need", "help", "look", "see", "listen", "hear", "sleep", "rest",
        "run", "walk", "jump", "read", "write", "open", "close", "give", "take", "wash", "clean",
        "sing", "dance", "draw", "color", "talk", "hug", "come", "sit", "stand", "throw", "catch",
        "turn on", "turn off", "push", "pull", "find", "make", "put", "get", "tell", "show", "start",
        "finish" # Added more here
    ],
    "places": [
        "home", "house", "room", "school", "park", "playground", "store", "outside", "library", "hospital",
        "bathroom", "bedroom", "kitchen", "living room", "car", "bus", "go to", "come from",
        "upstairs", "downstairs", "garden", "shop", "pool" # Added more here
    ],
    "toys & play": [ # Combined for relevance
        "ball", "doll", "car", "blocks", "puzzle", "play", "game", "bike", "train", "plane",
        "teddy bear", "crayons", "paint", "bubbles", "book", "music", "computer", "tablet", "phone", "watch TV",
        "toy", "robot", "action figure", "board game", "card game", "build" # Added more here
    ],
    "clothing": [
        "shirt", "pants", "shoes", "socks", "hat", "jacket", "dress", "get dressed", "coat",
        "shorts", "sweater", "pajamas", "put on", "take off", "t-shirt", "jeans", "skirt", "boot" # Added more here
    ],
    "body parts": [
        "head", "eyes", "nose", "mouth", "ears", "hands", "feet", "arms", "legs", "tummy",
        "hair", "fingers", "toes", "teeth", "tongue", "hurt here", "wash hands", "brush teeth",
        "elbow", "knee", "shoulder", "face", "back" # Added more here
    ],
    "school items": [ # More specific than just "school" as a place
        "book", "pencil", "paper", "crayons", "scissors", "glue", "backpack",
        "desk", "chair", "computer", "teacher", "student", "learn", "read", "write", "homework",
        "eraser", "ruler", "pen", "coloring book" # Added more here
    ],
    "colors": [
        "red", "blue", "green", "yellow", "orange", "purple", "pink", "brown", "black", "white", "gray", "color"
    ],
    "numbers & quantity": [ # Combined for functional use
        "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "zero",
        "number", "count", "how many", "a little", "a lot", "some", "all", "more", "less", "none" # Added more here
    ],
    "nature & outside": [ # Common outdoor elements
        "tree", "flower", "sun", "moon", "star", "sky", "cloud", "rain", "snow", "wind",
        "grass", "leaf", "rock", "sand", "outside", "park", "walk", "bird", "insect", "water" # Added more here
    ],
    "time & schedule": [ # Basic time concepts for routines
        "time", "now", "later", "soon", "today", "yesterday", "tomorrow",
        "morning", "afternoon", "evening", "night", "day", "clock", "watch", "calendar",
        "first", "next", "then", "last", "finished", "time for", "wait", "before", "after",
        "early", "late" # Added more here
    ],
    "household items": [ # Common items in the home environment
        "table", "chair", "bed", "sofa", "lamp", "door", "window", "kitchen", "bathroom", "bedroom",
        "plate", "bowl", "fork", "spoon", "cup", "television", "phone", "computer", "light", "blanket", "pillow",
        "towel", "soap", "brush", "comb", "mirror", "toy box" # Added more here
    ],
    "questions": [ # Essential for seeking information and interaction
        "who", "what", "where", "when", "why", "how", "which", "question", "ask", "tell me",
        "is it", "can I", "do you" # Added more here
    ],
    "descriptors & concepts": [ # Adjectives, adverbs, and basic concepts
        "big", "small", "little", "hot", "cold", "fast", "slow", "loud", "quiet", "good", "bad",
        "nice", "pretty", "new", "old", "long", "short", "heavy", "light", "dark", "bright",
        "soft", "hard", "wet", "dry", "clean", "dirty", "same", "different", "up", "down", "in", "out", "on", "off", "under", "over",
        "inside", "outside", "next to", "behind", "in front of", "far", "near", "all", "none", "empty", "full" # Added more here
    ],
    "animals": [ # Common animals, often a topic of interest
        "dog", "cat", "bird", "fish", "bear", "lion", "horse", "cow", "pig", "duck", "frog",
        "elephant", "monkey", "rabbit", "sheep", "turtle", "snake", "spider", "bee", "ant",
        "chicken", "mouse", "fox", "wolf" # Added more here
    ]
}


# --- Existing Endpoint for Standard Categories ---
@router.get(
    "/standard-categories",
    response_model=Dict[str, List[str]],
    summary="Get Standard Symbol Categories (Autism Communication Focus)",
    description="Retrieves a predefined set of standard categories and symbol keywords, tailored for daily communication for individuals with autism. These are general categories, not time-specific.",
    tags=["Symbols & Categories"]
)
async def get_standard_symbol_categories():
    """
    Returns a dictionary where keys are category names (lowercase)
    and values are lists of symbol keywords (strings),
    optimized for daily communication for individuals with autism.
    """
    logger.info("Request received for standard symbol categories (autism communication focus).")
    try:
        if not MOCK_STANDARD_CATEGORIES_DATA:
            logger.warning("Standard categories data (autism focus) is empty or not configured.")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Standard category data (autism focus) not found or not configured."
            )

        logger.info(f"Returning {len(MOCK_STANDARD_CATEGORIES_DATA)} standard categories (autism focus).")
        return MOCK_STANDARD_CATEGORIES_DATA
    except Exception as e:
        logger.exception("An unexpected error occurred while fetching standard symbol categories (autism focus).")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving standard categories (autism focus)."
        )

# --- NEW Endpoint for Time-Based Symbols ---
@router.get(
    "/current-time-context",
    response_model=List[str],
    summary="Get Symbols based on Current Time Context",
    description="Retrieves a list of symbol keywords relevant to the current time of day (Morning, Afternoon, Evening, or Night). Uses the server's current local time to determine the context.",
    tags=["Symbols & Categories"]
)
async def get_symbols_by_time_context():
    """
    Determines the current time context and returns the list of
    relevant symbol keywords for that context.
    """
    logger.info("Request received for symbols based on current time context.")
    try:
        # Determine the current time context using the Python function
        current_context = get_current_time_context()
        logger.info(f"Current time context determined: {current_context}")

        # Get the symbols for that context using the Python function
        contextual_symbols = get_contextual_symbols(current_context)

        if not contextual_symbols:
             logger.warning(f"No symbols found for time context: {current_context}. Returning empty list.")
             # While unlikely with the current data structure, good to handle explicitly
             return []

        logger.info(f"Returning {len(contextual_symbols)} symbols for context: {current_context}.")
        return contextual_symbols

    except Exception as e:
        logger.exception("An unexpected error occurred while fetching time-based symbols.")
        # Raise an HTTP exception for the API consumer
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving symbols based on time context."
        )