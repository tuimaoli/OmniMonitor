import threading
import json
import time
import os
import re
import socketserver
from urllib.parse import unquote
from http.server import BaseHTTPRequestHandler, HTTPServer
from web_template import HTML_TEMPLATE
import utils


class ThreadingHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True


class WebService:
    def __init__(self, config_manager, logger, fetcher, monitor, auth_mgr, port=8888):
        self.cfg_mgr = config_manager
        self.logger = logger
        self.fetcher = fetcher
        self.monitor = monitor
        self.auth_mgr = auth_mgr
        self.port = port
        self.server = None
        self.thread = None

        self.cached_quote = "Keep loving, keep going."
        self.last_quote_time = 0

        # 安全响应头 (每次响应统一注入)
        self.security_headers = [
            ('X-Content-Type-Options', 'nosniff'),
            ('X-Frame-Options', 'DENY'),
            ('X-XSS-Protection', '1; mode=block'),
            ('Referrer-Policy', 'strict-origin-when-cross-origin'),
            ('Cache-Control', 'no-store, no-cache, must-revalidate'),
            ('Permissions-Policy', 'camera=(), microphone=(), geolocation=()'),
        ]

    # ═══════════════════════════════════════
    #  启动
    # ═══════════════════════════════════════

    def start(self):
        handler = self._make_handler()
        try:
            self.server = ThreadingHTTPServer(('0.0.0.0', self.port), handler)
            self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
            self.thread.start()
            self.logger.info(f"🌐 Console started: http://0.0.0.0:{self.port} (Multi-threaded, Auth enabled)")
        except Exception as e:
            self.logger.error(f"Web Service Start Failed: {e}")

    # ═══════════════════════════════════════
    #  配置校验
    # ═══════════════════════════════════════

    def _validate_config_schema(self, config):
        if not isinstance(config, dict):
            return False, "Root must be dict"
        required = ['api_keys', 'pushplus_users', 'logging', 'cyclic_report']
        for k in required:
            if k not in config:
                return False, f"Missing {k}"
        return True, ""

    # ═══════════════════════════════════════
    #  处理器工厂 (闭包注入依赖)
    # ═══════════════════════════════════════

    def _make_handler(self):
        cfg_mgr = self.cfg_mgr
        fetcher = self.fetcher
        monitor = self.monitor
        auth_mgr = self.auth_mgr
        service_ref = self
        security_headers = self.security_headers

        PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
        GULU_DIR = os.path.join(PROJECT_ROOT, 'gulu')

        # 预编译正则：提取 Bearer token
        TOKEN_RE = re.compile(r'^Bearer\s+(.+)$', re.IGNORECASE)

        class ConfigHandler(BaseHTTPRequestHandler):
            def log_message(self, format, *args):
                return

            # ── 辅助方法 ──────────────────────────

            def _add_security_headers(self):
                for name, value in security_headers:
                    self.send_header(name, value)

            def _json(self, code, data, extra_headers=None):
                """快捷 JSON 响应"""
                self.send_response(code)
                self.send_header('Content-type', 'application/json; charset=utf-8')
                self._add_security_headers()
                if extra_headers:
                    for k, v in extra_headers:
                        self.send_header(k, v)
                self.end_headers()
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

            def _json_error(self, code, msg):
                self._json(code, {'error': msg})

            def _get_client_ip(self):
                """获取客户端真实 IP（考虑反向代理）"""
                forwarded = self.headers.get('X-Forwarded-For', '')
                if forwarded:
                    return forwarded.split(',')[0].strip()
                return self.client_address[0]

            def _extract_token(self):
                """从 Authorization 头提取 Bearer token"""
                auth = self.headers.get('Authorization', '')
                m = TOKEN_RE.match(auth)
                return m.group(1) if m else None

            def _check_auth(self, require_admin=False):
                """
                认证 + 频率限制检查。
                返回 (username, role) 成功；失败时已发送 401/403/429 并返回 None。
                """
                ip = self._get_client_ip()

                # 1. 频率限制
                if not auth_mgr.check_rate_limit(ip):
                    self._json_error(429, '请求过于频繁，请稍后再试')
                    return None

                # 2. Token 校验
                token = self._extract_token()
                if not token:
                    self._json_error(401, '未提供认证令牌')
                    return None

                result = auth_mgr.validate_token(token)
                if result is None:
                    self._json_error(401, '令牌无效或已过期，请重新登录')
                    return None

                username, role = result

                # 3. 热重载用户表
                cfg_users = cfg_mgr.data.get('users', [])
                if not any(u['username'] == username for u in cfg_users):
                    self._json_error(401, '用户不存在')
                    return None

                # 4. 管理员权限检查
                if require_admin and role != 'admin':
                    self._json_error(403, '权限不足，仅管理员可执行此操作')
                    return None

                return username, role

            # ═══════════════════════════════════════
            #  GET
            # ═══════════════════════════════════════

            def do_GET(self):
                try:
                    # 0. 安全头 — 所有响应统一注入 (send_response 之前调用有效)
                    #    do_GET 各分支手动调用 _add_security_headers

                    # 1. 主页 (无需认证，前端自己判断登录状态)
                    if self.path == '/':
                        self.send_response(200)
                        self.send_header('Content-type', 'text/html; charset=utf-8')
                        self._add_security_headers()
                        self.end_headers()
                        self.wfile.write(HTML_TEMPLATE.encode('utf-8'))

                    # 2. 静态图片 (无需认证)
                    elif self.path.startswith('/gulu/'):
                        request_path = unquote(self.path)
                        filename = os.path.basename(request_path)
                        file_path = os.path.join(GULU_DIR, filename)
                        if os.path.exists(file_path) and os.path.isfile(file_path):
                            self.send_response(200)
                            self.send_header('Content-type', 'image/png')
                            self.send_header('Cache-Control', 'public, max-age=86400')
                            self._add_security_headers()
                            self.end_headers()
                            with open(file_path, 'rb') as f:
                                self.wfile.write(f.read())
                        else:
                            self.send_error(404)

                    # 3. API: 认证检查 (页面加载时验证 token 有效性)
                    elif self.path == '/api/auth-check':
                        auth_result = self._check_auth()
                        if auth_result is None:
                            return
                        username, role = auth_result
                        self._json(200, {'username': username, 'role': role})

                    # 4. API: Config (需认证)
                    elif self.path == '/api/config':
                        auth_result = self._check_auth()
                        if auth_result is None:
                            return
                        # 返回配置时脱敏：隐藏密码哈希和 salt
                        safe_config = json.loads(json.dumps(cfg_mgr.data))
                        for u in safe_config.get('users', []):
                            u['password_hash'] = '***'
                            u['salt'] = '***'
                        safe_config.get('auth', {})['secret_key'] = '***'
                        self._json(200, safe_config)

                    # 5. API: Status 仪表盘 (需认证)
                    elif self.path == '/api/status':
                        auth_result = self._check_auth()
                        if auth_result is None:
                            return

                        if time.time() - service_ref.last_quote_time > 3600:
                            try:
                                q = fetcher.get_daily_quote(raw=True)
                                if q:
                                    service_ref.cached_quote = q
                                    service_ref.last_quote_time = time.time()
                            except:
                                pass

                        sys_status = {
                            'cpu_temp': monitor.get_cpu_temp(),
                            'disk_usage': monitor.get_disk_usage(),
                            'mem_usage': monitor.get_memory_usage(),
                        }

                        countdowns = []
                        config_evts = cfg_mgr.data.get('scheduled_push', {}).get('countdowns', [])
                        for e in config_evts:
                            days, _ = utils.calculate_days_left(e['date'], e.get('is_lunar', False))
                            if days is not None:
                                countdowns.append({
                                    'name': e['name'], 'date': e['date'], 'days': days,
                                    'is_lunar': e.get('is_lunar', False),
                                    'remind_days': e.get('remind_days', 7),
                                })
                        countdowns.sort(key=lambda x: x['days'])

                        resp = {
                            'quote': service_ref.cached_quote,
                            'system': sys_status,
                            'countdowns': countdowns,
                        }
                        self._json(200, resp)

                    else:
                        self.send_error(404)

                except (ConnectionResetError, BrokenPipeError):
                    pass
                except Exception as e:
                    service_ref.logger.error(f"Web GET Error: {e}")

            # ═══════════════════════════════════════
            #  POST
            # ═══════════════════════════════════════

            def do_POST(self):
                try:
                    # ── 登录 (无需认证，但有爆破保护) ──
                    if self.path == '/api/login':
                        self._handle_login()
                        return

                    # ── 登出 (需有效 token) ──
                    if self.path == '/api/logout':
                        auth_result = self._check_auth()
                        if auth_result is None:
                            return
                        # 登出只是告知前端清除 token，服务端无需额外操作
                        self._json(200, {'status': 'ok', 'message': '已登出'})
                        return

                    # ── 保存配置 (需管理员) ──
                    if self.path == '/api/save':
                        auth_result = self._check_auth(require_admin=True)
                        if auth_result is None:
                            return

                        length = int(self.headers.get('Content-Length', 0))
                        data = self.rfile.read(length)
                        new_config = json.loads(data.decode('utf-8'))

                        is_valid, error_msg = service_ref._validate_config_schema(new_config)
                        if not is_valid:
                            self._json(400, {'error': f'Invalid Config: {error_msg}'})
                            return

                        # 安全：保留现有 auth 和 users 配置，防止 Web 端覆盖
                        existing = cfg_mgr.data
                        for section in ('auth', 'users'):
                            if section in existing:
                                new_config[section] = existing[section]

                        cfg_mgr.save(new_config)
                        # 通知 auth_mgr 重载用户表
                        auth_mgr.reload_users()
                        self._json(200, {'status': 'ok'})
                        return

                    self.send_error(404)

                except Exception as e:
                    service_ref.logger.error(f"Config Save Exception: {e}")
                    self.send_response(500)
                    self.send_header('Content-type', 'application/json; charset=utf-8')
                    self.end_headers()
                    self.wfile.write(json.dumps({'error': str(e)}).encode('utf-8'))

            # ── 登录处理 ──────────────────────────

            def _handle_login(self):
                ip = self._get_client_ip()

                # 频率限制
                if not auth_mgr.check_rate_limit(ip):
                    self._json_error(429, '请求过于频繁，请稍后再试')
                    return

                # 爆破锁定检查
                if auth_mgr.is_locked_out(ip):
                    self._json_error(423, '登录尝试次数过多，账号已临时锁定，请15分钟后再试')
                    return

                # 读取请求体
                length = int(self.headers.get('Content-Length', 0))
                if length == 0 or length > 4096:
                    self._json_error(400, '请求体无效')
                    return

                try:
                    body = json.loads(self.rfile.read(length))
                    username = (body.get('username') or '').strip()
                    password = body.get('password') or ''
                except json.JSONDecodeError:
                    self._json_error(400, 'JSON 格式错误')
                    return

                if not username or not password:
                    remaining = auth_mgr.record_login_failure(ip)
                    self._json_error(400, '用户名和密码不能为空')
                    return

                # 验证用户
                user = auth_mgr.get_user(username)
                if user is None:
                    remaining = auth_mgr.record_login_failure(ip)
                    self._json_error(401, f'用户名或密码错误 (剩余尝试 {remaining} 次)')
                    return

                if not auth_mgr.verify_password(password, user['salt'], user['hash']):
                    remaining = auth_mgr.record_login_failure(ip)
                    self._json_error(401, f'用户名或密码错误 (剩余尝试 {remaining} 次)')
                    return

                # 成功
                auth_mgr.reset_failures(ip)
                token = auth_mgr.generate_token(username, user['role'])
                self._json(200, {
                    'token': token,
                    'role': user['role'],
                    'username': username,
                    'expires_in': auth_mgr.token_expire_sec,
                })
                if service_ref.logger:
                    service_ref.logger.info(f"✅ 用户 {username} ({user['role']}) 登录成功 (IP: {ip})")

        return ConfigHandler
