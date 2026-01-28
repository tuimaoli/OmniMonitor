import os
from config_manager import ConfigManager
from logger_manager import LoggerManager
from push_client import PushPlusClient
from data_fetcher import DataFetcher
from monitor import SystemMonitor
from web_service import WebService
from scheduler import TaskScheduler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(BASE_DIR, 'config.json')
CACHE_FILE = os.path.join(BASE_DIR, '.push_cache_v2')

def main():
    # 1. 启动日志
    temp_cfg = {}
    try:
        import json
        with open(CONFIG_PATH, 'r') as f: temp_cfg = json.load(f)
    except: pass
    
    log_mgr = LoggerManager(temp_cfg)
    logger = log_mgr.get_logger()
    logger.info(">>> OmniMonitor v7.3 Starting...")

    # 2. 初始化核心组件
    config_mgr = ConfigManager(CONFIG_PATH, logger)
    
    # 3. 初始化服务组件
    pusher = PushPlusClient(config_mgr.data.get('pushplus_users', []), logger)
    fetcher = DataFetcher(config_mgr.data, logger)
    monitor = SystemMonitor(logger)

    # 4. 启动 Web 配置台
    web_server = WebService(
        config_manager=config_mgr, 
        logger=logger, 
        fetcher=fetcher, 
        monitor=monitor, 
        port=8888
    )
    web_server.start()

    # 5. 启动任务调度器 (主线程阻塞)
    scheduler = TaskScheduler(
        config_mgr=config_mgr,
        logger=logger,
        pusher=pusher,
        fetcher=fetcher,
        monitor=monitor,
        cache_file=CACHE_FILE
    )
    
    scheduler.start()

if __name__ == "__main__":
    main()
