import logging
import os
import shutil
import subprocess
from datetime import datetime

logger = logging.getLogger(__name__)


class Innoextractor:
    """
    Service for extracting GOG game installers using innoextractor.
    """
    INNOEXTRACT_ERROR_MESSAGES = {
        1: "Generic error or syntax error",
        2: "File not found or I/O error",
        3: "Unsupported installer version",
        4: "Setup data is encrypted",
        5: "Checksum error",
        6: "Unknown error",
        7: "Unsupported compression method",
        8: "Corrupted installer",
        9: "Insufficient disk space",
        10: "Cancelled by user"
    }

    def __init__(self, innoextract_path=None, clear_destination=True):
        self.innoextract_path = innoextract_path or os.getenv('INNOEXTRACT_PATH')
        self.log_dir = os.getenv('LOG_DIR')
        self.clear_destination = clear_destination

        self.failed_extractions = []

    def process_game(self, game_name, source_dir, dest_dir, sorted_installers):
        """
        Process game by extracting its installers to the destination directory.
        """
        logger.info(f"Processing game '{game_name}'...")

        try:
            # If desired, first clear any existing destination directory
            if os.path.exists(dest_dir) and self.clear_destination:
                logger.info(f"Deleting existing destination directory: {dest_dir}")
                shutil.rmtree(dest_dir)

            os.makedirs(dest_dir, exist_ok=True)

            # Iterate through each game installer and extract using innoextract
            for installer_rel_path in sorted_installers:
                installer_path = os.path.join(source_dir, installer_rel_path)

                if not os.path.exists(installer_path):
                    raise FileNotFoundError(f"Installer not found: {installer_path}")

                result = self._extract_installer(installer_path, dest_dir)
                if not result:
                    raise RuntimeError("Failed to extract one of the installers")

            # Verify destination directory was created and is non-empty
            if not os.path.exists(dest_dir) or not os.listdir(dest_dir):
                raise RuntimeError("Extraction verification failed.")

            logger.info(f"Successfully extracted all installers for game")
            return True

        except (FileNotFoundError, RuntimeError) as e:
            logger.error(f"Failed to process game '{game_name}'. Cleaning up: {e}")

            if os.path.exists(dest_dir):
                try:
                    shutil.rmtree(dest_dir)
                except Exception as e_cleanup:
                    logger.error(f"Failed to clean up directory {dest_dir}: {e_cleanup}")

            self.failed_extractions.append({
                "game_name": game_name,
                "source_dir": source_dir,
                "dest_dir": dest_dir,
                "installers": sorted_installers,
                "timestamp": datetime.now().isoformat()
            })

            return False

    def _extract_installer(self, installer_path, dest_dir):
        """
        Extract a GOG installer using innoextract.
        """
        file_size_mb = os.path.getsize(installer_path) / (1024 * 1024)
        logger.info(f"Extracting installer: {installer_path} ({file_size_mb:.2f} MB)")

        command = [self.innoextract_path, '--gog', '-m', '-d', dest_dir, installer_path]
        extract_log = os.path.join(self.log_dir, f"innoextract_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")

        try:
            with open(extract_log, 'w', encoding='utf-8', errors='replace') as log_file:
                result = subprocess.run(
                    command,
                    stdout=log_file,
                    stderr=subprocess.STDOUT,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=10800
                )

            if result.returncode == 0:
                logger.info(f"Successfully extracted installer to destination directory: {dest_dir}")
                try:
                    os.remove(extract_log)
                except:
                    pass

                return True

            else:
                error_desc = self.INNOEXTRACT_ERROR_MESSAGES.get(
                    result.returncode,
                    f"Unknown error code: {result.returncode}"
                )
                logger.error(f"Error extracting installer: {error_desc}")
                logger.error(f"Full extraction log saved: {extract_log}")
                return False

        except subprocess.TimeoutExpired:
            logger.error(f"Extraction timed out after three hours")
            logger.error(f"Partial extraction log saved: {extract_log}")
            return False
        except FileNotFoundError:
            logger.error(f"innoextract not found: {self.innoextract_path}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error extracting {installer_path}: {e}")
            return False
