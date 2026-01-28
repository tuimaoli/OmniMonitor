import threading
import json
import time
import os
from urllib.parse import unquote
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
        
        # 缓存一言
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
        if not isinstance(config, dict): return False, "Root must be dict"
        required = ['api_keys', 'pushplus_users', 'logging', 'cyclic_report']
        for k in required:
            if k not in config: return False, f"Missing {k}"
        return True, ""

    def _make_handler(self):
        cfg_mgr = self.cfg_mgr
        fetcher = self.fetcher
        monitor = self.monitor
        service_ref = self
        
        # --- 关键修复：获取项目根目录的绝对路径 ---
        # 无论在哪里运行脚本，都能准确定位到 gulu 文件夹
        PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
        GULU_DIR = os.path.join(PROJECT_ROOT, 'gulu')
        
        class ConfigHandler(BaseHTTPRequestHandler):
            def do_GET(self):
                # 1. 主页
                if self.path == '/':
                    self.send_response(200)
                    self.send_header('Content-type', 'text/html; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(HTML_TEMPLATE.encode('utf-8'))
                
                # 2. 静态图片服务 (强制定位到 gulu 文件夹)
                elif self.path.startswith('/gulu/'):
                    try:
                        # 1. 解码 URL (处理中文名)
                        request_path = unquote(self.path)
                        
                        # 2. 提取文件名 (防止目录遍历攻击)
                        filename = os.path.basename(request_path)
                        
                        # 3. 拼接绝对路径
                        file_path = os.path.join(GULU_DIR, filename)
                        
                        # 4. 检查文件是否存在
                        if os.path.exists(file_path) and os.path.isfile(file_path):
                            self.send_response(200)
                            self.send_header('Content-type', 'image/png')
                            self.send_header('Cache-Control', 'public, max-age=86400') # 缓存一天
                            self.end_headers()
                            with open(file_path, 'rb') as f:
                                self.wfile.write(f.read())
                        else:
                            service_ref.logger.warning(f"404 Image Not Found: {file_path}")
                            self.send_error(404, "File Not Found")
                            
                    except Exception as e:
                        service_ref.logger.error(f"Image Serve Error: {e}")
                        self.send_error(500)

                # 3. API: Config
                elif self.path == '/api/config':
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json; charset=utf-8')
                    self.end_headers()
                    json_str = json.dumps(cfg_mgr.data, ensure_ascii=False)
                    self.wfile.write(json_str.encode('utf-8'))

                # 4. API: Status
                elif self.path == '/api/status':
                    self.send_response(200)
                    self.send_header('Content-type', 'application/json; charset=utf-8')
                    self.end_headers()
                    
                    if time.time() - service_ref.last_quote_time > 3600:
                        try: 
                            q = fetcher.get_daily_quote(raw=True)
                            if q: service_ref.cached_quote = q; service_ref.last_quote_time = time.time()
                        except: pass
                    
                    sys_status = {
                        "cpu_temp": monitor.get_cpu_temp(),
                        "disk_usage": monitor.get_disk_usage(),
                        "mem_usage": monitor.get_memory_usage()
                    }
                    
                    countdowns = []
                    config_evts = cfg_mgr.data.get('scheduled_push', {}).get('countdowns', [])
                    for e in config_evts:
                        days, _ = utils.calculate_days_left(e['date'], e.get('is_lunar', False))
                        if days is not None:
                            countdowns.append({
                                "name": e['name'], "date": e['date'], "days": days,
                                "is_lunar": e.get('is_lunar', False), "remind_days": e.get('remind_days', 7)
                            })
                    countdowns.sort(key=lambda x: x['days'])

                    resp = { "quote": service_ref.cached_quote, "system": sys_status, "countdowns": countdowns }
                    self.wfile.write(json.dumps(resp, ensure_ascii=False).encode('utf-8'))
                
                else:
                    self.send_error(404)

            def do_POST(self):
                if self.path == '/api/save':
                    length = int(self.headers['Content-Length'])
                    data = self.rfile.read(length)
                    try:
                        new_config = json.loads(data.decode('utf-8'))
                        is_valid, error_msg = service_ref._validate_config_schema(new_config)
                        
                        if not is_valid:
                            self.send_response(400)
                            self.end_headers()
                            self.wfile.write(json.dumps({"error": f"Invalid Config: {error_msg}"}).encode('utf-8'))
                            return

                        cfg_mgr.save(new_config)
                        self.send_response(200)
                        self.end_headers()
                        self.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))
                        
                    except Exception as e:
                        service_ref.logger.error(f"Config Save Exception: {e}")
                        self.send_response(500)
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
        
        return ConfigHandler
