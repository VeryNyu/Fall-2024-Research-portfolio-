import json
import random

def load_all_json():
    files = dict()

    for fileName in ["combatants", "decks", "skills", "cards", "epiphanies"]:
        with open(f"AIED/data/{fileName}.json") as f:
            files[f"{fileName}_data"] = json.load(f)
    
    return files

def pick_random_items(d):
    return random.choice(list(d.items()))

def pick_random_key(d):
    return random.choice(list(d.keys()))

def pick_random_value(d):
    return random.choice(list(d.values()))

def pick_random_sample(v, k):
    return random.sample(v, k)