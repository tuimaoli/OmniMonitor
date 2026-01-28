from datetime import datetime, date, time as dtime
import sys
import os

# 自定义库路径 (如果在特定目录下)
custom_lib_path = '/home/ubuntu/pyProject/ENV/zhdate'
if os.path.exists(custom_lib_path):
    sys.path.insert(0, custom_lib_path)

# 尝试导入农历库
try:
    from zhdate import ZhDate
    HAS_ZHDATE = True
except ImportError:
    HAS_ZHDATE = False
    print(f"提示: 未找到 zhdate 库，农历功能将不可用")

def calculate_days_left(target_str, is_lunar=False):
    """
    计算距离目标日期的天数
    修复了以下问题:
    1. 农历跨年计算 (例如当前1月，目标是农历12月)
    2. ZhDate 类型报错 (需传入 datetime 而非 date)
    3. 农历大小月问题 (设置30日但当月只有29天)
    """
    today = date.today()
    try:
        # 提取月和日 (格式 YYYY-MM-DD)
        _, m, d = map(int, target_str.split('-'))
    except:
        return None, None

    if is_lunar and HAS_ZHDATE:
        try:
            # === 修复点: 类型转换 ===
            # ZhDate.from_datetime 需要 datetime 对象
            now_datetime = datetime.combine(today, dtime.min)
            
            # 1. 获取当前农历年份
            today_lunar = ZhDate.from_datetime(now_datetime)
            curr_lunar_year = today_lunar.lunar_year
            
            # === 辅助函数: 安全获取阳历日期 ===
            def get_solar_safe(year, month, day):
                try:
                    return ZhDate(year, month, day).to_datetime().date()
                except:
                    # 如果报错(例如设置30日但该月只有29天)，尝试减一天
                    try:
                        return ZhDate(year, month, day - 1).to_datetime().date()
                    except:
                        return None

            # 2. 尝试计算"当前农历年"对应的阳历日期
            target_solar = get_solar_safe(curr_lunar_year, m, d)
            
            # 3. 如果计算失败或者日子已经过去了，计算"下一个农历年"
            if not target_solar or target_solar < today:
                target_solar = get_solar_safe(curr_lunar_year + 1, m, d)
            
            if target_solar:
                target_date = target_solar
            else:
                return 999, today # 极端错误容错
            
        except Exception as e: 
            print(f"农历计算错误: {e}")
            return 999, today
    else:
        # === 阳历处理 ===
        try:
            this_year_bday = date(today.year, m, d)
        except ValueError:
            # 处理2月29日 (平年没有则算到3月1日)
            this_year_bday = date(today.year, 3, 1)

        if this_year_bday < today:
            target_date = date(today.year + 1, m, d)
        else:
            target_date = this_year_bday

    days_left = (target_date - today).days
    return days_left, target_date

def get_countdown_html(countdowns):
    """生成推送用的倒数日表格 HTML"""
    rows = ""
    events = []
    
    for item in countdowns:
        days, target_date = calculate_days_left(item['date'], item.get('is_lunar', False))
        if days is not None:
            events.append({**item, "days": days, "target_dt": target_date})
    
    # 按剩余天数排序，最近的在前面
    events.sort(key=lambda x: x['days'])
    
    td_style = "padding:6px 8px; border-bottom:1px solid #eee; font-size:13px;"
    
    for e in events:
        days_str = "今天!" if e['days'] == 0 else f"{e['days']}天"
        # 临近日期标红 (小于等于 remind_days)
        color = "#e74c3c" if e['days'] <= e.get('remind_days', 7) else "#333"
        date_type = "<span style='color:#999;font-size:12px;margin-left:2px'>(农)</span>" if e.get('is_lunar') else ""
        
        # 显示目标日期的阳历月日
        target_str = e['target_dt'].strftime('%m-%d')
        
        rows += f"""
        <tr>
            <td style='{td_style} text-align:left;'>{e['name']}{date_type}</td>
            <td style='{td_style} color:#999; text-align:center;'>{target_str}</td>
            <td style='{td_style} color:{color}; font-weight:bold; text-align:right;'>{days_str}</td>
        </tr>
        """
    
    if not rows: return ""
    return f"""
    <table style="width:100%; border-collapse:collapse; margin-top:5px;">
        {rows}
    </table>
    """
