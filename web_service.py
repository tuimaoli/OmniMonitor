import threading
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer
from web_template import HTML_TEMPLATE
import utils

class WebService:
    def __init__(self, config_manager, logger, fetcher, monitor, port=8888):
        self.cfg_mgr = config_manager
        self.logger = logger
        self.fetcher = fetcher
        self.monitor = monitor
        self.port = port
        self.server = None
        self.thread = None
        
        # 缓存一言，防止前端轮询导致API超限
        self.cached_quote = "Keep loving, keep going."
        self.last_quote_time = 0

    def start(self):
        handler = self._make_handler()
        try:
            self.server = HTTPServer(('0.0.0.0', self.port), handler)
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            self.logger.info(f"🌐 Console started: http://0.0.0.0:{self.port}")
        except Exception as e:
            self.logger.error(f"Web Service Start Failed: {e}")

    def _validate_config_schema(self, config):
        """
        后端核心防线：Schema 校验
        返回: (is_valid, error_message)
        """
        if not isinstance(config, dict):
            return False, "Root element must be a dictionary"

        # 1. 必填顶层 Key 检查
        required_keys = [
            'api_keys', 'pushplus_users', 'logging', 
            'cyclic_report', 'active_alert', 'scheduled_push'
        ]
        for k in required_keys:
            if k not in config:
                return False, f"Missing required top-level key: {k}"

        # 2. 关键类型检查
        # PushPlus Users 必须是列表
        if not isinstance(config.get('pushplus_users'), list):
            return False, "'pushplus_users' must be a list"
        
        # 验证 pushplus_users 内部结构
        for user in config['pushplus_users']:
            if not isinstance(user, dict) or 'token' not in user:
                return False, "Invalid item in 'pushplus_users': missing 'token'"

        # API Keys 必须是字典
        if not isinstance(config.get('api_keys'), dict):
            return False, "'api_keys' must be a dictionary"

        # Cyclic Report 检查
        if not isinstance(config.get('cyclic_report'), dict):
            return False, "'cyclic_report' must be a dictionary"
        
        # Locations 必须是列表
        if not isinstance(config['cyclic_report'].get('locations'), list):
            return False, "'cyclic_report.locations' must be a list"

        # 3. 可以在这里添加更深度的数值范围检查
        # 例如 retention_days 不能是负数
        if config.get('logging', {}).get('retention_days', 0) < 0:
            return False, "Retention days cannot be negative"

        return True, ""

    def _make_handler(self):
        cfg_mgr = self.cfg_mgr
        fetcher = self.fetcher
        monitor = self.monitor
        # 引用 self 以访问验证方法和缓存
        service_ref = self
        
        class ConfigHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                if self.path == '/':
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(HTML_TEMPLATE.encode('utf-8'))
                
                elif self.path == '/api/config':
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json; charset=utf-8')
                    self.end_headers()
                    json_str = json.dumps(cfg_mgr.data, ensure_ascii=False)
                    self.wfile.write(json_str.encode('utf-8'))

                elif self.path == '/api/status':
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json; charset=utf-8')
                    self.end_headers()
                    
                    # 1. Quote Caching
                    if time.time() - service_ref.last_quote_time > 3600:
                        try: 
                            q = fetcher.get_daily_quote(raw=True)
                            if q: 
                                service_ref.cached_quote = q
                                service_ref.last_quote_time = time.time()
                        except: pass
                    
                    # 2. System Status
                    sys_status = {
                        "cpu_temp": monitor.get_cpu_temp(),
                        "disk_usage": monitor.get_disk_usage(),
                        "mem_usage": monitor.get_memory_usage()
                    }
                    
                    # 3. Countdowns
                    countdowns = []
                    config_evts = cfg_mgr.data.get('scheduled_push', {}).get('countdowns', [])
                    for e in config_evts:
                        days, target_dt = utils.calculate_days_left(e['date'], e.get('is_lunar', False))
                        if days is not None:
                            countdowns.append({
                                "name": e['name'],
                                "date": e['date'],
                                "days": days,
                                "is_lunar": e.get('is_lunar', False),
                                "remind_days": e.get('remind_days', 7)
                            })
                    countdowns.sort(key=lambda x: x['days'])

                    resp = {
                        "quote": service_ref.cached_quote,
                        "system": sys_status,
                        "countdowns": countdowns,
                        "timestamp": time.time()
                    }
                    self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))
                
                else:
                    self.send_error(404)

            def do_POST(self):
                if self.path == '/api/save':
                    length = int(self.headers['Content-Length'])
                    data = self.rfile.read(length)
                    try:
                        # 1. 安全解析 JSON
                        new_config = json.loads(data.decode('utf-8'))
                        
                        # 2. Schema 完整性校验
                        is_valid, error_msg = service_ref._validate_config_schema(new_config)
                        
                        if not is_valid:
                            self.send_response(400) # Bad Request
                            self.end_headers()
                            self.wfile.write(json.dumps({"error": f"Invalid Config: {error_msg}"}).encode('utf-8'))
                            service_ref.logger.warning(f"Config save rejected: {error_msg}")
                            return

                        # 3. 调用管理器的保存 (这里假设管理器内部会处理原子写入)
                        # 如果你有 config_manager.py 的权限，建议在 cfg_mgr.save() 内部实现 write_temp -> rename 的逻辑
                        cfg_mgr.save(new_config)
                        
                        self.send_response(200)
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))
                        
                    except json.JSONDecodeError:
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": "Invalid JSON syntax"}).encode('utf-8'))
                    except Exception as e:
                        service_ref.logger.error(f"Config Save Exception: {e}")
                        self.send_response(500)
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        
        return ConfigHandler
