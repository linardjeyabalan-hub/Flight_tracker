# tracker.py

import yaml

with open("config.yaml", "r") as f:
    config = yaml.safe_load(f)

for option in config["options"]:
    print(option["name"])