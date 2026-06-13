"""
OmniMonitor 认证与安全模块
- 密码加盐哈希 (SHA-256)
- HMAC Token 签发/校验 (含过期)
- IP 级防暴力破解锁定
- 简易频率限制
"""

from __future__ import annotations

import hashlib
import hmac
import os
import time
import base64
import json
from collections import defaultdict
from threading import Lock


class AuthManager:
    def __init__(self, config, logger=None):
        """
        :param config: 配置字典 (包含 auth 和 users 段)
        :param logger: 可选日志器
        """
        self.cfg = config
        self.logger = logger
        self._lock = Lock()

        # --- 从配置读取参数 ---
        auth_cfg = config.get('auth', {})
        self.secret_key = auth_cfg.get('secret_key', self._rand_hex(32)).encode('utf-8')
        self.token_expire_sec = auth_cfg.get('token_expire_hours', 24) * 3600
        self.max_attempts = auth_cfg.get('max_login_attempts', 5)
        self.lockout_sec = auth_cfg.get('lockout_minutes', 15) * 60

        # --- 频率限制 (API 级别) ---
        self.rate_window_sec = 60          # 窗口 60 秒
        self.rate_max_requests = 60        # 每个 IP 每分钟最多 60 次请求
        self.rate_records: dict[str, list[float]] = defaultdict(list)

        # --- 爆破锁定状态: {ip: (fail_count, first_fail_ts, locked_until_ts)} ---
        self.failures: dict[str, tuple[int, float, float]] = {}

        # --- 用户表: {username: {hash, salt, role}} ---
        self.users: dict[str, dict] = {}
        self._load_users()

    # ═══════════════════════════════════════════════════
    #  密码
    # ═══════════════════════════════════════════════════

    @staticmethod
    def _rand_hex(n: int) -> str:
        return os.urandom(n).hex()

    def hash_password(self, password: str, salt: str = None) -> tuple[str, str]:
        """返回 (hash_hex, salt_hex)"""
        if salt is None:
            salt = self._rand_hex(32)
        h = hashlib.sha256((salt + password).encode('utf-8')).hexdigest()
        return h, salt

    def verify_password(self, password: str, salt: str, stored_hash: str) -> bool:
        """验证密码是否匹配"""
        h, _ = self.hash_password(password, salt)
        return hmac.compare_digest(h, stored_hash)

    # ═══════════════════════════════════════════════════
    #  用户
    # ═══════════════════════════════════════════════════

    def _load_users(self):
        """从配置中加载用户表"""
        for u in self.cfg.get('users', []):
            self.users[u['username']] = {
                'hash': u['password_hash'],
                'salt': u['salt'],
                'role': u.get('role', 'guest'),
            }

    def reload_users(self):
        """热重载时调用"""
        self.users.clear()
        self._load_users()

    def get_user(self, username: str) -> dict | None:
        return self.users.get(username)

    # ═══════════════════════════════════════════════════
    #  Token (HMAC-SHA256)
    # ═══════════════════════════════════════════════════

    def generate_token(self, username: str, role: str) -> str:
        """
        生成 token: base64( payload_json + "." + hmac_hex )
        payload = {"u":"admin","r":"admin","exp":1738000000}
        """
        exp = int(time.time()) + self.token_expire_sec
        payload = json.dumps({"u": username, "r": role, "exp": exp}, separators=(',', ':'))
        payload_b64 = base64.urlsafe_b64encode(payload.encode('utf-8')).decode('utf-8').rstrip('=')
        sig = hmac.new(self.secret_key, payload_b64.encode('utf-8'), hashlib.sha256).hexdigest()
        return f"{payload_b64}.{sig}"

    def validate_token(self, token: str) -> tuple[str, str] | None:
        """
        校验 token，返回 (username, role) 或 None
        """
        if not token or '.' not in token:
            return None
        try:
            payload_b64, sig = token.rsplit('.', 1)
            # 签名校验
            expected_sig = hmac.new(self.secret_key, payload_b64.encode('utf-8'), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(expected_sig, sig):
                return None
            # 解码 payload (补齐 padding)
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += '=' * padding
            payload = json.loads(base64.urlsafe_b64decode(payload_b64))
            # 过期检查
            if payload.get('exp', 0) < time.time():
                return None
            return payload.get('u'), payload.get('r')
        except Exception:
            return None

    # ═══════════════════════════════════════════════════
    #  防暴力破解 (IP 级)
    # ═══════════════════════════════════════════════════

    def _cleanup_failures(self):
        """清理已过锁定期的记录"""
        now = time.time()
        expired = [ip for ip, (_, _, locked_until) in self.failures.items() if locked_until < now]
        for ip in expired:
            del self.failures[ip]

    def is_locked_out(self, ip: str) -> bool:
        """检查 IP 是否被暂时锁定"""
        with self._lock:
            self._cleanup_failures()
            if ip in self.failures:
                _, _, locked_until = self.failures[ip]
                if time.time() < locked_until:
                    return True
            return False

    def record_login_failure(self, ip: str) -> int:
        """
        记录一次登录失败，返回剩余尝试次数（0 表示已锁定）
        """
        with self._lock:
            self._cleanup_failures()
            now = time.time()
            if ip in self.failures:
                count, first_ts, locked_until = self.failures[ip]
                if now < locked_until:
                    return 0  # 仍在锁定中
                # 锁定期已过，重置计数
                if now - first_ts > self.lockout_sec:
                    count = 0
                    first_ts = now
                count += 1
            else:
                count = 1
                first_ts = now

            if count >= self.max_attempts:
                locked_until = now + self.lockout_sec
                self.failures[ip] = (count, first_ts, locked_until)
                if self.logger:
                    self.logger.warning(f"🔒 IP {ip} 登录失败 {count} 次，已锁定 {self.lockout_sec // 60} 分钟")
                return 0
            else:
                self.failures[ip] = (count, first_ts, 0)
                remaining = self.max_attempts - count
                return remaining

    def reset_failures(self, ip: str):
        """登录成功后清除失败记录"""
        with self._lock:
            self.failures.pop(ip, None)

    # ═══════════════════════════════════════════════════
    #  频率限制 (API 级别)
    # ═══════════════════════════════════════════════════

    def check_rate_limit(self, ip: str) -> bool:
        """
        检查 IP 是否超出频率限制。
        返回 True 表示允许通过，False 表示被限。
        """
        now = time.time()
        with self._lock:
            records = self.rate_records[ip]
            # 移除窗口外的记录
            cutoff = now - self.rate_window_sec
            while records and records[0] < cutoff:
                records.pop(0)
            if len(records) >= self.rate_max_requests:
                return False
            records.append(now)
            return True

    # ═══════════════════════════════════════════════════
    #  默认用户初始化
    # ═══════════════════════════════════════════════════

    @staticmethod
    def create_default_users_config():
        """返回默认的 users + auth 配置段 (用于首次启动自动生成)"""
        # 默认密码: admin / guest
        mgr = AuthManager.__new__(AuthManager)
        mgr.secret_key = os.urandom(32).hex().encode('utf-8')
        admin_hash, admin_salt = mgr.hash_password('admin123')
        guest_hash, guest_salt = mgr.hash_password('guest123')

        return {
            'auth': {
                'secret_key': mgr.secret_key.decode('utf-8'),
                'token_expire_hours': 24,
                'max_login_attempts': 5,
                'lockout_minutes': 15,
            },
            'users': [
                {
                    'username': 'admin',
                    'password_hash': admin_hash,
                    'salt': admin_salt,
                    'role': 'admin',
                },
                {
                    'username': 'guest',
                    'password_hash': guest_hash,
                    'salt': guest_salt,
                    'role': 'guest',
                },
            ],
        }
