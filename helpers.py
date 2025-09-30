import glob
import json
import logging
import os

logger = logging.getLogger(__name__)


def get_game_details_from_gog_info_file(game_source_dir):
    """
    Gets the game name and launcher path from any GOG info files (goggame-*.info) within a game
    source directory.
    """
    game_source_dir = os.path.abspath(game_source_dir)

    # 1. Look for info files in the parent directory only (non-recursive)
    info_file_paths = glob.glob(os.path.join(game_source_dir, 'goggame-*.info'))

    # 2. If no info files were found in the parent directory, scan recursively
    if not info_file_paths:
        info_file_paths = glob.glob(
            os.path.join(game_source_dir, '**', 'goggame-*.info'),
            recursive=True
        )

    # Process any identified GOG info files
    for info_file in info_file_paths:
        try:
            with open(info_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

                # Get the directory where the info file was found
                info_file_dir = os.path.dirname(info_file)

                play_tasks = data.get('playTasks', [])
                for task in play_tasks:
                    if task.get('isPrimary') is True and task.get('path'):
                        game_name = data.get('name') or task.get('name')

                        # Get absolute path to game launcher, then find path relative to source dir
                        abs_launcher_path = os.path.join(info_file_dir, task['path'])
                        rel_launcher_path = os.path.relpath(abs_launcher_path, start=game_source_dir)

                        return game_name, rel_launcher_path

        except (IOError, json.JSONDecodeError) as e:
            logger.warning(f"Error reading or parsing GOG info file '{info_file}': {e}")
            continue

    return None, None
