from io import TextIOWrapper
import os
import json
from quart import Quart
import sys


def remove_json_value(file_path, key):
    try:
        with open(file_path, "r+") as file:
            data = json.load(file)
            if key in data:
                del data[key]
                file.seek(0)
                json.dump(data, file, indent=4)
                file.truncate()
            else:
                print(f"Key '{key}' not found in JSON.", file=sys.stderr)
    except FileNotFoundError:
        print(f"File '{file_path}' not found.", file=sys.stderr)
    except json.JSONDecodeError:
        print(f"Error decoding JSON in file '{file_path}'.", file=sys.stderr)
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)


# Example usage:
# remove_json_value('data.json', 'name')


def set_file_json_value(file_path, key, value):
    try:
        with open(file_path, "r+") as file:
            data = json.load(file)
            data[key] = value
            file.seek(0)
            json.dump(data, file)
            file.truncate()
    except FileNotFoundError:
        print(f"File '{file_path}' not found.", file=sys.stderr)
    except json.JSONDecodeError:
        print(f"Error decoding JSON in file '{file_path}'.", file=sys.stderr)
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)


def get_file_metadata(server: Quart, md5_name, key):
    metadata_folder = server.config["METADATA_FOLDER"]

    metadata_file_path = os.path.join(metadata_folder, f"{md5_name}.json")

    if os.path.exists(metadata_file_path):
        with open(metadata_file_path, "r") as metadata_file:
            metadata = json.load(metadata_file)
            return metadata.get(key, None)
    else:
        return None
