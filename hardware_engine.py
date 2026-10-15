import os
import time
import math
import winreg
import platform
import subprocess
import threading
from collections import deque
import psutil

class HardwareEngine:
    def __init__(self):
        self.lock = threading.Lock()
        self.static_info = {}
        self.current_metrics = {
            "timestamp": time.time(),
            "cpu_percent": 0.0,
            "cpu_per_core": [],
            "cpu_freq_mhz": 0,
            "temperature_c": 0.0,
            "gpu_util": 0.0,
            "gpu_temp_c": 0.0,
            "memory_percent": 0.0,
            "memory_used_gb": 0.0,
            "memory_total_gb": 0.0,
            "memory_available_gb": 0.0,
            "disk_read_kbps": 0.0,
            "disk_write_kbps": 0.0,
            "net_download_kbps": 0.0,
            "net_upload_kbps": 0.0,
            "disks": [],
            "battery": None,
            "uptime_seconds": 0,
            "top_processes": [],
            "alert": {
                "level": "normal", # normal, caution, warning, critical
                "message": "システムは正常温度で安定稼働中"
            }
        }
        
        # Temp & GPU background poll cache
        self.cached_thermal_c = 0.0
        self.cached_gpu_util = 0.0
        
        # Previous counters for delta calculation
        self.prev_disk_io = psutil.disk_io_counters()
        self.prev_net_io = psutil.net_io_counters()
        self.prev_time = time.time()
        self.boot_time = psutil.boot_time()
        
        # Game Recording Session (In-memory ONLY, Explorer storage strictly disabled)
        self.recording_active = False
        self.session_data = []
        self.session_summary = None
        
        # Initialize static specs
        self._init_static_specs()
        
        # Start background polling thread for counters (Thermal & GPU)
        self.running = True
        self.counter_thread = threading.Thread(target=self._counter_poll_worker, daemon=True)
        self.counter_thread.start()

    def _init_static_specs(self):
        # CPU
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
            cpu_name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
            mhz, _ = winreg.QueryValueEx(key, "~MHz")
            winreg.CloseKey(key)
        except Exception:
            cpu_name = platform.processor()
            mhz = 0

        self.static_info = {
            "cpu_name": cpu_name.strip(),
            "cpu_base_mhz": mhz,
            "cpu_physical_cores": psutil.cpu_count(logical=False) or 0,
            "cpu_threads": psutil.cpu_count(logical=True) or 0,
            "cpu_arch": platform.machine(),
            "memory_total_gb": round(psutil.virtual_memory().total / (1024**3), 2),
            "gpu_name": "汎用GPU",
            "gpu_driver": "N/A",
            "gpu_vram_mb": 0,
            "board_vendor": "N/A",
            "board_model": "N/A",
            "bios_version": "N/A",
            "os_caption": f"{platform.system()} {platform.release()}",
            "os_build": platform.version(),
        }

        # Query WMI once for deep hardware specs
        try:
            ps_script = """
            $ErrorActionPreference = 'SilentlyContinue'
            $gpu = Get-CimInstance Win32_VideoController | Select-Object -First 1 Name, DriverVersion, AdapterRAM
            $board = Get-CimInstance Win32_BaseBoard | Select-Object -First 1 Manufacturer, Product
            $bios = Get-CimInstance Win32_BIOS | Select-Object -First 1 SMBIOSBIOSVersion, ReleaseDate
            $os = Get-CimInstance Win32_OperatingSystem | Select-Object -First 1 Caption, BuildNumber

            [PSCustomObject]@{
                gpu_name = $gpu.Name
                gpu_driver = $gpu.DriverVersion
                gpu_vram_mb = [math]::Round($gpu.AdapterRAM / 1MB, 0)
                board_vendor = $board.Manufacturer
                board_model = $board.Product
                bios_version = $bios.SMBIOSBIOSVersion
                os_caption = $os.Caption
                os_build = $os.BuildNumber
            } | ConvertTo-Json -Compress
            """
            proc = subprocess.run(["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
                                  capture_output=True, text=True, encoding="utf-8", timeout=6)
            import json
            data = json.loads(proc.stdout.strip())
            for k, v in data.items():
                if v:
                    self.static_info[k] = v
        except Exception:
            pass

    def _counter_poll_worker(self):
        """Polls temperature and GPU utilization using Windows performance counters."""
        ps_loop_script = """
        $ErrorActionPreference = 'SilentlyContinue'
        while ($true) {
            $thermalRaw = (Get-Counter '\\Thermal Zone Information(*)\\High Precision Temperature' -MaxSamples 1).CounterSamples.CookedValue
            if (-not $thermalRaw) {
                $thermalRaw = (Get-Counter '\\Thermal Zone Information(*)\\Temperature' -MaxSamples 1).CounterSamples.CookedValue
                if ($thermalRaw) { $thermalC = [math]::Round($thermalRaw - 273.15, 1) } else { $thermalC = 0 }
            } else {
                $thermalC = [math]::Round(($thermalRaw / 10.0) - 273.15, 1)
            }

            $gpuSample = (Get-Counter '\\GPU Engine(*engtype_3D)\\Utilization Percentage' -MaxSamples 1).CounterSamples
            $gpuUtil = 0
            if ($gpuSample) {
                $gpuUtil = [math]::Round(($gpuSample | Measure-Object -Property CookedValue -Sum).Sum, 1)
            }

            "$thermalC,$gpuUtil"
            Start-Sleep -Milliseconds 800
        }
        """
        while self.running:
            try:
                proc = subprocess.Popen(
                    ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_loop_script],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    encoding="utf-8",
                    bufsize=1
                )
                for line in proc.stdout:
                    if not self.running:
                        break
                    line = line.strip()
                    if line and "," in line:
                        parts = line.split(",")
                        try:
                            t = float(parts[0])
                            g = float(parts[1])
                            with self.lock:
                                self.cached_thermal_c = t
                                self.cached_gpu_util = g
                        except ValueError:
                            pass
                proc.terminate()
            except Exception:
                time.sleep(2)

    def sample_metrics(self):
        with self.lock:
            cached_temp = self.cached_thermal_c
            cached_gpu = self.cached_gpu_util

        now = time.time()
        dt = max(now - self.prev_time, 0.001)

        # CPU
        cpu_percent = psutil.cpu_percent(interval=None)
        cpu_per_core = psutil.cpu_percent(interval=None, percpu=True)
        freq = psutil.cpu_freq()
        cpu_freq_mhz = round(freq.current, 0) if freq else 0

        # Memory
        mem = psutil.virtual_memory()
        mem_percent = mem.percent
        mem_used_gb = round(mem.used / (1024**3), 2)
        mem_total_gb = round(mem.total / (1024**3), 2)
        mem_available_gb = round(mem.available / (1024**3), 2)

        # Disk I/O
        current_disk_io = psutil.disk_io_counters()
        disk_read_kbps = 0.0
        disk_write_kbps = 0.0
        if current_disk_io and self.prev_disk_io:
            disk_read_kbps = round((current_disk_io.read_bytes - self.prev_disk_io.read_bytes) / 1024 / dt, 1)
            disk_write_kbps = round((current_disk_io.write_bytes - self.prev_disk_io.write_bytes) / 1024 / dt, 1)
        self.prev_disk_io = current_disk_io

        # Network I/O
        current_net_io = psutil.net_io_counters()
        net_down_kbps = 0.0
        net_up_kbps = 0.0
        if current_net_io and self.prev_net_io:
            net_down_kbps = round((current_net_io.bytes_recv - self.prev_net_io.bytes_recv) / 1024 / dt, 1)
            net_up_kbps = round((current_net_io.bytes_sent - self.prev_net_io.bytes_sent) / 1024 / dt, 1)
        self.prev_net_io = current_net_io
        self.prev_time = now

        # Storage partitions
        disks = []
        for p in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(p.mountpoint)
                disks.append({
                    "device": p.device,
                    "mount": p.mountpoint,
                    "fstype": p.fstype,
                    "total_gb": round(usage.total / (1024**3), 1),
                    "used_gb": round(usage.used / (1024**3), 1),
                    "free_gb": round(usage.free / (1024**3), 1),
                    "percent": usage.percent
                })
            except Exception:
                pass

        # Battery
        battery_data = None
        try:
            bat = psutil.sensors_battery()
            if bat:
                battery_data = {
                    "percent": bat.percent,
                    "power_plugged": bat.power_plugged,
                    "secsleft": bat.secsleft if bat.secsleft > 0 else None
                }
        except Exception:
            pass

        # Top processes by CPU and Memory
        top_procs = []
        try:
            for p in sorted(psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']),
                            key=lambda x: (x.info['cpu_percent'] or 0) + (x.info['memory_percent'] or 0),
                            reverse=True)[:6]:
                try:
                    top_procs.append({
                        "pid": p.info['pid'],
                        "name": p.info['name'],
                        "cpu": round(p.info['cpu_percent'] or 0.0, 1),
                        "mem": round(p.info['memory_percent'] or 0.0, 1)
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception:
            pass

        # High temperature evaluation
        # Temperatures: caution >= 75C, warning >= 82C, critical >= 88C
        temp = cached_temp if cached_temp > 0 else (45.0 + (cpu_percent * 0.35))
        alert_level = "normal"
        alert_msg = "CPU・システム温度は適正範囲内です（安定）"
        if temp >= 88.0:
            alert_level = "critical"
            alert_msg = f"【極度危険】CPU温度が {temp}℃ に達しました！サーマルスロットリングや熱暴走に警戒してください！"
        elif temp >= 82.0:
            alert_level = "warning"
            alert_msg = f"【高温警告】CPU温度が {temp}℃ です。ファンの動作やエアフローを確認してください。"
        elif temp >= 75.0:
            alert_level = "caution"
            alert_msg = f"【温度注意】負荷上昇に伴い温度が {temp}℃ に上昇しています。"

        # GPU temp approximation if not directly reported
        gpu_temp = round(max(38.0, temp - 5.0 + (cached_gpu * 0.2)), 1)

        uptime = int(now - self.boot_time)

        metrics = {
            "timestamp": now,
            "cpu_percent": round(cpu_percent, 1),
            "cpu_per_core": [round(c, 1) for c in cpu_per_core],
            "cpu_freq_mhz": cpu_freq_mhz,
            "temperature_c": round(temp, 1),
            "gpu_util": round(min(cached_gpu, 100.0), 1),
            "gpu_temp_c": gpu_temp,
            "memory_percent": round(mem_percent, 1),
            "memory_used_gb": mem_used_gb,
            "memory_total_gb": mem_total_gb,
            "memory_available_gb": mem_available_gb,
            "disk_read_kbps": disk_read_kbps,
            "disk_write_kbps": disk_write_kbps,
            "net_download_kbps": net_down_kbps,
            "net_upload_kbps": net_up_kbps,
            "disks": disks,
            "battery": battery_data,
            "uptime_seconds": uptime,
            "top_processes": top_procs,
            "alert": {
                "level": alert_level,
                "message": alert_msg
            }
        }

        # Handle Game Flight Recorder (strictly in RAM memory)
        if self.recording_active:
            self.session_data.append({
                "t": round(now - self.session_start_time, 1),
                "cpu": metrics["cpu_percent"],
                "gpu": metrics["gpu_util"],
                "temp": metrics["temperature_c"],
                "mem": metrics["memory_percent"],
                "read_kb": disk_read_kbps,
                "write_kb": disk_write_kbps
            })

        self.current_metrics = metrics
        return metrics

    def start_game_recording(self):
        """Start game session recorder in volatile memory."""
        self.session_data = []
        self.session_summary = None
        self.session_start_time = time.time()
        self.recording_active = True
        return {"status": "recording_started", "time": self.session_start_time}

    def stop_game_recording(self):
        """Stop game session recorder and analyze the flight log in memory."""
        if not self.recording_active:
            return {"error": "Recording is not active"}
        
        self.recording_active = False
        duration = round(time.time() - self.session_start_time, 1)
        data = self.session_data
        
        if not data:
            self.session_summary = {"duration": duration, "samples": 0}
            return self.session_summary

        cpu_vals = [d["cpu"] for d in data]
        gpu_vals = [d["gpu"] for d in data]
        temp_vals = [d["temp"] for d in data]
        mem_vals = [d["mem"] for d in data]

        avg_cpu = round(sum(cpu_vals) / len(cpu_vals), 1)
        max_cpu = round(max(cpu_vals), 1)
        avg_gpu = round(sum(gpu_vals) / len(gpu_vals), 1)
        max_gpu = round(max(gpu_vals), 1)
        max_temp = round(max(temp_vals), 1)
        avg_temp = round(sum(temp_vals) / len(temp_vals), 1)
        peak_mem = round(max(mem_vals), 1)

        # Bottleneck & Stability assessment
        bottleneck = "均衡 (Balanced)"
        if avg_gpu > 88.0 and avg_cpu < 60.0:
            bottleneck = "GPU律速 (GPU Bottleneck) - グラフィック設定の最適化余地あり"
        elif avg_cpu > 85.0 and avg_gpu < 50.0:
            bottleneck = "CPU律速 (CPU Bottleneck) - バックグラウンドタスクまたはCPU負荷高"
        elif max_temp >= 88.0:
            bottleneck = "サーマルスロットリング警戒 (Thermal Throttling Risk)"

        self.session_summary = {
            "duration_sec": duration,
            "samples_count": len(data),
            "avg_cpu": avg_cpu,
            "max_cpu": max_cpu,
            "avg_gpu": avg_gpu,
            "max_gpu": max_gpu,
            "avg_temp": avg_temp,
            "max_temp": max_temp,
            "peak_mem": peak_mem,
            "bottleneck": bottleneck,
            "timeline": data[-60:] if len(data) > 60 else data # return up to 60 points for summary chart
        }
        return self.session_summary

    def close(self):
        self.running = False
