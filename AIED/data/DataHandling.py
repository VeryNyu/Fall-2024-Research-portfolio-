from os import path
import json, pandas
import random

FILE_PATH = "AIED/data/"

def load_all_json():
    files = dict()

    for fileName in ["combatants", "decks", "skills", "cards", "epiphanies"]:
        with open(f"AIED/data/{fileName}.json") as f:
            files[f"{fileName}_data"] = json.load(f)
    
    return files


def load_json(filename):
    with open(path.join(FILE_PATH, filename), "r") as f:
        return json.load(f)


def load_csv(filename):
    return pandas.read_csv(path.join(FILE_PATH, filename),
        header=None,
        engine="python",
        on_bad_lines="skip"
    )


def pick_random_items(d):
    return random.choice(list(d.items()))


def pick_random_key(d):
    return random.choice(list(d.keys()))


def pick_random_value(d):
    return random.choice(list(d.values()))


def pick_random_sample(v, k):
    return random.sample(v, k)