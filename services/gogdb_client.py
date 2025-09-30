import logging
import os
import re
import sqlite3
from datetime import datetime, timedelta

import requests

logger = logging.getLogger(__name__)


class GOGDBClient:
    """
    Client for managing and querying the GOGDB SQLite database.
    """

    def __init__(self, db_path=None, auto_update=True):
        self.db_path = db_path or os.getenv('GOGDB_DB_PATH')
        self.gogdb_url = os.getenv('GOGDB_URL')
        self.update_days = 7  # Re-download db file if older than seven days
        self.auto_update = auto_update

        self._available = os.path.exists(self.db_path)

        if not self._available:
            logger.warning(f"GOGDB database cannot be found, downloading...")
            self.download()

        if self.auto_update and not self._is_utd():
            logger.info(f"GOGDB database is out of date, re-downloading...")
            self.download()

    def query_one(self, query, params=None):
        """
        Execute a query and return the first result.
        """
        if not self._available:
            return None

        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            return cursor.fetchone()
        except sqlite3.Error as e:
            logger.error(f"Database query error: {e}")
            return None
        finally:
            if conn:
                conn.close()

    def query_all(self, query, params=None):
        """
        Execute a query and return all results.
        """
        if not self._available:
            return []

        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute(query, params or ())
            return cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Database query error: {e}")
            return []
        finally:
            if conn:
                conn.close()

    def get_game_name(self, game_key):
        """
        Convenience method for getting game name.
        """
        if not self._available:
            return None

        search_key = game_key.replace('_', '')
        logger.debug(f"Looking up game name in GOGDB database using key '{search_key}'...")

        result = self.query_one("SELECT title FROM products WHERE search_title = ?", (search_key,))
        if result:
            game_name = result[0].encode('ascii', 'ignore').decode('ascii')
            game_name = re.sub(r'[\\/:*?"<>|]', '', game_name)
            logger.debug(f"Found game name: '{game_name}'")
            return game_name

        logger.debug(f"No game found for key '{search_key}'")
        return None

    def download(self):
        """
        Download and verify the GOGDB database.
        """
        logger.info("Downloading GOGDB database...")

        try:
            # Download the db to a temporary file location
            response = requests.get(self.gogdb_url, stream=True)
            response.raise_for_status()

            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

            temp_file = self.db_path + ".temp"
            with open(temp_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)

            logger.info(f"Downloaded database to temporary location: {temp_file}")

            # Check the temporary db is valid, and if so, use it to replace original db
            if self._is_valid(temp_file):
                os.replace(temp_file, self.db_path)
                logger.info(f"Successfully updated database: {self.db_path}")
                return True

            else:
                logger.error("Downloaded database failed validation. Cleaning up.")
                if os.path.exists(temp_file):
                    os.remove(temp_file)

            return False

        except requests.exceptions.RequestException as e:
            logger.error(f"Error downloading database: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during database download: {e}")
            return False

    def _is_utd(self):
        """
        Ensure database is up to date by checking modified date is within range.
        """
        file_mod_time = datetime.fromtimestamp(os.path.getmtime(self.db_path))
        return datetime.now() - file_mod_time <= timedelta(days=self.update_days)

    def _is_valid(self, db_path):
        """
        Ensure database file is a valid SQLite database with expected structure.
        """
        conn = None
        try:
            conn = sqlite3.connect(db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='products' LIMIT 1;")
            result = cursor.fetchone()
            if result:
                cursor.execute("SELECT COUNT(*) FROM products LIMIT 1;")
                count = cursor.fetchone()[0]
                return count > 0
            return False
        except sqlite3.Error as e:
            logger.error(f"GOGDB database validation error: {e}")
            return False
        finally:
            if conn:
                conn.close()
