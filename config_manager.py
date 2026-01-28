import os
import json
import logging

class ConfigManager:
    def __init__(self, config_path, logger=None):
        self.config_path = config_path
        self.logger = logger
        self._config = {}
        self._mtime = 0
        self.reload() # Initial load

    def reload(self):
        """Force reload from disk"""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._config = json.load(f)
                self._mtime = os.path.getmtime(self.config_path)
                return True
            except Exception as e:
                if self.logger: self.logger.error(f"Config load failed: {e}")
        return False

    def check_hot_reload(self):
        """Check if file modified externally"""
        try:
            current_mtime = os.path.getmtime(self.config_path)
            if current_mtime > self._mtime:
                if self.reload():
                    if self.logger: self.logger.info("♻️ Config file changed, hot reloaded.")
                    return True
        except:
            pass
        return False

    def save(self, new_config):
        """Atomic write to prevent corruption"""
        try:
            tmp_path = self.config_path + ".tmp"
            with open(tmp_path, 'w', encoding='utf-8') as f:
                json.dump(new_config, f, ensure_ascii=False, indent=4)
            # Atomic replacement
            os.replace(tmp_path, self.config_path)
            
            # Update memory and mtime
            self._config = new_config
            self._mtime = os.path.getmtime(self.config_path)
            return True
        except Exception as e:
            if self.logger: self.logger.error(f"Config save failed: {e}")
            raise e

    @property
    def data(self):
        """Get current config dict"""
        return self._config
