import os
import time
import re
from collections import deque

class SystemMonitor:
    def __init__(self, logger=None):
        self.logger = logger
        self.hisilicon_pattern = re.compile(r'temperature\s*=\s*(\d+)')
        
        # 内存采样 (用于计算5分钟平均值)
        self.mem_samples = []
        
        # 历史趋势数据 (保留最近60个点，约1小时数据)
        self.history = {
            'cpu': deque(maxlen=60),
            'mem': deque(maxlen=60),
            'disk': deque(maxlen=60)
        }

    def log(self, msg):
        if self.logger: self.logger.info(msg)

    def _record_history(self, key, value):
        """记录历史数据用于前端绘图"""
        if value is not None:
            self.history[key].append(value)

    def get_cpu_temp(self):
        """获取CPU温度并记录历史"""
        temp = 0
        try:
            # 1. 海思芯片
            hisilicon_path = "/proc/msp/pm_cpu"
            if os.path.exists(hisilicon_path):
                with open(hisilicon_path, "r") as f:
                    match = self.hisilicon_pattern.search(f.read())
                    if match: temp = float(match.group(1))
            else:
                # 2. 常规 Linux
                paths = [
                    "/sys/class/thermal/thermal_zone0/temp",
                    "/sys/class/hwmon/hwmon0/temp1_input"
                ]
                for p in paths:
                    if os.path.exists(p):
                        with open(p, "r") as f:
                            val = int(f.read().strip())
                            temp = val / 1000.0 if val > 200 else float(val)
                            break
        except Exception as e:
            if self.logger: self.logger.error(f"温度读取出错: {e}")
        
        self._record_history('cpu', temp)
        return temp

    def get_disk_usage(self):
        """获取磁盘占用并记录历史"""
        usage = 0
        try:
            st = os.statvfs('/')
            total = st.f_blocks * st.f_frsize
            if total > 0:
                usage = round(100 * (total - st.f_bfree * st.f_frsize) / total, 1)
        except: pass
        
        self._record_history('disk', usage)
        return usage

    def get_memory_usage(self):
        """获取内存(5分钟平均)并记录历史"""
        current_usage = 0
        try:
            if os.path.exists("/proc/meminfo"):
                mem_info = {}
                with open("/proc/meminfo", "r") as f:
                    for line in f:
                        parts = line.split(':')
                        if len(parts) == 2:
                            mem_info[parts[0].strip()] = int(parts[1].split()[0])
                        if 'MemTotal' in mem_info and 'MemAvailable' in mem_info:
                            break
                
                total = mem_info.get('MemTotal', 0)
                avail = mem_info.get('MemAvailable', 0)
                if total > 0:
                    current_usage = 100 * (total - avail) / total

            # 滑动平均逻辑
            now = time.time()
            self.mem_samples.append((now, current_usage))
            cutoff = now - 300
            self.mem_samples = [(t, v) for t, v in self.mem_samples if t > cutoff]
            
            avg_val = 0
            if self.mem_samples:
                avg_val = sum(v for t, v in self.mem_samples) / len(self.mem_samples)
            
            avg_val = round(avg_val, 1)
            self._record_history('mem', avg_val)
            return avg_val

        except Exception as e:
            if self.logger: self.logger.error(f"内存读取出错: {e}")
            return 0
    
    def get_history(self):
        """返回列表格式的历史数据"""
        return {
            'cpu': list(self.history['cpu']),
            'mem': list(self.history['mem']),
            'disk': list(self.history['disk'])
        }
