import glob
import logging
import os
import re

from services.gogdb_client import GOGDBClient
from utils import save_json

logger = logging.getLogger(__name__)


class ManifestGenerator:
    """
    Service for generating installer manifests which can be passed to innoextractor for extraction.
    """
    def __init__(self, manifests_output_dir=None):
        self.manifests_output_dir = manifests_output_dir or os.getenv('MANIFESTS_OUTPUT_DIR')
        self.gogdb_client = GOGDBClient()

    def generate_manifest(
            self,
            source_type,
            source_dir,
            default_dest_dir,
            possible_dest_dirs,
            ignores,
            overrides,
            base_installer_only=False
    ):
        """
        Generates a JSON manifest for innoextractor based on game source folder contents.
        """
        if not os.path.isdir(source_dir):
            logger.warning(f"Source directory not found. Skipping: {source_dir}")
            return {}

        logger.info(f"Generating manifest data for source type '{source_type}'...")

        # Create lookup dict with game key as the key, and latest game source folder for each value
        latest_source_folder_by_game_key = self._get_latest_source_folder_by_game_key(source_type, source_dir, ignores)

        manifest_data = {}
        for game_key, source_folder_name in latest_source_folder_by_game_key.items():
            logger.info(f"Adding game key '{game_key}' data to manifest")

            clean_key = self._clean_game_key(game_key)
            game_source_dir = os.path.join(source_dir, source_folder_name)

            # Get game name and version, either using !info.txt, GOGDB database, or the game key
            game_name, game_version = self._get_game_details(source_type, clean_key, game_source_dir)

            folder_name = self._clean_game_name(game_name)

            # Check for existing installation across possible root directories
            game_dest_dir = os.path.join(default_dest_dir, folder_name)
            for destination_dir in possible_dest_dirs:
                possible_game_dir = os.path.join(destination_dir, folder_name)
                if os.path.exists(possible_game_dir) and os.listdir(possible_game_dir):
                    game_dest_dir = possible_game_dir
                    break

            # Get sorted installer paths from overrides or using sorting logic
            if overrides.get(source_folder_name):
                logger.info(f"Using override installers for game key '{game_key}'")
                sorted_installers = overrides.get(source_folder_name, [])
            else:
                sorted_installers = self._get_sorted_installers(
                    clean_key,
                    game_source_dir,
                    base_installer_only=base_installer_only
                )

            manifest_data[game_key] = {
                "game_name": folder_name,
                "game_version": game_version,
                "source_directory": game_source_dir,
                "destination_directory": game_dest_dir,
                "sorted_installers": sorted_installers,
            }

        manifest_path = os.path.join(self.manifests_output_dir, source_type + ".json")
        save_json(manifest_data, manifest_path)

        logger.info(f"Successfully generated and saved manifest: {manifest_path}")

        return manifest_data

    def _get_latest_source_folder_by_game_key(self, source_type, source_dir, ignores):
        """
        Scans the root source directory and creates a dictionary which groups game folders by their
        game key. If multiple game folders exist for a game key, it only includes the latest folder
        according to package version.
        """
        source_folder_tuples_by_game_key = {}

        for source_folder_name in os.listdir(source_dir):
            # Skip if source folder name is in ignore patterns
            is_ignored = False
            for ignore_pattern in ignores:
                if re.fullmatch(re.escape(ignore_pattern).replace(r'\*', '.*'), source_folder_name):
                    logger.debug(f"Ignoring '{source_folder_name}' due to pattern '{ignore_pattern}'")
                    is_ignored = True
                    break

            if is_ignored:
                continue

            game_key = source_folder_name
            package_version = None

            # If 'gog-games' source, extract game key and package version, whilst excluding instances of '_windows_gog_'
            # Otherwise, treat the source folder name as the game key and package version as None
            if source_type == "gog-games":
                match = re.match(r"([a-zA-Z0-9_.]+)_windows_gog_\(([\d\.]+)\)", source_folder_name)
                if match:
                    game_key = match.group(1)
                    version_str = match.group(2).replace('.', '')
                    try:
                        package_version = int(version_str)
                    except ValueError:
                        pass

            # Build a dictionary which groups tuples (of package version and source folder names) by their game key
            source_folder_tuples_by_game_key.setdefault(game_key, []).append((package_version, source_folder_name))

        latest_source_folder_by_game_key = {}

        # Sort tuples under each game key by their package version
        for game_key, source_folder_tuples in source_folder_tuples_by_game_key.items():
            source_folder_tuples.sort(reverse=True, key=lambda x: (x[0] is None, x[0]))

            # Use the latest source folder for each game key to populate the final dictionary
            _, latest_folder_name = source_folder_tuples[0]
            latest_source_folder_by_game_key[game_key] = latest_folder_name

        return latest_source_folder_by_game_key

    def _clean_game_key(self, raw_key):
        """
        Clean raw game key by removing '_base_game', '_base', or '_game' suffix.
        """
        clean_key = re.sub(r'_base_game$', '', raw_key)
        if not re.search(r'_(second)_base$', clean_key):
            clean_key = re.sub(r'_base$', '', clean_key)
        if not re.search(r'_(the|video|action|adventure|playing)_game$', clean_key):
            clean_key = re.sub(r'_game$', '', clean_key)
        return clean_key

    def _clean_game_name(self, raw_name):
        """
        Cleans the game name to make it suitable to use in a file path.
        """
        clean_name = re.sub(r'[<>:"/\\|?*]', ' ', raw_name)
        clean_name = re.sub(r'\s+', ' ', clean_name).strip()
        return clean_name

    def _get_game_details(self, source_type, clean_key, game_source_dir):
        """
        Gets the game name and version from various sources using fallback logic.
        """
        game_name = None
        game_version = None
        
        # 1. For 'gog-service' sources, try to extract game name and version from !info.txt file
        if source_type == "gog-service":
            game_name, game_version = self._get_game_details_from_info_file(game_source_dir)

        # 2. If no game version found, try to extract from main game installer filename
        if not game_version:
            game_version = self._get_game_version_from_base_installer(clean_key, game_source_dir)

        # 3. If no game name found, try and query from GOGDB database
        if not game_name:
            game_name = self.gogdb_client.get_game_name(clean_key)

        # 4. If still no game name found, use cleaned key
        if not game_name:
            game_name = clean_key.replace('_', ' ').title().strip()
            logger.info(f"Could not determine game name. Using '{game_name}' from cleaned key.")

        return game_name, game_version

    def _get_game_details_from_info_file(self, game_source_dir):
        """
        Gets the game name and version from info file (!info.txt) within a game source directory.
        """
        game_name = None
        game_version = None

        info_file_path = os.path.join(game_source_dir, "!info.txt")
        if not os.path.exists(info_file_path):
            logger.warning(f"!info.txt not found in source directory: {info_file_path}.")
            return game_name, game_version

        try:
            with open(info_file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()

            game_name_line = lines[1].strip()
            parts = game_name_line.split('--')
            if len(parts) >= 3:
                raw_name = parts[1].strip()
                encoded_name = raw_name.encode('ascii', 'ignore').decode('ascii')
                game_name = re.sub(r'\s+', ' ', encoded_name).strip()

            version_pattern = re.compile(r'^\s*version:\s*(.*)', re.IGNORECASE)
            for line in lines:
                match = version_pattern.search(line)
                if match:
                    game_version = match.group(1).strip()
                    break

        except Exception as e:
            logger.error(f"Error reading or parsing info file {info_file_path}: {e}")

        return game_name, game_version

    def _get_game_version_from_base_installer(self, clean_key, game_source_dir):
        """
        Gets the game version from the main game installer filename within a game source directory.
        """
        base_installer_path = self._get_base_installer_path(clean_key, game_source_dir)
        if not base_installer_path:
            return None

        key_match_pattern = clean_key.replace('_', r'[-_\s]+')
        ver_extract_pattern = re.compile(
            rf'^setup_{key_match_pattern}(.+?)(?:\_\(64bit\))?\_\(\d+\)\.exe$',
            re.IGNORECASE
        )

        filename = os.path.basename(base_installer_path)

        version_match = ver_extract_pattern.search(filename)
        if version_match:
            return version_match.group(1).strip('_-')

        return None

    def _get_sorted_installers(self, clean_key, game_source_dir, base_installer_only=False):
        """
        Generates a sorted list of relative installer paths within a game source directory.
        """
        base_installer_path = self._get_base_installer_path(clean_key, game_source_dir)
        if not base_installer_path:
            return []

        sorted_paths = []

        if base_installer_path:
            # Include base installer as first entry in sorted installer list
            sorted_paths.append(base_installer_path)

        if not base_installer_only:
            # All other installers (dlc/extras) are included in their original order
            all_paths = glob.glob(os.path.join(game_source_dir, 'setup_*.exe'))
            other_installer_paths = [p for p in all_paths if p != base_installer_path]
            sorted_paths.extend(other_installer_paths)

        sorted_rel_paths = [os.path.relpath(path, start=game_source_dir) for path in sorted_paths]

        return sorted_rel_paths

    def _get_base_installer_path(self, clean_key, game_source_dir):
        """
        Gets the main game installer path within a game source directory.
        """
        all_paths = glob.glob(os.path.join(game_source_dir, 'setup_*.exe'))
        if not all_paths:
            logger.warning(f"No setup_*.exe files found in source directory: {game_source_dir}")
            return None

        all_paths.sort(key=lambda x: len(os.path.basename(x)))

        # 1. Try to find installer with a companion .bin file
        for path in all_paths:
            installer_basename = os.path.splitext(os.path.basename(path))[0]
            installer_bin_path = os.path.join(game_source_dir, f'{installer_basename}-1.bin')

            if os.path.exists(installer_bin_path):
                return path

        # 2. Try to find first installer (with shortest file name) which matches the clean key pattern
        key_match_pattern = clean_key.replace('_', r'[-_\s]+')
        main_installer_pattern = re.compile(rf'^setup_{key_match_pattern}', re.IGNORECASE)

        main_paths = [p for p in all_paths if main_installer_pattern.match(os.path.basename(p))]
        if main_paths:
            return main_paths[0]

        # 3. Otherwise, assume first installer with shortest filename is base installer
        return all_paths[0]
