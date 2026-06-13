import time
import gc
from datetime import datetime, timedelta
import utils

class TaskScheduler:
    def __init__(self, config_mgr, logger, pusher, fetcher, monitor, cache_file, auth_mgr=None):
        self.cfg_mgr = config_mgr
        self.logger = logger
        self.pusher = pusher
        self.fetcher = fetcher
        self.monitor = monitor
        self.cache_file = cache_file
        self.auth_mgr = auth_mgr
        
        self.cache = self._load_cache()
        # 运行时状态记录
        self.ts_checks = {
            'server': 0, 'gold': 0, 'weather': 0, 
            'bilibili': 0, 'log_clean': 0,
            'log_flush': 0,        # 上次强制写盘时间戳
            'cyclic_interval': 0 
        }
        
        # 初始化读取冲刷间隔，默认 600 秒
        self._update_intervals()

    def _update_intervals(self):
        """从配置中更新各种间隔时长"""
        log_cfg = self.cfg_mgr.data.get('logging', {})
        self.flush_interval = log_cfg.get('flush_interval_seconds', 600)

    def _load_cache(self):
        import json
        import os
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except: pass
        return {}

    def _save_cache(self):
        import json
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(self.cache, f, ensure_ascii=False)

    def _check_cooldown(self, key, duration):
        last = self.cache.get(f"cd_{key}", 0)
        return (time.time() - last > duration)

    def _update_cooldown(self, key):
        self.cache[f"cd_{key}"] = time.time()
        self._save_cache()

    def _make_card(self, title, content, color="#d9534f"):
        return f"""
        <div style="border:1px solid #eee; border-radius:8px; box-shadow:0 2px 6px rgba(0,0,0,0.05); overflow:hidden; margin-bottom:15px;">
            <div style="background:{color}; color:white; padding:8px 12px; font-weight:bold; font-size:14px;">{title}</div>
            <div style="padding:12px; background:#fff; color:#333; font-size:14px; line-height:1.6;">{content}</div>
        </div>
        """

    def start(self):
        self.logger.info("🚀 任务调度器已启动")
        
        while True:
            try:
                now = datetime.now()
                ts_now = time.time()
                config = self.cfg_mgr.data

                # --- 0. 定时强制冲刷日志 (配置化间隔) ---
                if ts_now - self.ts_checks['log_flush'] > self.flush_interval:
                    self._flush_logs()
                    self.ts_checks['log_flush'] = ts_now

                # --- 1. 热重载检测 ---
                if self.cfg_mgr.check_hot_reload():
                    self.pusher.users = config['pushplus_users']
                    self.fetcher.cfg = config
                    self.fetcher.keys = config['api_keys']
                    self._update_intervals() # 重新加载间隔配置
                    if self.auth_mgr:
                        self.auth_mgr.reload_users()
                    self.logger.info(f"配置已重载，当前日志冲刷间隔: {self.flush_interval}s")

                # --- 2. 日志清理 ---
                if ts_now - self.ts_checks['log_clean'] > 86400:
                    # 可以在这里显式调用 LoggerManager 的清理方法
                    self.ts_checks['log_clean'] = ts_now

                # --- 3. 各种业务逻辑循环 ---
                self._run_cyclic_report(now, ts_now, config)
                self._run_active_alerts(ts_now, config)
                self._run_scheduled_push(now, config)

                time.sleep(5)
                gc.collect()

            except KeyboardInterrupt:
                self.logger.info("程序手动停止，正在冲刷日志并保存缓存...")
                self._flush_logs()
                self._save_cache()
                break
            except Exception as e:
                self.logger.error(f"调度循环异常: {e}")
                self._flush_logs() 
                time.sleep(30)

    def _flush_logs(self):
        """遍历并强制执行日志 Handler 的 flush 操作"""
        try:
            for handler in self.logger.handlers:
                if hasattr(handler, 'flush'):
                    handler.flush()
        except:
            pass

    def _run_cyclic_report(self, now, ts_now, config):
        cfg = config.get('cyclic_report', {})
        if not cfg.get('enable'): return

        should_run = False
        
        # 模式1: 整点对齐 (Align to Hour)
        if cfg.get('align_to_hour', True):
            hour_key = now.strftime("%Y-%m-%d-%H")
            if now.minute == 0 and self.cache.get('last_cyclic_key') != hour_key:
                should_run = True
                self.cache['last_cyclic_key'] = hour_key # 记录小时Key
        
        # 模式2: 间隔轮询 (Interval)
        else:
            interval = cfg.get('interval_minutes', 60) * 60
            if ts_now - self.ts_checks['cyclic_interval'] >= interval:
                should_run = True
                self.ts_checks['cyclic_interval'] = ts_now # 记录时间戳

        if should_run:
            self.logger.info("执行状态上报...")
            weather = self.fetcher.get_weather_simple_html(cfg['locations'])
            gold = self.fetcher.get_gold_price()
            d_usage = self.monitor.get_disk_usage()
            c_temp = self.monitor.get_cpu_temp()
            m_usage = self.monitor.get_memory_usage()

            html = f"""
            <div style="background:#f4f6f8; padding:15px; border-radius:8px;">
                <h3 style="margin-top:0; color:#2c3e50;">📊 状态看板</h3>
                {weather}
                <div style="margin-top:10px; padding-top:10px; border-top:1px dashed #ccc;">
                    <p style="margin:5px 0;">💰 <b>金价:</b> <span style="color:#d35400">{gold if gold else 'N/A'}</span></p>
                    <p style="margin:5px 0;">🖥️ <b>Sys:</b> 磁盘{d_usage}% | 内存{m_usage}% | 温度{c_temp}°C</p>
                </div>
                <p style="text-align:right; margin:0; font-size:12px; color:#999;">{now.strftime('%H:%M')}</p>
            </div>
            """
            self.pusher.send("⏰ 状态报告", html)
            self._save_cache()

    def _run_active_alerts(self, ts_now, config):
        cfg = config.get('active_alert', {})
        
        # A. Server
        srv = cfg.get('server', {})
        if ts_now - self.ts_checks['server'] >= srv.get('check_interval', 60):
            temp = self.monitor.get_cpu_temp()
            disk = self.monitor.get_disk_usage()
            mem = self.monitor.get_memory_usage()
            
            warns = []
            if temp > srv.get('cpu_temp_threshold', 75): warns.append(f"🔥 CPU温度: <b>{temp}°C</b>")
            if disk > srv.get('disk_usage_threshold', 90): warns.append(f"💾 磁盘满: <b>{disk}%</b>")
            
            if warns and self._check_cooldown('server', srv.get('alert_cooldown', 3600)):
                warns.append(f"🧠 内存(5m): {mem}%")
                self.logger.warning(f"服务器报警: {warns}")
                self.pusher.send("🔴 服务器报警", self._make_card("🚨 紧急", "<br>".join(warns)))
                self._update_cooldown('server')
            self.ts_checks['server'] = ts_now

        # B. Gold
        gold_cfg = cfg.get('gold', {})
        if ts_now - self.ts_checks['gold'] >= gold_cfg.get('check_interval', 600):
            price = self.fetcher.get_gold_price()
            if price:
                low, high = gold_cfg.get('low', 0), gold_cfg.get('high', 9999)
                if (price < low or price > high) and self._check_cooldown('gold', gold_cfg.get('alert_cooldown', 14400)):
                    self.logger.warning(f"金价越界: {price}")
                    self.pusher.send(f"⚠️ 金价: {price}", self._make_card("💰 价格提醒", f"当前: {price}", "#f39c12"))
                    self._update_cooldown('gold')
            self.ts_checks['gold'] = ts_now

        # C. Weather
        w_cfg = cfg.get('weather', {})
        if ts_now - self.ts_checks['weather'] >= w_cfg.get('check_interval', 1800):
            for loc in w_cfg.get('locations', []):
                w = self.fetcher.get_weather_now(loc['code'])
                if w:
                    is_bad = int(w['temp']) < w_cfg.get('temp_low', 0)
                    for kw in w_cfg.get('bad_weather_keywords', []):
                        if kw in w['text']: is_bad = True
                    
                    cd_key = f"weather_{loc['code']}"
                    if is_bad and self._check_cooldown(cd_key, w_cfg.get('alert_cooldown', 21600)):
                        self.logger.info(f"天气预警: {loc['name']}")
                        self.pusher.send(f"🌨️ {loc['name']}天气", self._make_card(f"{loc['name']}预警", f"{w['text']} {w['temp']}°C", "#3498db"))
                        self._update_cooldown(cd_key)
            self.ts_checks['weather'] = ts_now

        # D. Bilibili
        bili = cfg.get('bilibili', {})
        if ts_now - self.ts_checks['bilibili'] >= bili.get('check_interval', 1200):
            for up in bili.get('uids', []):
                v = self.fetcher.get_bilibili_latest(up['uid'])
                if v:
                    k = f"bili_{up['uid']}"
                    if v['bvid'] != self.cache.get(k):
                        self.logger.info(f"B站更新: {up['name']}")
                        html = self._make_card(f"{up['name']} 更新", f"{v['title']}<br><img src='{v['pic']}' style='width:100%'><br><a href='https://www.bilibili.com/video/{v['bvid']}'>观看</a>", "#fb7299")
                        self.pusher.send(f"📺 {up['name']}", html)
                        self.cache[k] = v['bvid']
                        self._save_cache()
            self.ts_checks['bilibili'] = ts_now

    def _run_scheduled_push(self, now, config):
        sch = config.get('scheduled_push', {})
        cm = sch.get('commute', {})
        today_str = now.strftime("%Y-%m-%d")

        if cm.get('enable'):
            # 早安
            t_am = datetime.strptime(f"{today_str} {cm['work_start']}", "%Y-%m-%d %H:%M") - timedelta(minutes=cm['lead_time_minutes'])
            if now >= t_am and now < (t_am + timedelta(hours=1)) and self.cache.get('last_am') != today_str:
                self._send_daily_report("☀️ 早安", True, config, "#007bff", today_str)
                self.cache['last_am'] = today_str
                self._save_cache()

            # 下班
            t_pm = datetime.strptime(f"{today_str} {cm['work_end']}", "%Y-%m-%d %H:%M") - timedelta(minutes=cm['lead_time_minutes'])
            if now >= t_pm and now < (t_pm + timedelta(hours=1)) and self.cache.get('last_pm') != today_str:
                self._send_daily_report("🌙 下班", False, config, "#6c757d", today_str)
                self.cache['last_pm'] = today_str
                self._save_cache()

        # 9点独立倒数日
        if now.hour == 9 and self.cache.get('last_evt') != today_str:
            self._check_independent_countdown(sch)
            self.cache['last_evt'] = today_str
            self._save_cache()

    def _send_daily_report(self, title, is_am, config, color, today_str):
        self.logger.info(f"生成 {title} 报告...")
        cm = config['scheduled_push']['commute']
        
        city = "郑州"
        try: city = config['cyclic_report']['locations'][0]['name']
        except: pass

        quote = self.fetcher.get_daily_quote()
        s, e = (cm['home_loc'], cm['work_loc']) if is_am else (cm['work_loc'], cm['home_loc'])
        traffic = self.fetcher.get_commute_full_report(s, e, city)
        weather = self.fetcher.get_weather_simple_html(config['cyclic_report']['locations'])
        gold = self.fetcher.get_gold_price()
        mem = self.monitor.get_memory_usage()
        disk = self.monitor.get_disk_usage()
        temp = self.monitor.get_cpu_temp()
        cd = utils.get_countdown_html(config['scheduled_push']['countdowns']) if is_am else ""

        html = f"""
        <div style="font-family:sans-serif;">
            <div style="background:{color}; color:white; padding:15px; border-radius:8px 8px 0 0;">
                <h2 style="margin:0;">{title}</h2>
                <p style="margin:5px 0 0; opacity:0.9;">{today_str}</p>
            </div>
            <div style="border:1px solid #eee; border-top:none; border-radius:0 0 8px 8px; padding:15px; background:#fff;">
                <div style="background:#f8f9fa; padding:10px; border-left:4px solid {color}; margin-bottom:15px; color:#555; font-style:italic;">{quote}</div>
                <h4 style="border-bottom:1px solid #eee; padding-bottom:5px;">🚦 路况</h4>
                <div style="margin-bottom:15px;">{traffic}</div>
                <h4 style="border-bottom:1px solid #eee; padding-bottom:5px;">🌍 环境</h4>
                <div style="margin-bottom:15px;">{weather}
                <div style="margin-top:8px; font-size:13px; color:#666;">💰 金价: {gold if gold else '-'} | 🖥️ 内存{mem}% 磁盘{disk}% {temp}°C</div></div>
                {cd}
            </div>
        </div>
        """
        self.pusher.send(f"{title}·全能日报", html)

    def _check_independent_countdown(self, sch_config):
        events = []
        for e in sch_config.get('countdowns', []):
            d, _ = utils.calculate_days_left(e['date'], e.get('is_lunar', False))
            if d is not None and d <= e.get('remind_days', 3):
                events.append(f"<li><b>{e['name']}</b> 还有 <span style='color:red;font-size:18px'>{d}</span> 天</li>")
        
        if events:
            self.logger.info("发送独立倒数日提醒")
            self.pusher.send("📅 日程提醒", self._make_card("倒数日", f"<ul>{''.join(events)}</ul>", "#9b59b6"))
