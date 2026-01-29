import os
import logging
import re
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler, MemoryHandler

class LoggerManager:
    def __init__(self, config, base_dir=None):
        """
        :param config: 配置字典
        :param base_dir: 项目根目录的绝对路径
        """
        self.cfg = config.get('logging', {})
        
        # 1. 路径处理：强制绝对路径
        raw_log_dir = self.cfg.get('log_dir', '/var/log/OmniMonitor')
        if base_dir and not os.path.isabs(raw_log_dir):
            self.log_dir = os.path.join(base_dir, raw_log_dir)
        else:
            self.log_dir = os.path.abspath(raw_log_dir)
            
        self.retention_days = self.cfg.get('retention_days', 7)
        self.level_str = self.cfg.get('level', 'INFO')
        self.project_name = "OmniMonitor"
        
        # 闪存保护配置：当缓冲区达到 50 条记录时再一次性写入磁盘，减少 IOPS
        self.use_flash_protection = self.cfg.get('flash_protection', True)
        self.buffer_capacity = self.cfg.get('buffer_capacity', 50) 
        
        if not os.path.exists(self.log_dir):
            os.makedirs(self.log_dir, exist_ok=True)
            
        self.logger = logging.getLogger("PushMonitor")
        self.logger.setLevel(getattr(logging, self.level_str.upper(), logging.INFO))
        self.logger.propagate = False 
        
        self.log_name_pattern = re.compile(rf"{self.project_name}-(\d{{4}}-\d{{2}}-\d{{2}})\.log")

        if not self.logger.handlers:
            self._setup_handlers()
            
    def _setup_handlers(self):
        # 2. 格式化器
        formatter = logging.Formatter(
            '[%(asctime)s] [%(levelname)s] %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )

        # 3. 文件处理器 (底层的磁盘写入操作)
        today_str = datetime.now().strftime("%Y-%m-%d")
        current_log_file = os.path.join(self.log_dir, f"{self.project_name}-{today_str}.log")
        
        file_handler = TimedRotatingFileHandler(
            current_log_file, 
            when="midnight", 
            interval=1, 
            backupCount=self.retention_days, 
            encoding='utf-8'
        )
        file_handler.suffix = "%Y-%m-%d"
        
        def custom_namer(default_name):
            path, filename = os.path.split(default_name)
            if filename.startswith(self.project_name):
                parts = filename.split('.')
                if len(parts) > 2:
                    return os.path.join(path, f"{parts[0]}.log")
            return default_name

        file_handler.namer = custom_namer
        file_handler.setFormatter(formatter)

        # 4. 关键：闪存保护 (MemoryHandler)
        if self.use_flash_protection:
            # MemoryHandler 会在内存中积攒日志
            # target 指定积攒满后交给谁去写磁盘
            # flushLevel 设为 ERROR 表示一旦遇到错误立即写盘，平时则攒着
            flash_handler = MemoryHandler(
                capacity=self.buffer_capacity, 
                flushLevel=logging.ERROR, 
                target=file_handler
            )
            self.logger.addHandler(flash_handler)
        else:
            self.logger.addHandler(file_handler)
        
        # 5. 控制台输出 (不受缓存影响，实时看到)
        console_handler = logging.StreamHandler()
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def get_logger(self):
        return self.logger

    def flush(self):
        """强制将内存中的日志刷入磁盘"""
        for handler in self.logger.handlers:
            if isinstance(handler, MemoryHandler):
                handler.flush()

    def clean_old_logs(self):
        try:
            today = datetime.now().date()
            for f in os.listdir(self.log_dir):
                match = self.log_name_pattern.match(f)
                if match:
                    date_str = match.group(1)
                    try:
                        file_date = datetime.strptime(date_str, "%Y-%m-%d").date()
                        if (today - file_date).days > self.retention_days:
                            os.remove(os.path.join(self.log_dir, f))
                            self.logger.info(f"已清理旧日志: {f}")
                    except: continue
        except Exception as e:
            self.logger.error(f"日志清理异常: {e}")
