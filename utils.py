import json
import logging
import os
import re

import json5

logger = logging.getLogger(__name__)


def read_json(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Failed to read JSON file {file_path}: {e}")
        raise


def read_jsonc(file_path):
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return json5.load(f)
    except Exception as e:
        logger.error(f"Failed to read JSONC file {file_path}: {e}")
        raise


def save_json(data, file_path):
    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        logger.error(f"Failed to save JSON to {file_path}: {e}")
        raise


def read_meta_file(target_dir):
    meta_file_path = os.path.join(target_dir, '!meta.txt')
    if not os.path.exists(meta_file_path):
        return {}

    data = {}
    key_value_pattern = re.compile(r'^\s*([\w\-]+)\s*:\s*(.*)')

    try:
        with open(meta_file_path, 'r', encoding='utf-8') as f:
            for line in f:
                match = key_value_pattern.match(line)
                if match:
                    key = match.group(1).strip()
                    value = match.group(2).strip()

                    if key:
                        if value == '' or value.lower() == 'none':
                            data[key] = None
                        else:
                            data[key] = value

    except Exception as e:
        logger.error(f"Error reading meta file {meta_file_path}: {e}")

    return data


def create_meta_file(target_dir, game_data):
    meta_file_path = os.path.join(target_dir, '!meta.txt')
    content_lines = []
    for key, value in game_data.items():
        try:
            line = f"{str(key).strip()}: {str(value).strip()}\n"
            content_lines.append(line)
        except Exception as e:
            logger.error(f"Skipping key '{key}' due to formatting error: {e}")
            continue

    content = "".join(content_lines)

    try:
        with open(meta_file_path, 'w', encoding='utf-8') as f:
            f.write(content)

        logger.info(f"Successfully created meta file: {meta_file_path}")
        return True
    except IOError as e:
        logger.error(f"Error creating meta file {meta_file_path}: {e}")
        return False
