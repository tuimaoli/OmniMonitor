import urllib.request
import urllib.parse
import urllib.error
import json
import gzip
import time
import socket

class DataFetcher:
    def __init__(self, config, logger=None):
        self.cfg = config
        self.keys = config['api_keys']
        self.logger = logger
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept-Encoding": "gzip, deflate",
            "Accept": "*/*"
        }

    def _log(self, level, msg):
        if self.logger: getattr(self.logger, level)(msg)

    def _request(self, url, headers=None, max_retries=1, delay=2):
        """
        通用JSON请求方法 (带重试机制)
        :param max_retries: 最大重试次数 (默认失败后重试1次)
        :param delay: 重试前的等待秒数
        """
        if not headers: headers = self.headers
        
        # 尝试次数 = 1次正常请求 + max_retries次重试
        for attempt in range(max_retries + 1):
            try:
                req = urllib.request.Request(url, headers=headers)
                # 设置合理的超时时间，防止卡死
                with urllib.request.urlopen(req, timeout=10) as f:
                    raw = f.read()
                    if f.headers.get('Content-Encoding') == 'gzip':
                        try: raw = gzip.decompress(raw)
                        except: pass
                    # 成功获取数据，直接返回
                    return json.loads(raw.decode('utf-8'))
            
            except (urllib.error.URLError, socket.timeout) as e:
                # 只有是网络相关错误时才重试
                if attempt < max_retries:
                    self._log('warning', f"请求失败，{delay}秒后重试 ({attempt + 1}/{max_retries}): {url[:30]}... 错误: {e}")
                    time.sleep(delay) # 延时等待
                    continue # 进入下一次循环
                else:
                    # 重试次数用尽，返回None
                    self._log('error', f"API请求最终失败 (已重试{max_retries}次): {e}")
                    return None
                    
            except json.JSONDecodeError:
                self._log('warning', f"API返回了非JSON数据: {url[:30]}...")
                return None
            except Exception as e:
                self._log('error', f"API请求发生未知异常: {e}")
                return None
        
        return None

    def get_daily_quote(self, raw=False):
        """每日一言"""
        res = self._request("https://v1.hitokoto.cn/?c=i&c=d&c=k")
        if res:
            if raw: return f"{res['hitokoto']} —— {res.get('from', '佚名')}"
            return f"{res['hitokoto']} <span style='font-size:12px;color:#888'>—— {res.get('from', '佚名')}</span>"
        return "保持热爱，奔赴山海。"

    def get_commute_full_report(self, start, end, city_name=None):
        key = self.keys['amap']
        rows = []
        td_style = "padding:6px 4px; border-bottom:1px solid #eee; text-align:center; font-size:13px;"
        link_style = "text-decoration:none; color:#007bff; font-weight:bold;"
        
        # 1. 驾车
        url_car = f"https://restapi.amap.com/v3/direction/driving?origin={start}&destination={end}&key={key}&strategy=0"
        res = self._request(url_car)
        if res and res.get('status') == '1' and res['route']['paths']:
            p = res['route']['paths'][0]
            minutes = int(p['duration']) // 60
            km = int(p['distance']) // 1000
            map_url = f"https://uri.amap.com/navigation?from={start},起点&to={end},终点&mode=car&policy=0&src=push_bot&coordinate=gaode&callnative=1"
            rows.append(f"<tr><td style='{td_style}'>🚗 驾车</td><td style='{td_style} color:#333'><b>{minutes}</b>分</td><td style='{td_style} color:#999'>{km}km</td><td style='{td_style}'><a href='{map_url}' style='{link_style}'>路线&gt;</a></td></tr>")

        # 2. 公交
        if city_name:
            c_enc = urllib.parse.quote(city_name)
            url_bus = f"https://restapi.amap.com/v3/direction/transit/integrated?origin={start}&destination={end}&city={c_enc}&key={key}&strategy=0"
            res = self._request(url_bus)
            if res and res.get('status') == '1' and res['route']['transits']:
                p = res['route']['transits'][0]
                minutes = int(p['duration']) // 60
                km = int(p['distance']) // 1000
                map_url = f"https://uri.amap.com/navigation?from={start},起点&to={end},终点&mode=bus&city={c_enc}&src=push_bot&coordinate=gaode&callnative=1"
                rows.append(f"<tr><td style='{td_style}'>🚌 公交</td><td style='{td_style} color:#333'><b>{minutes}</b>分</td><td style='{td_style} color:#999'>{km}km</td><td style='{td_style}'><a href='{map_url}' style='{link_style}'>路线&gt;</a></td></tr>")

        # 3. 骑行
        url_bike = f"https://restapi.amap.com/v4/direction/bicycling?origin={start}&destination={end}&key={key}"
        res = self._request(url_bike)
        if res and res.get('data') and res['data']['paths']:
            p = res['data']['paths'][0]
            minutes = int(p['duration']) // 60
            km = int(p['distance']) // 1000
            map_url = f"https://uri.amap.com/navigation?from={start},起点&to={end},终点&mode=ride&src=push_bot&coordinate=gaode&callnative=1"
            rows.append(f"<tr><td style='{td_style}'>🚲 骑行</td><td style='{td_style} color:#333'><b>{minutes}</b>分</td><td style='{td_style} color:#999'>{km}km</td><td style='{td_style}'><a href='{map_url}' style='{link_style}'>路线&gt;</a></td></tr>")

        if not rows: return "暂时无法获取路况 (可能网络中断或Key无效)"
        
        return f"""
        <table style="width:100%; border-collapse:collapse; margin-top:5px;">
            <tbody>
                {"".join(rows)}
            </tbody>
        </table>
        """

    def get_weather_chart_url(self, hourly_data):
        try:
            times = []
            temps = []
            pops = [] 
            for item in hourly_data[:12]:
                times.append(item['fxTime'][11:13] + "时")
                temps.append(int(item['temp']))
                pops.append(int(item['pop']))
            config = {
                "type": "line",
                "data": {
                    "labels": times,
                    "datasets": [
                        {"type": "line", "label": "温度(°C)", "borderColor": "#ff9f40", "backgroundColor": "rgba(255, 159, 64, 0.2)", "fill": True, "data": temps, "yAxisID": "y-temp", "tension": 0.4},
                        {"type": "bar", "label": "降雨(%)", "backgroundColor": "rgba(54, 162, 235, 0.5)", "data": pops, "yAxisID": "y-pop"}
                    ]
                },
                "options": {
                    "title": {"display": False}, "legend": {"display": False},
                    "scales": {"yAxes": [{"id": "y-temp", "position": "left"}, {"id": "y-pop", "position": "right", "ticks": {"min": 0, "max": 100}, "gridLines": {"display": False}}]}
                }
            }
            return f"https://quickchart.io/chart?w=500&h=250&c={urllib.parse.quote(json.dumps(config))}"
        except: return ""

    def get_weather_now(self, location_code):
        url = f"https://devapi.qweather.com/v7/weather/now?location={location_code}&key={self.keys['qweather']}"
        res = self._request(url)
        if res and res['code'] == '200':
            return res['now']
        return None

    def get_weather_simple_html(self, locations):
        html = ""
        is_first = True
        has_data = False
        
        for loc in locations:
            url = f"https://devapi.qweather.com/v7/weather/24h?location={loc['code']}&key={self.keys['qweather']}"
            
            res = self._request(url, max_retries=2, delay=3)
            
            content = ""
            title_suffix = ""
            
            if res and res['code'] == '200':
                has_data = True
                hourly = res['hourly']
                now = hourly[0]
                chart_url = self.get_weather_chart_url(hourly)
                title_suffix = f"{now['text']} {now['temp']}°C"
                content = f"""
                <div style="padding:10px; border:1px solid #eee; border-top:none; border-radius:0 0 5px 5px;">
                    <p style="margin:5px 0; font-size:12px; color:#666">
                        当前: {now['text']} {now['temp']}°C | 风向: {now['windDir']} | 湿度: {now['humidity']}%
                    </p>
                    <img src="{chart_url}" style="width:100%; border-radius:5px; margin-top:5px;">
                </div>
                """
            else:
                title_suffix = "获取失败"
                content = "<p style='padding:10px; color:#999'>暂无数据 (网络异常或服务不可用)</p>"

            open_attr = "open" if is_first else ""
            html += f"""
            <details {open_attr} style="margin-bottom:8px; border:1px solid #ddd; border-radius:5px;">
                <summary style="background:#f5f5f5; padding:8px; cursor:pointer; font-weight:bold; outline:none; list-style:none;">
                    📍 {loc['name']} <span style="font-weight:normal; font-size:12px; float:right; color:#333;">{title_suffix}</span>
                </summary>
                {content}
            </details>
            """
            is_first = False
        
        if not has_data and html == "": return "暂无天气数据"
        return html

    def get_gold_price(self):
        # 黄金价格接口有时不稳定，也可以增加 retry=2
        try:
            ts = int(time.time() * 1000)
            url = f"https://api.jijinhao.com/sQuoteCenter/realTime.htm?code=JO_92233&isCalc=true&_={ts}"
            headers = self.headers.copy()
            headers["Referer"] = "https://quote.cngold.org/"
            
            # 这里也可以使用 _request 方法来简化，但由于解析逻辑特殊，保留原逻辑或稍微改造
            # 为了简单起见，这里仅演示核心 Weather/Request 部分的改动，保留原 Gold 逻辑
            # 如果想让 Gold 也支持重试，可以直接在 loop 中包裹这里的逻辑
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as f:
                raw = f.read()
                if f.headers.get('Content-Encoding') == 'gzip': raw = gzip.decompress(raw)
                content = raw.decode('utf-8', errors='ignore')
                if "quote_json" in content:
                    start, end = content.find('{'), content.rfind('}') + 1
                    data = json.loads(content[start:end])
                    if "JO_92233" in data: return float(data["JO_92233"]["q63"])
                if "hq_str" in content:
                    items = content[content.find('"')+1 : content.rfind('"')].split(',')
                    if len(items) > 3: return float(items[3])
        except Exception as e: 
            pass
        return None

    def get_bilibili_latest(self, uid):
        url = f"https://api.bilibili.com/x/space/arc/search?mid={uid}&ps=1&tid=0&pn=1&order=pubdate"
        res = self._request(url)
        if res and res.get('code') == 0:
            vlist = res.get('data', {}).get('list', {}).get('vlist', [])
            if vlist: return vlist[0]
        return None