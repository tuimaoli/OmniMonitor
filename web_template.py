HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no, viewport-fit=cover">
    <title>监控推送控制台</title>
    <style>
        :root {
            --primary: #6366f1;
            --safe-top: env(safe-area-inset-top);
            --safe-bottom: env(safe-area-inset-bottom);
            
            --glass-bg: rgba(255, 255, 255, 0.75);
            --glass-border: rgba(255, 255, 255, 0.8);
            --glass-shadow: 0 12px 40px -10px rgba(0, 0, 0, 0.08);
            
            --text-main: #334155;
            --text-sub: #64748b;
            --radius-box: 24px;
            --radius-btn: 12px;
        }

        * { box-sizing: border-box; outline: none; -webkit-tap-highlight-color: transparent; }
        
        body {
            margin: 0; padding: 0;
            font-family: -apple-system, BlinkMacSystemFont, "SF Pro Display", "Segoe UI", Roboto, sans-serif;
            color: var(--text-main);
            height: 100vh;
            overscroll-behavior: none;
            display: flex; justify-content: center; align-items: center;
            overflow: hidden;
            user-select: none;
            cursor: default;
            background-color: #f0f2f5;
            background-image: 
                radial-gradient(at 10% 10%, rgba(199, 210, 254, 0.5) 0px, transparent 50%),
                radial-gradient(at 90% 10%, rgba(253, 230, 138, 0.4) 0px, transparent 50%),
                radial-gradient(at 90% 90%, rgba(165, 243, 252, 0.5) 0px, transparent 50%),
                radial-gradient(at 10% 90%, rgba(251, 207, 232, 0.4) 0px, transparent 50%);
        }
        
        /* Ambient Background Animation */
        body::before {
            content: ''; position: absolute; top: 10%; left: 10%; width: 60vw; height: 60vw;
            background: radial-gradient(circle, rgba(99, 102, 241, 0.12) 0%, transparent 70%);
            animation: float1 20s infinite ease-in-out alternate;
            pointer-events: none; z-index: -1; will-change: transform;
        }
        body::after {
            content: ''; position: absolute; bottom: 10%; right: 10%; width: 50vw; height: 50vw;
            background: radial-gradient(circle, rgba(236, 72, 153, 0.1) 0%, transparent 70%);
            animation: float2 25s infinite ease-in-out alternate;
            pointer-events: none; z-index: -1; will-change: transform;
        }
        @keyframes float1 { from { transform: translate(0,0); } to { transform: translate(40px, 30px); } }
        @keyframes float2 { from { transform: translate(0,0); } to { transform: translate(-30px, -40px); } }
        
        /* App Container */
        .app-container {
            width: 96%; max-width: 1100px; height: 90vh;
            background: var(--glass-bg);
            backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
            border-radius: var(--radius-box);
            border: 1px solid var(--glass-border);
            box-shadow: var(--glass-shadow);
            display: flex; flex-direction: column;
            overflow: hidden;
            animation: popIn 0.6s cubic-bezier(0.2, 0.8, 0.2, 1);
            position: relative;
        }

        /* Header */
        .header {
            padding: 12px 28px;
            display: flex; justify-content: space-between; align-items: center;
            background: rgba(255,255,255,0.4);
            border-bottom: 1px solid rgba(0,0,0,0.03);
            flex-shrink: 0; z-index: 20;
            transition: all 0.3s ease;
        }
        .brand { font-size: 15px; font-weight: 700; color: #1e293b; display: flex; align-items: center; gap: 8px; }
        .pulse-dot { width: 8px; height: 8px; background: #34d399; border-radius: 50%; box-shadow: 0 0 0 2px rgba(52, 211, 153, 0.2); }
        
        /* Mobile Dynamic Title */
        .page-title {
            font-size: 14px; font-weight: 600; color: var(--primary);
            background: rgba(99, 102, 241, 0.08); padding: 4px 12px; border-radius: 20px;
            opacity: 0.8; transition: all 0.3s;
        }

        /* Layout */
        .content-wrapper { flex: 1; display: flex; overflow: hidden; position: relative; }
        
        /* Sidebar (Desktop) */
        .sidebar {
            width: 200px; padding: 20px 12px;
            background: rgba(255,255,255,0.3);
            border-right: 1px solid rgba(0,0,0,0.03);
            display: flex; flex-direction: column; gap: 4px;
            flex-shrink: 0;
        }
        .nav-btn {
            padding: 10px 12px; border-radius: var(--radius-btn);
            border: none; background: transparent;
            color: var(--text-sub); font-weight: 600; text-align: left; font-size: 13px;
            cursor: pointer; transition: all 0.2s;
            display: flex; align-items: center; gap: 10px;
            white-space: nowrap;
        }
        .nav-btn:hover { background: rgba(255,255,255,0.6); color: var(--primary); transform: translateX(2px); }
        .nav-btn.active { background: #fff; color: var(--primary); box-shadow: 0 2px 6px rgba(0,0,0,0.04); }

        /* Mobile Page Indicator (Auto-Hiding Ghost Dock) */
        .mobile-indicator {
            display: none; /* Desktop hidden */
            position: absolute; bottom: 30px; left: 50%; 
            transform: translateX(-50%) translateY(20px); /* Initially down and hidden */
            opacity: 0;
            justify-content: center; gap: 8px;
            padding: 8px 16px;
            background: rgba(255,255,255,0.85); 
            backdrop-filter: blur(12px); -webkit-backdrop-filter: blur(12px);
            border-radius: 20px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            z-index: 50;
            transition: opacity 0.5s cubic-bezier(0.2, 0.8, 0.2, 1), transform 0.5s cubic-bezier(0.2, 0.8, 0.2, 1);
            pointer-events: none; /* Let touches pass through when hidden */
        }
        /* Active State for Indicator */
        .mobile-indicator.visible {
            opacity: 1;
            transform: translateX(-50%) translateY(0);
        }
        
        .dot {
            width: 6px; height: 6px; border-radius: 50%; background: #cbd5e1;
            transition: all 0.3s cubic-bezier(0.25, 1, 0.5, 1);
        }
        .dot.active { width: 16px; background: var(--primary); border-radius: 4px; }

        /* Main Panel */
        .main-panel { 
            flex: 1; padding: 24px 36px; 
            overflow-y: auto; overflow-x: hidden; scroll-behavior: smooth; 
            -webkit-overflow-scrolling: touch;
            position: relative;
        }

        /* --- Smooth Slide Animations --- */
        .section { 
            display: none; 
            max-width: 960px; margin: 0 auto; padding-bottom: 100px; 
            width: 100%;
        }
        .section.active { display: block; }
        
        /* Keyframes for sliding */
        .anim-enter-right { animation: slideInRight 0.4s cubic-bezier(0.2, 0.8, 0.2, 1) forwards; }
        .anim-exit-left { animation: slideOutLeft 0.4s cubic-bezier(0.2, 0.8, 0.2, 1) forwards; }
        .anim-enter-left { animation: slideInLeft 0.4s cubic-bezier(0.2, 0.8, 0.2, 1) forwards; }
        .anim-exit-right { animation: slideOutRight 0.4s cubic-bezier(0.2, 0.8, 0.2, 1) forwards; }

        @keyframes slideInRight {
            from { opacity: 0; transform: translateX(30px) scale(0.98); }
            to { opacity: 1; transform: translateX(0) scale(1); }
        }
        @keyframes slideOutLeft {
            from { opacity: 1; transform: translateX(0) scale(1); }
            to { opacity: 0; transform: translateX(-30px) scale(0.98); }
        }
        @keyframes slideInLeft {
            from { opacity: 0; transform: translateX(-30px) scale(0.98); }
            to { opacity: 1; transform: translateX(0) scale(1); }
        }
        @keyframes slideOutRight {
            from { opacity: 1; transform: translateX(0) scale(1); }
            to { opacity: 0; transform: translateX(30px) scale(0.98); }
        }

        /* --- Dashboard --- */
        .dash-header { display: flex; justify-content: space-between; align-items: flex-end; margin-bottom: 20px; }
        .welcome-box h1 { font-size: 24px; font-weight: 800; margin: 0; color: #1e293b; letter-spacing: -0.5px; }
        .welcome-box p { font-size: 13px; color: var(--text-sub); margin: 2px 0 0 0; }
        
        .clock-box { text-align: right; }
        .clock-time { font-size: 30px; font-weight: 800; color: #334155; font-variant-numeric: tabular-nums; }
        .clock-date { font-size: 12px; color: var(--text-sub); font-weight: 600; }

        .quote-card { 
            background: rgba(255,255,255,0.8);
            padding: 14px 20px; border-radius: 16px; margin-bottom: 24px; 
            border: 1px solid rgba(255,255,255,0.5);
            display: flex; align-items: center; gap: 12px;
        }
        .quote-text { font-size: 13px; font-weight: 500; font-style: italic; color: #475569; line-height: 1.4; }

        /* --- LIQUID CARDS --- */
        .dash-grid { 
            display: grid; grid-template-columns: repeat(3, 1fr); gap: 18px; 
            margin-bottom: 24px; height: 130px; 
        }
        .liquid-card {
            position: relative; overflow: hidden;
            border-radius: 20px; background: #fff;
            border: 1px solid rgba(255, 255, 255, 0.6);
            box-shadow: 0 4px 15px rgba(0,0,0,0.03);
            transition: transform 0.2s, box-shadow 0.2s;
            cursor: pointer; z-index: 1; transform: translateZ(0); 
            -webkit-tap-highlight-color: transparent;
        }
        .liquid-card:active { transform: scale(0.98); }

        .liquid-container {
            position: absolute; width: 100%; height: 100%; top: 0; left: 0; z-index: 0;
            transition: transform 0.5s cubic-bezier(0.2, 0.8, 0.2, 1); will-change: transform;
        }
        .liquid-wave-wrapper {
            position: absolute; bottom: 0; left: 0; width: 100%; height: 0%; 
            transition: height 0.6s cubic-bezier(0.4, 0, 0.2, 1); will-change: height;
            background: currentColor;
        }
        .wave-slider {
            position: absolute; 
            /* Fix for white line gap: overlap by 1px */
            top: -27px; 
            left: 0; width: 200%; height: 28px;
            background: currentColor;
            -webkit-mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1000 100' preserveAspectRatio='none'%3E%3Cpath d='M0 100 V 50 Q 250 0 500 50 T 1000 50 V 100 Z' fill='%23000'/%3E%3C/svg%3E");
            mask-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1000 100' preserveAspectRatio='none'%3E%3Cpath d='M0 100 V 50 Q 250 0 500 50 T 1000 50 V 100 Z' fill='%23000'/%3E%3C/svg%3E");
            -webkit-mask-size: 50% 100%; mask-size: 50% 100%;
            -webkit-mask-repeat: repeat-x; mask-repeat: repeat-x;
            animation: wave-move 4s linear infinite; will-change: transform;
        }
        .wave-slider.back { 
            /* Fix for gap: align perfectly with overlap */
            top: -27px; 
            opacity: 0.4; animation: wave-move 7s linear infinite reverse; 
        }
        @keyframes wave-move { 0% { transform: translate3d(0, 0, 0); } 100% { transform: translate3d(-50%, 0, 0); } }

        .theme-cpu { color: #f87171; } .theme-cpu .liquid-wave-wrapper { background: linear-gradient(to top, #ef4444, #f87171); }
        .theme-mem { color: #a78bfa; } .theme-mem .liquid-wave-wrapper { background: linear-gradient(to top, #7c3aed, #a78bfa); }
        .theme-disk { color: #60a5fa; } .theme-disk .liquid-wave-wrapper { background: linear-gradient(to top, #2563eb, #60a5fa); }

        .card-content {
            position: absolute; top: 0; left: 0; width: 100%; height: 100%; z-index: 10; padding: 16px 20px;
            display: flex; flex-direction: column; justify-content: space-between; pointer-events: none;
        }
        .stat-header { display: flex; align-items: center; gap: 8px; }
        .stat-icon { 
            font-size: 16px; width: 32px; height: 32px; background: rgba(255,255,255,0.9);
            border-radius: 8px; display: flex; align-items: center; justify-content: center; 
            box-shadow: 0 2px 6px rgba(0,0,0,0.05); color: #333;
        }
        .stat-title { font-weight: 700; color: #64748b; font-size: 12px; text-transform: uppercase; }
        .stat-value { font-size: 32px; font-weight: 800; color: #1e293b; letter-spacing: -1px; text-shadow: 0 0 15px rgba(255,255,255,0.9); }
        .stat-unit { font-size: 13px; font-weight: 600; color: #64748b; margin-left: 2px; text-shadow: 0 0 15px rgba(255,255,255,0.9); }

        /* Config UI */
        .config-card { 
            background: #fff; border-radius: 16px; padding: 20px; margin-bottom: 16px; 
            box-shadow: 0 1px 3px rgba(0,0,0,0.03); border: 1px solid #f1f5f9;
        }
        .card-title { 
            font-size: 14px; font-weight: 700; margin-bottom: 14px; padding-bottom: 10px; 
            border-bottom: 1px solid #f1f5f9; display: flex; justify-content: space-between; align-items: center; 
            color: #1e293b;
        }
        
        .cd-list { display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 12px; }
        .cd-item { background: #f8fafc; padding: 12px 16px; border-radius: 12px; display: flex; justify-content: space-between; align-items: center; }
        .cd-days { font-size: 16px; font-weight: 800; color: var(--primary); background: rgba(99, 102, 241, 0.1); padding: 4px 10px; border-radius: 8px; white-space: nowrap;}
        .cd-days.urgent { color: #ef4444; background: rgba(239, 68, 68, 0.1); }

        .form-row { display: grid; grid-template-columns: 1fr 1fr; gap: 15px; margin-bottom: 12px; }
        .label { display: block; font-size: 12px; font-weight: 600; color: #64748b; margin-bottom: 6px; }
        .input { width: 100%; padding: 12px 14px; border: 1px solid #e2e8f0; background: #f8fafc; border-radius: 10px; font-size: 16px; color: #334155; transition: 0.2s; font-family: inherit; -webkit-appearance: none;} /* 16px font to prevent iOS zoom */
        .input:focus { background: #fff; border-color: var(--primary); box-shadow: 0 0 0 3px rgba(99, 102, 241, 0.1); }
        .input-wrapper { position: relative; width: 100%; display: flex; align-items: center; }
        .eye-icon { position: absolute; right: 12px; cursor: pointer; color: #94a3b8; font-size: 14px; padding: 5px; }

        .list-item { background: #fff; border: 1px solid #f1f5f9; border-radius: 12px; padding: 14px; margin-bottom: 8px; position: relative; padding-right: 45px; }
        .btn-del { position: absolute; top: 50%; right: 10px; transform: translateY(-50%); width: 28px; height: 28px; border-radius: 8px; background: #fee2e2; color: #ef4444; border: none; cursor: pointer; display: flex; align-items: center; justify-content: center;}
        .btn-add-row { width: 100%; padding: 12px; border: 2px dashed #cbd5e1; background: transparent; border-radius: 12px; color: #64748b; font-weight: 700; cursor: pointer; font-size: 13px; display: flex; align-items: center; justify-content: center; gap: 6px;}

        .fab-save { 
            position: absolute; bottom: 30px; right: 40px; 
            background: linear-gradient(135deg, #6366f1, #4f46e5); color: white; padding: 12px 32px; border-radius: 50px; border: none; 
            font-weight: 700; font-size: 14px; box-shadow: 0 8px 20px rgba(79, 70, 229, 0.3); 
            cursor: pointer; transition: all 0.3s; z-index: 100; opacity: 0; pointer-events: none; transform: translateY(20px) scale(0.9); 
        }
        .fab-save.visible { opacity: 1; pointer-events: auto; transform: translateY(0) scale(1); }

        .particle-star { position: fixed; pointer-events: none; z-index: 99999; color: #fbbf24; font-size: 16px; opacity: 0; will-change: transform, opacity; display: flex; align-items: center; justify-content: center;}
        
        @keyframes popIn { from { opacity: 0; transform: scale(0.98); } to { opacity: 1; transform: scale(1); } }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

        .toggle { position: relative; width: 40px; height: 22px; display: inline-block; vertical-align: middle; }
        .toggle input { opacity: 0; width: 0; height: 0; }
        .slider { position: absolute; cursor: pointer; top: 0; left: 0; right: 0; bottom: 0; background-color: #cbd5e1; border-radius: 34px; transition: .3s; }
        .slider:before { position: absolute; content: ""; height: 16px; width: 16px; left: 3px; bottom: 3px; background-color: white; border-radius: 50%; transition: .3s; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }
        input:checked + .slider { background-color: var(--primary); }
        input:checked + .slider:before { transform: translateX(18px); }

        a.link-btn { text-decoration: none; font-size: 12px; color: var(--primary); font-weight: 600; background: #eef2ff; padding: 4px 8px; border-radius: 6px; }
        textarea#raw-json { width:100%; height:100%; border:none; resize:none; font-family:'Menlo', monospace; font-size:12px; color:#374151; background:transparent; line-height:1.6; padding: 15px; background: #f8fafc; border-radius: 12px; }
        #toast { position: fixed; top: 20px; left: 50%; transform: translateX(-50%) translateY(-100px); background: rgba(30, 41, 59, 0.9); backdrop-filter: blur(4px); color: white; padding: 10px 24px; border-radius: 30px; font-size: 13px; font-weight: 600; z-index: 10000; transition: transform 0.4s; width: max-content; max-width: 90%; text-align: center; }
        #toast.show { transform: translateX(-50%) translateY(0); }

        /* Confirm Modal */
        .modal-overlay {
            position: fixed; top: 0; left: 0; width: 100%; height: 100%;
            background: rgba(0,0,0,0.2); backdrop-filter: blur(5px);
            z-index: 2000; display: none; align-items: center; justify-content: center;
            animation: fadeIn 0.2s ease;
        }
        .modal-box {
            background: rgba(255,255,255,0.9); width: 85%; max-width: 320px;
            border-radius: 20px; padding: 24px; text-align: center;
            box-shadow: 0 20px 40px rgba(0,0,0,0.2);
            transform: scale(0.95); animation: popIn 0.3s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
        }
        .modal-title { font-size: 18px; font-weight: 700; margin-bottom: 8px; color: #1e293b; }
        .modal-desc { font-size: 14px; color: #64748b; margin-bottom: 24px; }
        .modal-actions { display: flex; flex-direction: column; gap: 10px; }
        .btn-modal { padding: 12px; border-radius: 12px; font-weight: 600; border: none; font-size: 14px; cursor: pointer; }
        .btn-primary { background: var(--primary); color: white; }
        .btn-danger { background: #fee2e2; color: #ef4444; }
        .btn-cancel { background: transparent; color: #94a3b8; }
        
        /* Mobile specific adjustments */
        @media (max-width: 768px) {
            .app-container { width: 100%; height: 100vh; border-radius: 0; border: none; }
            .header { padding: 12px 20px; }
            .content-wrapper { flex-direction: column; }
            .sidebar { display: none; }
            
            /* Move indicator to bottom center */
            .mobile-indicator { display: flex; }
            
            /* Hide the V8.0 text on mobile to make room for Title */
            .version-tag { display: none; }
            
            .main-panel { padding: 20px; padding-bottom: 120px; }
            .dash-grid { grid-template-columns: 1fr; height: auto; gap: 15px; } 
            .liquid-card { height: 120px; }
            .form-row { grid-template-columns: 1fr; gap: 10px; }
            .fab-save { bottom: 80px; right: 50%; transform: translateX(50%) translateY(20px) scale(0.9); width: auto; white-space: nowrap;}
            .fab-save.visible { transform: translateX(50%) translateY(0) scale(1); }
        }
    </style>
</head>
<body>
    <div class="app-container">
        <div class="header">
            <div class="brand"><div class="pulse-dot"></div> 监控推送控制台</div>
            <div class="version-tag" style="font-size:12px; color:var(--text-sub); font-weight:600; opacity:0.6">V8.5 Gulu</div>
            <div class="page-title" id="mobile-page-title" style="display:none">仪表盘</div>
        </div>
        
        <div class="content-wrapper">
            <!-- Desktop Sidebar -->
            <div class="sidebar">
                <button class="nav-btn active" onclick="switchTab('dashboard', this)"><span>🏠</span> 仪表盘</button>
                <button class="nav-btn" onclick="switchTab('basic', this)"><span>🛠️</span> 基础配置</button>
                <button class="nav-btn" onclick="switchTab('cyclic', this)"><span>📊</span> 循环上报</button>
                <button class="nav-btn" onclick="switchTab('alert', this)"><span>🚨</span> 主动报警</button>
                <button class="nav-btn" onclick="switchTab('schedule', this)"><span>📅</span> 日程任务</button>
                <button class="nav-btn" onclick="switchTab('json', this)"><span>📝</span> JSON 编辑</button>
            </div>
            
            <div class="main-panel" id="main-panel">
                <div id="dashboard" class="section active">
                    <div class="dash-header">
                        <div class="welcome-box">
                            <h1>Hi, TML 👋</h1>
                            <p>系统运行平稳，所有服务在线。</p>
                        </div>
                        <div class="clock-box">
                            <div class="clock-time" id="clock">00:00:00</div>
                            <div class="clock-date" id="date">Loading...</div>
                        </div>
                    </div>
                    <div class="quote-card"><div class="quote-icon">❝</div><div class="quote-text" id="dash-quote">正在获取每日一言...</div></div>
                    <div class="dash-grid">
                        <div class="liquid-card theme-cpu" id="card-cpu">
                            <div class="liquid-container"><div class="liquid-wave-wrapper" id="wave-fill-cpu"><div class="wave-slider back"></div><div class="wave-slider"></div></div></div>
                            <div class="card-content"><div class="stat-header"><div class="stat-icon">🔥</div><div class="stat-title">CPU 温度</div></div><div class="stat-value-box"><span class="stat-value" id="val-cpu">0</span><span class="stat-unit">°C</span></div></div>
                        </div>
                        <div class="liquid-card theme-mem" id="card-mem">
                            <div class="liquid-container"><div class="liquid-wave-wrapper" id="wave-fill-mem"><div class="wave-slider back"></div><div class="wave-slider"></div></div></div>
                            <div class="card-content"><div class="stat-header"><div class="stat-icon">🧠</div><div class="stat-title">内存占用</div></div><div class="stat-value-box"><span class="stat-value" id="val-mem">0</span><span class="stat-unit">%</span></div></div>
                        </div>
                        <div class="liquid-card theme-disk" id="card-disk">
                            <div class="liquid-container"><div class="liquid-wave-wrapper" id="wave-fill-disk"><div class="wave-slider back"></div><div class="wave-slider"></div></div></div>
                            <div class="card-content"><div class="stat-header"><div class="stat-icon">💾</div><div class="stat-title">磁盘空间</div></div><div class="stat-value-box"><span class="stat-value" id="val-disk">0</span><span class="stat-unit">%</span></div></div>
                        </div>
                    </div>
                    <div class="config-card"><div class="card-title">📅 倒数日概览</div><div id="dash-cd-list" class="cd-list"></div></div>
                </div>

                <div id="basic" class="section">
                    <div class="config-card"><div class="card-title">PushPlus 用户列表</div><div id="push-list"></div><button class="btn-add-row" onclick="addPush()"><span>+</span> 添加用户</button></div>
                    <div class="config-card">
                        <div class="card-title">密钥管理</div>
                        <div class="form-row">
                            <div class="form-group"><label class="label">高德地图 Key</label><div class="input-wrapper"><input type="password" class="input" id="key-amap"><span class="eye-icon" onclick="toggleEye('key-amap', this)">👁️</span></div></div>
                            <div class="form-group"><label class="label">和风天气 Key</label><div class="input-wrapper"><input type="password" class="input" id="key-qweather"><span class="eye-icon" onclick="toggleEye('key-qweather', this)">👁️</span></div></div>
                        </div>
                    </div>
                    <div class="config-card"><div class="card-title">日志</div><div class="form-group"><label class="label">保留天数</label><input type="number" class="input" id="log-days" style="width:120px"></div></div>
                </div>

                <div id="cyclic" class="section">
                    <div class="config-card">
                        <div class="card-title">功能开关 <label class="toggle"><input type="checkbox" id="cyc-enable"><span class="slider"></span></label></div>
                        <div style="display:flex; gap:30px;">
                            <div class="form-group"><label class="label">整点报时</label><label class="toggle"><input type="checkbox" id="cyc-align" onchange="toggleCycInput()"><span class="slider"></span></label></div>
                            <div class="form-group" style="flex:1"><label class="label">轮询间隔 (分钟)</label><input type="number" class="input" id="cyc-interval"></div>
                        </div>
                    </div>
                    <div class="config-card"><div class="card-title">监控地点 <a href="https://github.com/qwd/LocationList" target="_blank" class="link-btn">🔍 代码表</a></div><div id="loc-list"></div><button class="btn-add-row" onclick="addLoc()"><span>+</span> 添加地点</button></div>
                </div>

                <div id="alert" class="section">
                    <div class="config-card">
                        <div class="card-title">阈值设置</div>
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:25px">
                            <div class="form-group"><label class="label">CPU温度</label><input type="number" class="input" id="alt-temp"></div>
                            <div class="form-group"><label class="label">磁盘占用</label><input type="number" class="input" id="alt-disk"></div>
                            <div class="form-group"><label class="label">金价低位</label><input type="number" class="input" id="alt-glow"></div>
                            <div class="form-group"><label class="label">金价高位</label><input type="number" class="input" id="alt-ghigh"></div>
                        </div>
                    </div>
                    <div class="config-card"><div class="card-title">📺 B站关注</div><div id="bili-list"></div><button class="btn-add-row" onclick="addBili()"><span>+</span> 添加UP主</button></div>
                </div>

                <div id="schedule" class="section">
                    <div class="config-card">
                        <div class="card-title">
                            <div style="display:flex;align-items:center;gap:6px;flex-wrap:wrap">
                                通勤日报 🚌🚗🚲
                                <a href="https://lbs.amap.com/tools/picker" target="_blank" class="link-btn" style="font-weight:normal;opacity:0.9">📍 拾取坐标</a>
                            </div>
                            <label class="toggle"><input type="checkbox" id="sch-enable"><span class="slider"></span></label>
                        </div>
                        <div style="display:grid; grid-template-columns:1fr 1fr; gap:25px">
                            <div class="form-group"><label class="label">上班时间</label><input type="time" class="input" id="sch-start"></div>
                            <div class="form-group"><label class="label">下班时间</label><input type="time" class="input" id="sch-end"></div>
                        </div>
                        <div class="form-group"><label class="label">家坐标</label><input class="input" id="loc-home" placeholder="经度,纬度 (如: 116.39,39.90)"></div>
                        <div class="form-group"><label class="label">公司坐标</label><input class="input" id="loc-work" placeholder="经度,纬度"></div>
                    </div>
                    <div class="config-card"><div class="card-title">📅 倒数日</div><div id="cd-list"></div><button class="btn-add-row" onclick="addCD()"><span>+</span> 添加纪念日</button></div>
                </div>

                <div id="json" class="section">
                    <div class="config-card" style="height:650px;display:flex;flex-direction:column"><textarea id="raw-json" spellcheck="false"></textarea></div>
                </div>
            </div>
        </div>
        
        <!-- Mobile Bottom Floating Indicator -->
        <div class="mobile-indicator" id="page-dots"></div>
        
        <button id="save-btn" class="fab-save" onclick="handleSaveClick()">💾 保存配置</button>
    </div>
    
    <!-- Confirm Modal -->
    <div class="modal-overlay" id="confirm-modal">
        <div class="modal-box">
            <div class="modal-title">未保存的更改</div>
            <div class="modal-desc">您修改了配置但尚未保存，如果离开，更改将丢失。</div>
            <div class="modal-actions">
                <button class="btn-modal btn-primary" onclick="confirmSave()">保存并离开</button>
                <button class="btn-modal btn-danger" onclick="confirmDiscard()">放弃修改</button>
                <button class="btn-modal btn-cancel" onclick="closeModal()">取消</button>
            </div>
        </div>
    </div>
    <div id="toast"></div>

    <script>
        // --- Global State ---
        let cfg = {};
        let originalCfgStr = ""; 
        const tabs = ['dashboard', 'basic', 'cyclic', 'alert', 'schedule', 'json'];
        const tabNames = ['仪表盘', '基础配置', '循环上报', '主动报警', '日程任务', 'JSON 编辑']; // Title mapping
        let currentTabIndex = 0;
        let pendingTargetIndex = -1; 

        // --- Init ---
        window.onload = async () => {
            initDots();
            setInterval(updateClock, 1000); updateClock();
            setInterval(loadStatus, 3000); 
            // Mobile Title Init
            updateMobileTitle(0);
            
            try {
                const res = await fetch('/api/config');
                cfg = await res.json();
                originalCfgStr = JSON.stringify(cfg); 
                renderAll(); loadStatus();
                // Initially show indicator
                wakeUpIndicator();
            } catch(e) { toast('初始化失败', true); }
        };

        // --- Auto-Hide Indicator Logic ---
        let indicatorTimer;
        const indicatorEl = document.getElementById('page-dots');

        function wakeUpIndicator() {
            if (!indicatorEl) return;
            // Show it
            indicatorEl.classList.add('visible');
            
            // Reset timer
            clearTimeout(indicatorTimer);
            indicatorTimer = setTimeout(() => {
                indicatorEl.classList.remove('visible');
            }, 3000); // Hide after 3 seconds of inactivity
        }

        // Add Listeners for global interaction
        window.addEventListener('touchstart', wakeUpIndicator, {passive: true});
        window.addEventListener('mousemove', wakeUpIndicator, {passive: true}); // For desktop testing context
        window.addEventListener('click', wakeUpIndicator, {passive: true});

        // --- Swipe Logic (Mobile) ---
        let touchStartX = 0;
        let touchStartY = 0;
        const mainPanel = document.getElementById('main-panel');

        mainPanel.addEventListener('touchstart', e => {
            touchStartX = e.changedTouches[0].screenX;
            touchStartY = e.changedTouches[0].screenY;
        }, {passive: true});

        mainPanel.addEventListener('touchend', e => {
            const touchEndX = e.changedTouches[0].screenX;
            const touchEndY = e.changedTouches[0].screenY;
            handleSwipe(touchStartX, touchEndX, touchStartY, touchEndY);
        }, {passive: true});

        function handleSwipe(startX, endX, startY, endY) {
            const diffX = endX - startX;
            const diffY = endY - startY;
            if (Math.abs(diffX) < 50 || Math.abs(diffY) > Math.abs(diffX)) return; // Scroll protection

            if (diffX > 0) {
                if (currentTabIndex > 0) attemptSwitch(currentTabIndex - 1, 'right');
            } else {
                if (currentTabIndex < tabs.length - 1) attemptSwitch(currentTabIndex + 1, 'left');
            }
        }

        // --- Dirty Check ---
        function isDirty() {
            if (currentTabIndex === 0) return false; 
            if (tabs[currentTabIndex] === 'json') {
                const currentJsonStr = val('raw-json');
                try {
                    const currentObj = JSON.parse(currentJsonStr);
                    const originalObj = JSON.parse(originalCfgStr);
                    return JSON.stringify(currentObj) !== JSON.stringify(originalObj);
                } catch(e) { return true; } 
            }
            return JSON.stringify(cfg) !== originalCfgStr;
        }

        function attemptSwitch(targetIndex, direction = 'jump') {
            wakeUpIndicator(); // Ensure indicator is visible when switching
            if (targetIndex === currentTabIndex) return;
            if (isDirty()) {
                pendingTargetIndex = targetIndex;
                openModal();
            } else {
                executeSwitch(targetIndex, direction);
            }
        }

        function executeSwitch(index, direction) {
            const oldIndex = currentTabIndex;
            currentTabIndex = index;
            const tabId = tabs[index];

            // 1. Mobile Title Update
            updateMobileTitle(index);

            // 2. Animation Classes logic
            const oldSection = byId(tabs[oldIndex]);
            const newSection = byId(tabId);
            
            // Remove old animation classes
            oldSection.classList.remove('active', 'anim-enter-right', 'anim-enter-left', 'anim-exit-left', 'anim-exit-right');
            newSection.classList.remove('active', 'anim-enter-right', 'anim-enter-left', 'anim-exit-left', 'anim-exit-right');

            // Apply direction based animation
            if (direction === 'left') { // Next Page
                oldSection.classList.add('active', 'anim-exit-left'); // Slide out to left
                newSection.classList.add('active', 'anim-enter-right'); // Slide in from right
                
                // Cleanup after animation
                setTimeout(() => {
                    oldSection.classList.remove('active', 'anim-exit-left');
                }, 400); 

            } else if (direction === 'right') { // Prev Page
                oldSection.classList.add('active', 'anim-exit-right'); // Slide out to right
                newSection.classList.add('active', 'anim-enter-left'); // Slide in from left
                
                setTimeout(() => {
                    oldSection.classList.remove('active', 'anim-exit-right');
                }, 400);
            } else {
                // Default Jump (Desktop Click) - No fancy slide, just fade
                document.querySelectorAll('.section').forEach(e => e.classList.remove('active'));
                newSection.classList.add('active', 'anim-enter-right'); // Default fade in
            }
            
            // 3. Update Nav States
            document.querySelectorAll('.nav-btn').forEach(e => e.classList.remove('active'));
            document.querySelectorAll('.nav-btn')[index].classList.add('active');
            document.querySelectorAll('.dot').forEach((d, i) => {
                if(i === index) d.classList.add('active'); else d.classList.remove('active');
            });
            
            const saveBtn = byId('save-btn');
            if (tabId === 'dashboard') saveBtn.classList.remove('visible'); else saveBtn.classList.add('visible');
        }

        function updateMobileTitle(index) {
            const titleEl = byId('mobile-page-title');
            if (window.innerWidth <= 768) {
                titleEl.style.display = 'block';
                titleEl.innerText = tabNames[index];
            } else {
                titleEl.style.display = 'none';
            }
        }

        // --- Modal ---
        function openModal() { byId('confirm-modal').style.display = 'flex'; }
        function closeModal() { byId('confirm-modal').style.display = 'none'; pendingTargetIndex = -1; }
        
        async function confirmSave() {
            closeModal();
            const success = await saveAll();
            if (success && pendingTargetIndex !== -1) executeSwitch(pendingTargetIndex, pendingTargetIndex > currentTabIndex ? 'left' : 'right');
        }
        
        function confirmDiscard() {
            closeModal();
            cfg = JSON.parse(originalCfgStr);
            renderAll(); 
            if (pendingTargetIndex !== -1) executeSwitch(pendingTargetIndex, pendingTargetIndex > currentTabIndex ? 'left' : 'right');
        }

        // --- Standard UI ---
        function initDots() {
            const container = byId('page-dots');
            tabs.forEach((_, i) => {
                const dot = document.createElement('div');
                dot.className = 'dot' + (i===0 ? ' active' : '');
                container.appendChild(dot);
            });
        }

        function switchTab(id, btn) {
            const index = tabs.indexOf(id);
            attemptSwitch(index);
        }

        async function handleSaveClick() { await saveAll(); }

        async function saveAll() {
            if (document.getElementById('json').classList.contains('active')) {
                const rawContent = val('raw-json');
                try { cfg = JSON.parse(rawContent); } 
                catch(e) { toast('⚠️ JSON 格式错误', true); return false; }
            } else {
                cfg.api_keys.amap = val('key-amap');
                cfg.api_keys.qweather = val('key-qweather');
                cfg.logging.retention_days = parseInt(val('log-days'));
                cfg.cyclic_report.enable = byId('cyc-enable').checked;
                cfg.cyclic_report.align_to_hour = byId('cyc-align').checked;
                cfg.cyclic_report.interval_minutes = parseInt(val('cyc-interval'));
                cfg.active_alert.server.cpu_temp_threshold = parseInt(val('alt-temp'));
                cfg.active_alert.server.disk_usage_threshold = parseInt(val('alt-disk'));
                cfg.active_alert.gold.low = parseInt(val('alt-glow'));
                cfg.active_alert.gold.high = parseInt(val('alt-ghigh'));
                cfg.scheduled_push.commute.enable = byId('sch-enable').checked;
                cfg.scheduled_push.commute.work_start = val('sch-start');
                cfg.scheduled_push.commute.work_end = val('sch-end');
                cfg.scheduled_push.commute.home_loc = val('loc-home');
                cfg.scheduled_push.commute.work_loc = val('loc-work');
            }

            try {
                const res = await fetch('/api/save', { method: 'POST', body: JSON.stringify(cfg) });
                if(res.ok) { 
                    toast('✅ 配置已安全保存'); 
                    originalCfgStr = JSON.stringify(cfg); 
                    renderAll(); loadStatus();
                    return true;
                } else {
                    const errText = await res.text();
                    try { toast('❌ ' + JSON.parse(errText).error, true); } catch(e) { toast('❌ 服务器错误', true); }
                    return false;
                }
            } catch(e) { toast('❌ 网络错误', true); return false; }
        }

        // --- Helpers ---
        window.addEventListener('click', (e) => { createStars(e.clientX, e.clientY); });
        function createStars(x, y) {
            // Updated paths to be absolute from server root
            const images = [
                '/gulu/普通咕噜球.png',
                '/gulu/高级咕噜球.png',
                '/gulu/超级咕噜球.png',
                '/gulu/国王球.png',
            ]; 
            
            for (let i = 0; i < 6; i++) {
                const star = document.createElement('div');
                star.classList.add('particle-star');
                
                // Random Size Logic (e.g., 10px to 20px)
                const size = 10 + Math.random() * 10; 
                star.style.width = `${size}px`;
                star.style.height = `${size}px`;
                
                // Create Image
                const img = document.createElement('img');
                img.src = images[Math.floor(Math.random() * images.length)];
                img.style.width = '100%';
                img.style.height = '100%';
                img.style.objectFit = 'contain';
                
                star.appendChild(img);
                document.body.appendChild(star);
                
                const offsetX = (Math.random() - 0.5) * 60;
                const offsetY = (Math.random() - 0.5) * 40;
                star.style.left = (x + offsetX) + 'px';
                star.style.top = (y + offsetY) + 'px';
                star.animate([
                    { transform: 'translate(0, 0) scale(0.5)', opacity: 0 },
                    { transform: `translate(${offsetX * 0.5}px, 20px) scale(1)`, opacity: 1, offset: 0.2 },
                    { transform: `translate(${offsetX}px, 150px) scale(0.5)`, opacity: 0 }
                ], { duration: 2000 + Math.random() * 1000 }).onfinish = () => star.remove();
            }
        }
        
        document.querySelectorAll('.liquid-card').forEach(card => {
            const container = card.querySelector('.liquid-container');
            card.addEventListener('mouseenter', () => { container.style.transform = 'translate3d(0, 15px, 0)'; setTimeout(() => container.style.transform = 'translate3d(0,0,0)', 150); });
            card.addEventListener('mouseleave', () => { container.style.transform = 'translate3d(0, -15px, 0)'; setTimeout(() => container.style.transform = 'translate3d(0,0,0)', 200); });
            card.addEventListener('touchstart', () => { container.style.transform = 'translate3d(0, 15px, 0)'; }, {passive:true});
            card.addEventListener('touchend', () => { container.style.transform = 'translate3d(0, -15px, 0)'; setTimeout(() => container.style.transform = 'translate3d(0,0,0)', 200); }, {passive:true});
        });

        function updateClock() {
            const now = new Date();
            byId('clock').innerText = now.toLocaleTimeString('en-GB');
            byId('date').innerText = now.toLocaleDateString('zh-CN', {weekday:'long', year:'numeric', month:'long', day:'numeric'});
        }

        function loadStatus() {
            fetch('/api/status').then(r=>r.json()).then(data => {
                byId('dash-quote').innerHTML = data.quote;
                const setWave = (id, v) => {
                    byId('val-'+id).innerText = v;
                    byId('wave-fill-'+id).style.height = Math.max(v, 10) + '%';
                };
                setWave('cpu', data.system.cpu_temp); setWave('mem', data.system.mem_usage); setWave('disk', data.system.disk_usage);
                
                const evts = data.countdowns || [];
                byId('dash-cd-list').innerHTML = evts.length ? evts.slice(0,6).map(e => `
                    <div class="cd-item">
                        <div><div style="font-weight:700;color:#334155;font-size:13px">${e.name}</div><div style="font-size:12px;color:#94a3b8">${e.date}</div></div>
                        <div class="cd-days ${e.days<=e.remind_days?'urgent':''}">${e.days} 天</div>
                    </div>`).join('') : '<div style="text-align:center;color:#999;grid-column:1/-1;padding:20px;">暂无倒数日配置</div>';
            }).catch(()=>{});
        }

        function renderAll() {
            val('key-amap', cfg.api_keys.amap);
            val('key-qweather', cfg.api_keys.qweather);
            val('log-days', cfg.logging.retention_days);
            chk('cyc-enable', cfg.cyclic_report.enable);
            chk('cyc-align', cfg.cyclic_report.align_to_hour);
            val('cyc-interval', cfg.cyclic_report.interval_minutes);
            toggleCycInput();
            val('alt-temp', cfg.active_alert.server.cpu_temp_threshold);
            val('alt-disk', cfg.active_alert.server.disk_usage_threshold);
            val('alt-glow', cfg.active_alert.gold.low);
            val('alt-ghigh', cfg.active_alert.gold.high);
            chk('sch-enable', cfg.scheduled_push.commute.enable);
            val('sch-start', cfg.scheduled_push.commute.work_start);
            val('sch-end', cfg.scheduled_push.commute.work_end);
            val('loc-home', cfg.scheduled_push.commute.home_loc);
            val('loc-work', cfg.scheduled_push.commute.work_loc);
            val('raw-json', JSON.stringify(cfg, null, 4));
            
            byId('push-list').innerHTML = cfg.pushplus_users.map((u, i) => `
                <div class="list-item"><button class="btn-del" onclick="cfg.pushplus_users.splice(${i},1);renderAll()">×</button><div style="display:flex; gap:10px;"><div class="input-wrapper" style="flex:2"><input class="input" type="password" id="pp-${i}" value="${u.token}" onchange="cfg.pushplus_users[${i}].token=this.value" placeholder="Token"><span class="eye-icon" onclick="toggleEye('pp-${i}',this)">👁️</span></div><input class="input" style="flex:1" value="${u.topic||''}" onchange="cfg.pushplus_users[${i}].topic=this.value" placeholder="Topic"></div></div>`).join('');
            
            byId('loc-list').innerHTML = cfg.cyclic_report.locations.map((l, i) => `
                <div class="list-item"><button class="btn-del" onclick="cfg.cyclic_report.locations.splice(${i},1);renderAll()">×</button><div style="display:flex;gap:10px"><input class="input" style="width:30%" value="${l.name}" onchange="cfg.cyclic_report.locations[${i}].name=this.value"><input class="input" style="flex:1" value="${l.code}" onchange="cfg.cyclic_report.locations[${i}].code=this.value"></div></div>`).join('');
                
            byId('bili-list').innerHTML = cfg.active_alert.bilibili.uids.map((u, i) => `
                <div class="list-item"><button class="btn-del" onclick="cfg.active_alert.bilibili.uids.splice(${i},1);renderAll()">×</button><div style="display:flex;gap:10px"><input class="input" style="width:40%" value="${u.name}" onchange="cfg.active_alert.bilibili.uids[${i}].name=this.value"><input class="input" style="flex:1" value="${u.uid}" onchange="cfg.active_alert.bilibili.uids[${i}].uid=this.value"></div></div>`).join('');
                
            byId('cd-list').innerHTML = cfg.scheduled_push.countdowns.map((c, i) => `
                <div class="list-item"><button class="btn-del" onclick="cfg.scheduled_push.countdowns.splice(${i},1);renderAll()">×</button><div style="display:flex;gap:10px;margin-bottom:10px"><input class="input" value="${c.name}" onchange="cfg.scheduled_push.countdowns[${i}].name=this.value"><input type="date" class="input" style="width:140px" value="${c.date}" onchange="cfg.scheduled_push.countdowns[${i}].date=this.value"></div><div style="display:flex;gap:15px;font-size:12px;align-items:center"><label style="display:flex;gap:4px"><input type="checkbox" ${c.is_lunar?'checked':''} onchange="cfg.scheduled_push.countdowns[${i}].is_lunar=this.checked"> 农历</label><span>提前 <input type="number" style="width:40px;padding:4px;border:1px solid #ddd;border-radius:6px" value="${c.remind_days}" onchange="cfg.scheduled_push.countdowns[${i}].remind_days=parseInt(this.value)"> 天</span></div></div>`).join('');
        }

        function addPush() { cfg.pushplus_users.push({token:"", topic:""}); renderAll(); }
        function addLoc() { cfg.cyclic_report.locations.push({name:"", code:""}); renderAll(); }
        function addBili() { cfg.active_alert.bilibili.uids.push({name:"", uid:""}); renderAll(); }
        function addCD() { cfg.scheduled_push.countdowns.push({name:"", date:"2025-01-01", is_lunar:false, remind_days:7}); renderAll(); }
        
        function toggleEye(id, icon) { const el = byId(id); el.type = el.type==='password'?'text':'password'; icon.innerText = el.type==='password'?'👁️':'🙈'; }
        function toggleCycInput() { byId('cyc-interval').disabled = byId('cyc-align').checked; }
        function val(id, v) { if(v===undefined) return byId(id).value; byId(id).value = v; }
        function chk(id, v) { byId(id).checked = v; }
        function byId(id) { return document.getElementById(id); }
        function toast(msg, err=false) { const t = byId('toast'); t.innerText = msg; t.style.background = err?'rgba(239,68,68,0.9)':'rgba(16,185,129,0.9)'; t.classList.add('show'); setTimeout(()=>t.classList.remove('show'), 3000); }
    </script>
</body>
</html>
"""
