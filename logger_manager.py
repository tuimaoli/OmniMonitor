import os
import time
import logging
import re
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

class LoggerManager:
    def __init__(self, config):
        self.cfg = config.get('logging', {})
        self.log_dir = self.cfg.get('log_dir', './logs')
        self.retention_days = self.cfg.get('retention_days', 7)
        self.level_str = self.cfg.get('level', 'INFO')
        
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir)
            
        self.logger = logging.getLogger("PushMonitor")
        self.logger.setLevel(getattr(logging, self.level_str.upper(), logging.INFO))
        self.logger.propagate = False 
        
        # 优化: 预编译正则表达式，节省重复编译开销
        self.log_name_pattern = re.compile(r"monitor-(\d{4}-\d{2}-\d{2})\.log")

        if not self.logger.handlers:
            self._setup_handlers()
            
    def _setup_handlers(self):
        base_filename = os.path.join(self.log_dir, "monitor.log")
        
        file_handler = TimedRotatingFileHandler(
            base_filename, 
            when="midnight", 
            interval=1, 
            backupCount=self.retention_days, 
            encoding='utf-8'
        )
        file_handler.suffix = "%Y-%m-%d"
        
        def custom_namer(default_name):
            path, filename = os.path.split(default_name)
            parts = filename.split('.')
            if len(parts) >= 3:
                date_part = parts[-1]
                new_filename = f"monitor-{date_part}.log"
                return os.path.join(path, new_filename)
            return default_name

        file_handler.namer = custom_namer
        
        console_handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        file_handler.setFormatter(formatter)
        console_handler.setFormatter(formatter)
        
        self.logger.addHandler(file_handler)
        self.logger.addHandler(console_handler)

    def get_logger(self):
        return self.logger

    def clean_old_logs(self):
        """
        基于文件名的日期比对清理逻辑
        """
        try:
            today = datetime.now().date()
            # 优化: 使用预编译的正则
            
            for f in os.listdir(self.log_dir):
                match = self.log_name_pattern.match(f)
                if match:
                    date_str = match.group(1)
                    try:
                        file_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                        days_diff = (today - file_date).days
                        
                        if days_diff > self.retention_days:
                            fp = os.path.join(self.log_dir, f)
                            os.remove(fp)
                            self.logger.info(f"已清理过期日志: {f}")
                    except ValueError:
                        continue 
                    except Exception as e:
                        self.logger.warning(f"删除日志失败 {f}: {e}")
                        
        except Exception as e:
            self.logger.error(f"日志清理流程异常: {e}")
