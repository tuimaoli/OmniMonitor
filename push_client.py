import http.client
import json
import gzip
import socket
from datetime import datetime

class PushPlusClient:
    def __init__(self, user_list, logger=None):
        self.users = user_list
        self.host = "www.pushplus.plus"
        self.logger = logger
        self.headers = {
            "Content-Type": "application/json",
            "Accept-Encoding": "gzip, deflate"
        }

    def _log(self, level, msg):
        if self.logger:
            getattr(self.logger, level)(msg)
        else:
            print(f"[{level.upper()}] {msg}")

    def _post(self, payload):
        conn = None
        try:
            # 设置超时时间 10秒，防止断网卡死
            conn = http.client.HTTPSConnection(self.host, timeout=10)
            conn.request("POST", "/send", json.dumps(payload), self.headers)
            res = conn.getresponse()
            raw = res.read()
            if res.getheader('Content-Encoding') == 'gzip':
                raw = gzip.decompress(raw)
            conn.close()
            return json.loads(raw.decode("utf-8"))
        except (socket.gaierror, socket.timeout, ConnectionError):
            # 捕获网络层面的错误 (DNS解析失败、超时、连接断开)
            raise ConnectionError("网络连接失败")
        except Exception as e:
            if conn: conn.close()
            raise e

    def send(self, title, content):
        """发送推送，如果失败则记录日志并忽略"""
        self._log('info', f"正在推送: {title}")
        
        success_count = 0
        for user in self.users:
            payload = {
                "token": user['token'],
                "title": title,
                "content": content,
                "template": "html",
                "channel": "wechat"
            }
            if user.get('topic'): payload['topic'] = user['topic']
            
            try:
                res = self._post(payload)
                if res.get('code') == 200:
                    success_count += 1
                else:
                    self._log('warning', f"PushPlus响应错误: {res.get('msg')}")
            except ConnectionError:
                # 断网场景：详略得当，只记录一行警告，不打印堆栈
                self._log('warning', f"发送失败(网络中断): 无法连接到 {self.host}，已忽略本次推送。")
            except Exception as e:
                self._log('error', f"发送异常: {e}")

        if success_count > 0:
            self._log('info', f"推送完成 (成功发送 {success_count} 个用户)")
