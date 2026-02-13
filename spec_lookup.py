import json
from pathlib import Path
import re

DATA_DIR = Path(__file__).resolve().parent / 'data'
SPEC_DB_PATH = DATA_DIR / 'spec_database.json'

def load_spec_db():
    if not SPEC_DB_PATH.exists():
        return {}
    with open(SPEC_DB_PATH, 'r') as f:
        return json.load(f)

SPEC_DB = load_spec_db()

def find_model_specs(title):
    """
    Attempt to find the model in the spec database by searching for keys in the title.
    Returns the spec dictionary or default values if not found.
    """
    title_upper = title.upper()
    for model, specs in SPEC_DB.items():
        if model.upper() in title_upper:
            return specs

    # Default values for unknown models
    return {
        "ram_soldered": None,
        "ssd_soldered": False,
        "max_ram_capacity": "Unknown",
        "gpu_dedicated": False
    }

def get_soldered_status(title):
    specs = find_model_specs(title)
    return specs.get('ram_soldered'), specs.get('ssd_soldered')

def extract_cpu_gen(title):
    """
    Heuristics to extract CPU Generation from title
    """
    # Intel: i7-1185G7 -> 11th Gen, i7-8550U -> 8th Gen, i7-12700H -> 12th Gen
    intel_match = re.search(r'i[3579]-(\d{1,2})', title, re.I)
    if intel_match:
        gen = intel_match.group(1)
        if len(gen) == 1: return f"{gen}th Gen"
        return f"{gen}th Gen"

    # Apple: M1, M2, M3
    apple_match = re.search(r'M(\d)', title, re.I)
    if apple_match:
        return f"Apple {apple_match.group(1)}"

    return "Unknown"

def is_touchscreen(title):
    return any(word in title.lower() for word in ['touch', 'touchscreen', '2-in-1', 'x360', 'yoga'])
