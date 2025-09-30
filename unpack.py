import argparse
import os

from dotenv import load_dotenv

from helpers import get_game_details_from_gog_info_file
from logger import setup_logger
from services.innoextractor import Innoextractor
from services.manifest_generator import ManifestGenerator
from utils import read_jsonc, read_meta_file, create_meta_file

load_dotenv()

CONFIG_PATH = os.getenv('CONFIG_PATH')

logger = setup_logger(log_name='unpack')


def main():
    parser = argparse.ArgumentParser(description="Generate and process GOG game manifests.")
    parser.add_argument(
        '--config',
        type=str,
        help="Key of the config to process. If not provided, all configs are processed.",
        required=False
    )
    parser.add_argument(
        '--game',
        type=str,
        help="Key of the specific game to process. If not provided, all games within manifest are processed.",
        required=False
    )
    parser.add_argument(
        '--force',
        action='store_true',
        help="If provided, the game will be reinstalled to its destination directory, even if the source hasn't changed.",
        required=False
    )
    parser.add_argument(
        '--base-installer-only',
        action='store_true',
        help="If provided, only the base game installer (if found) will be included in manifest.",
        required=False
    )
    args = parser.parse_args()

    logger.info("Starting GOG unpack process...")

    config = read_jsonc(CONFIG_PATH)
    if not config:
        return

    manifest_generator = ManifestGenerator()
    innoextractor = Innoextractor(clear_destination=True)

    configs = config.items()  # Default to all configs
    if args.config:
        if args.config in config:
            configs = [(args.config, config[args.config])]
        else:
            logger.error(f"Config key '{args.config}' not found in configuration file.")
            return

    total_games = 0
    successful_games = 0

    for config_key, config_data in configs:
        source_type = config_data['source_type']
        source_dir = config_data['source_directory']
        default_dest_dir = config_data['default_destination_directory']
        possible_dest_dirs = config_data.get('possible_destination_directories', [])
        ignores = config_data.get('ignores', [])
        overrides = config_data.get('overrides', {})

        logger.info(f"Processing config '{config_key}'...")

        # Generate and save manifest data
        manifest_data = manifest_generator.generate_manifest(
            source_type,
            source_dir,
            default_dest_dir,
            possible_dest_dirs,
            ignores,
            overrides,
            base_installer_only=args.base_installer_only
        )

        # Process all games within manifest, or a single game if user passes the --game argument.
        games_to_process = manifest_data.items()
        if args.game:
            if args.game in manifest_data:
                games_to_process = [(args.game, manifest_data[args.game])]
            else:
                logger.warning(
                    f"Game key '{args.game}' not found in manifest for config '{config_key}'. Skipping."
                )
                continue

        for game_key, game_data in games_to_process:
            game_name = game_data['game_name']
            game_version = game_data.get('game_version', '')
            game_source_dir = game_data['source_directory']
            game_dest_dir = game_data['destination_directory']
            sorted_installers = game_data['sorted_installers']

            if not game_data.get('sorted_installers'):
                logger.warning(f"No installers found for game '{game_name}'. Skipping.")
                continue

            total_games += 1

            # Don't extract if the source directory and version haven't changed, unless user passes
            # the --force argument.
            if os.path.exists(game_dest_dir) and not args.force:
                existing_meta = read_meta_file(game_dest_dir)

                existing_source_dir = existing_meta.get('source_directory')
                existing_game_version = existing_meta.get('game_version')

                if existing_source_dir == game_source_dir and existing_game_version == game_version:
                    logger.info(f"Game '{game_name}' is already up-to-date. Skipping.")
                    successful_games += 1
                    continue

            # Extract sorted installers to destination directory
            success = innoextractor.process_game(
                game_name,
                game_source_dir,
                game_dest_dir,
                sorted_installers
            )

            if success:
                successful_games += 1

                # The manifest uses folder name as game name. So, here we update the game name by
                # processing goggame-###.info files extracted by innoextractor and then use the
                # parsed game name in !meta.txt, with folder name used as a fallback.
                game_name, rel_launcher_path = get_game_details_from_gog_info_file(game_dest_dir)

                meta_data = {
                    'game_name': game_name or game_data['game_name'],
                    'game_version': game_version or "",
                    'rel_launcher_path': rel_launcher_path,
                    'source_directory': game_source_dir,
                    'sorted_installers': sorted_installers,
                }
                create_meta_file(game_dest_dir, meta_data)

    logger.info(f"Unpack finished. Successfully processed {successful_games}/{total_games} games.")
    if innoextractor.failed_extractions:
        logger.warning(f"{len(innoextractor.failed_extractions)} games failed to extract.")


if __name__ == "__main__":
    main()
