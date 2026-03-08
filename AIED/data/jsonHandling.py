import json

def load_all_json():
    files = dict()

    for fileName in ["combatants", "decks", "skills", "cards", "epiphanies"]:
        with open(f"AIED/data/{fileName}.json") as f:
            files[f"{fileName}_data"] = json.load(f)
    
    return files