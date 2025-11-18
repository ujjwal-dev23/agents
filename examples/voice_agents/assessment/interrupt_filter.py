import logging
import re
import json
import asyncio
import os
from livekit.agents.voice.agent_session import AgentSession

logger = logging.getLogger("interrupt-filter")
logger.setLevel(logging.DEBUG)


class InterruptFilter:
    def __init__(self, session: AgentSession, config_path: str = "ignored_words.json"):
        self.session = session
        self.agent_is_speaking = False
        self.config_path = config_path
        self.ignored_words = set()
        self.poll_interval: int = 2
        self.confidence_threshold = 0.8
        self._last_mtime = 0

        self.load_config()

        # We use asyncio.create_task to continuously monitor changes in the config file in the background
        self._watcher_task = asyncio.create_task(self.watch_config_file())

        logger.info("InterruptFilter initialized")

    def load_config(self):
        """Reads the JSON configuration file and updates the ignored words list."""
        if not os.path.exists(self.config_path):
            logger.warning(f"Config file not found at {self.config_path}. Using empty word list")
            return

        try:
            with open(self.config_path, "r") as f:
                data = json.load(f)
                # Expected JSON format : {"ignored words": ["word1", "word2"], "poll_interval": time_in_seconds}
                self.ignored_words = set()
                active_langs = data.get("active_languages", ["en"])
                all_langs = data.get("languages", {})
                for lang in active_langs:
                    self.ignored_words.update(all_langs.get(lang, []))
                logger.info(f"Updated ignored words list : {self.ignored_words}")

                self.poll_interval = data.get("poll_interval")
                logger.info(f"Updated poll interval to {self.poll_interval} seconds")

        except Exception as e:
            logger.error(f"Failed to load config file : {e}")

    async def watch_config_file(self):
        """Polls the config file for changes every x seconds as defined in ignored_words.json"""
        while True:
            await asyncio.sleep(self.poll_interval)  # Check every x seconds
            try:
                if not os.path.exists(self.config_path):
                    continue

                # Check if file has been modified since last read
                current_mtime = os.path.getmtime(self.config_path)
                if current_mtime != self._last_mtime:
                    self._last_mtime = current_mtime
                    logger.info("Config file change detected. Reloading...")
                    self.load_config()

            except Exception as e:
                logger.error(f"Error watching config file : {e}")

    def resume_agent_speech(self):
        """Resumes agent's current speech if it is playing and gets paused"""
        if not self.session.current_speech:
            return

        try:
            self.session.current_speech.resume()
            logger.debug("Agent speech RESUMED")
        except Exception as e:
            logger.warning(f"Failed to resume speech : {e}")

    def clean_text(self, text: str) -> set[str]:
        """Cleans transcription text into a set of words"""
        words = re.findall(r"\b\w+\b", text.lower())
        return set(words)

    def __del__(self):
        # Cleanup the background task if filter is destroyed
        if hasattr(self, "_watcher_task"):
            self._watcher_task.cancel()
