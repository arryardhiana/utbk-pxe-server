"""
UTBK PXE Server Orchestrator v2.0
Developed by Arry A - Universitas Padjadjaran
Copyright (c) 2026. All rights reserved.
"""

import os
import shutil
import psutil
import socket
import time
from fastapi import FastAPI, UploadFile, File, HTTPException, Header, Depends
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from typing import List
import subprocess
import glob
from datetime import datetime, timedelta
import re

app = FastAPI(title="UTBK PXE Server API")

UPLOAD_DIR = os.getenv("UPLOAD_DIR", "/app/uploads")
RAM_DISK = os.getenv("RAM_DISK", "/ram-disk")
TFTP_BOOT = os.getenv("TFTP_BOOT", "/var/lib/tftpboot")
METADATA_FILE = os.path.join(UPLOAD_DIR, "iso_metadata.json")
CONFIG_FILE = os.path.join(UPLOAD_DIR, "config.json")
APP_PASSWORD = os.getenv("APP_PASSWORD", "admin123")

async def verify_token(x_dashboard_token: str = Header(None)):
    if not x_dashboard_token or x_dashboard_token != APP_PASSWORD:
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid dashboard token")
    return x_dashboard_token

def detect_host_ip():
    """Detects the primary host IP, excluding lo and docker interfaces."""
    interfaces = psutil.net_if_addrs()
    # Priority patterns for main interfaces
    priority_patterns = [r'^eth', r'^ens', r'^eno', r'^enp']
    
    # First, try to find an IP on priority interfaces
    for pattern in priority_patterns:
        for iface, addrs in interfaces.items():
            if re.match(pattern, iface):
                for addr in addrs:
                    if addr.family == socket.AF_INET: # Only IPv4
                        if addr.address == '127.0.0.1':
                            continue
                        return addr.address
    
    # Fallback: any interface that isn't lo, docker, or bridge
    for iface, addrs in interfaces.items():
        if iface == 'lo' or iface.startswith('docker') or iface.startswith('br-') or iface.startswith('veth'):
            continue
        for addr in addrs:
            if addr.family == socket.AF_INET and addr.address != '127.0.0.1':
                return addr.address
                
    return "127.0.0.1" # Hard fallback if nothing found

def get_config():
    import json
    config = None
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                config = json.load(f)
        except:
            pass
    
    # Smart Validation: Check if saved IP still belongs to this host
    if config and "server_ip" in config:
        saved_ip = config["server_ip"]
        interfaces = psutil.net_if_addrs()
        all_host_ips = []
        for iface_addrs in interfaces.values():
            for addr in iface_addrs:
                if addr.family == socket.AF_INET:
                    all_host_ips.append(addr.address)
        
        if saved_ip not in all_host_ips and saved_ip != "127.0.0.1":
            print(f"Portability Alert: Saved IP {saved_ip} not found on this host. Re-detecting...")
            detected_ip = detect_host_ip()
            if detected_ip != saved_ip:
                config["server_ip"] = detected_ip
                save_config(config)
                print(f"Network Adjusted: New IP {detected_ip} applied.")
        return config

    # Fallback to detection if no config or invalid
    detected_ip = detect_host_ip()
    new_config = {"server_ip": detected_ip}
    save_config(new_config)
    return new_config

def save_config(config):
    import json
    with open(CONFIG_FILE, "w") as f:
        json.dump(config, f)
    # Update iPXE files whenever IP changes
    update_ipxe_files(config.get("server_ip", "127.0.0.1"))

def update_ipxe_files(ip):
    content = f"#!ipxe\n\ndhcp || reboot\n\nset server_ip {ip}\n\nkernel http://${{server_ip}}/pxe/vmlinuz initrd=initrd.img root=/dev/ram0 boot=live fetch=http://${{server_ip}}/pxe/rootfs.squashfs quiet splash vt.global_cursor_default=0\ninitrd http://${{server_ip}}/pxe/initrd.img\nboot\n"
    for filename in ["autoexec.ipxe", "boot.ipxe"]:
        with open(os.path.join(TFTP_BOOT, filename), "w") as f:
            f.write(content)

def save_iso_name(name: str):
    import json
    with open(METADATA_FILE, "w") as f:
        json.dump({"active_iso": name}, f)

def get_iso_name():
    import json
    if os.path.exists(METADATA_FILE):
        with open(METADATA_FILE, "r") as f:
            return json.load(f).get("active_iso", "None")
    return "None"

# Ensure directories exist
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(RAM_DISK, exist_ok=True)
os.makedirs(TFTP_BOOT, exist_ok=True)

@app.on_event("startup")
async def startup_event():
    # Sync IP configuration on startup
    config = get_config()
    update_ipxe_files(config.get("server_ip"))
    
    print("Startup sequence: Checking for boot components...")
    files_map = {
        "vmlinuz": "vmlinuz",
        "initrd.img": "initrd.img",
        "rootfs.squashfs": "rootfs.squashfs"
    }
    for src_name, dest_name in files_map.items():
        src_path = os.path.join(UPLOAD_DIR, src_name)
        dest_path = os.path.join(RAM_DISK, dest_name)
        if os.path.exists(src_path) and not os.path.exists(dest_path):
            try:
                print(f"Auto-loading {src_name} to RAM...")
                shutil.copy2(src_path, dest_path)
            except Exception as e:
                print(f"Failed to auto-load {src_name}: {e}")

class SystemStats(BaseModel):
    ram_used: float
    ram_total: float
    ram_percent: float
    tmpfs_used: float
    tmpfs_total: float
    tmpfs_percent: float
    unique_clients: int

@app.get("/api/stats", response_model=SystemStats)
async def get_stats(token: str = Depends(verify_token)):
    mem = psutil.virtual_memory()
    tmpfs = psutil.disk_usage(RAM_DISK)
    unique_clients = 0
    try:
        log_file = "/var/log/nginx/access.log"
        if os.path.exists(log_file):
            # Get last 200 lines to check recent activity
            result = subprocess.run(["tail", "-n", "200", log_file], capture_output=True, text=True)
            lines = result.stdout.splitlines()
            
            now = datetime.now()
            threshold = now - timedelta(seconds=15)
            unique_ips = set()
            
            for line in lines:
                if "/pxe/" in line:
                    match = re.search(r'(\d+\.\d+\.\d+\.\d+) .*? \[(.*?)\]', line)
                    if match:
                        ip = match.group(1)
                        ts_str = match.group(2).split(' ')[0] # 05/Feb/2026:12:39:33
                        try:
                            log_time = datetime.strptime(ts_str, "%d/%b/%Y:%H:%M:%S")
                            if log_time > threshold:
                                unique_ips.add(ip)
                        except:
                            continue
            unique_clients = len(unique_ips)
    except Exception as e:
        print(f"Error calculating realtime clients: {e}")

    return {
        "ram_used": mem.used,
        "ram_total": mem.total,
        "ram_percent": mem.percent,
        "tmpfs_used": tmpfs.used,
        "tmpfs_total": tmpfs.total,
        "tmpfs_percent": tmpfs.percent,
        "unique_clients": unique_clients
    }

@app.post("/api/upload/{file_type}")
async def upload_file(file_type: str, file: UploadFile = File(...), token: str = Depends(verify_token)):
    if file_type not in ["vmlinuz", "initrd", "rootfs", "iso"]:
        raise HTTPException(status_code=400, detail="Invalid file type")
    
    if file_type == "iso":
        return await handle_iso_upload(file)

    ext = ""
    if file_type == "vmlinuz": ext = ""
    elif file_type == "initrd": ext = ".img"
    elif file_type == "rootfs": ext = ".squashfs"
    
    file_path = os.path.join(UPLOAD_DIR, f"{file_type}{ext}")
    
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    return {"filename": file.filename, "type": file_type}

async def handle_iso_upload(file: UploadFile):
    # VALIDATION: Ensure no existing ISO is active
    if get_iso_name() != "None" or any(os.path.exists(os.path.join(RAM_DISK, f)) for f in ["vmlinuz", "initrd.img", "rootfs.squashfs"]):
        raise HTTPException(
            status_code=403, 
            detail="System Lock: An ISO is already active. Please perform a 'Factory Reset' to clear the system before uploading a new one."
        )

    # VALIDATION: Ensure file is an ISO
    if not file.filename.lower().endswith('.iso'):
        raise HTTPException(status_code=400, detail="Forbidden format: Only .iso files are allowed for orchestration.")

    iso_path = os.path.join(UPLOAD_DIR, "uploaded.iso")
    extract_path = os.path.join(UPLOAD_DIR, "iso_extract")
    
    components = ["vmlinuz", "initrd.img", "rootfs.squashfs"]
    for f in components:
        try:
            # Wipe from persistent storage
            p_path = os.path.join(UPLOAD_DIR, f)
            if os.path.exists(p_path): 
                os.remove(p_path)
            
            r_path = os.path.join(RAM_DISK, f)
            if os.path.exists(r_path): 
                os.remove(r_path)
        except Exception as e:
            print(f"Warning during cleanup: {e}")

    # Save ISO
    with open(iso_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    # Ensure ISO is readable
    os.chmod(iso_path, 0o666)
    
    # Clean and create extract dir
    if os.path.exists(extract_path):
        shutil.rmtree(extract_path)
    os.makedirs(extract_path)
    
    try:
        # Extract using 7z
        subprocess.run(["7z", "x", iso_path, f"-o{extract_path}", "-y"], check=True)
        
        found = {"vmlinuz": False, "initrd": False, "rootfs": False}
        
        for pattern in ["**/live/vmlinuz*", "**/casper/vmlinuz*", "**/vmlinuz*", "**/kernel*"]:
            matches = glob.glob(os.path.join(extract_path, pattern), recursive=True)
            if matches:
                 # Sort to pick the one with shortest path or specific criteria if needed
                 matches.sort(key=len)
                 dest_path = os.path.join(UPLOAD_DIR, "vmlinuz")
                 shutil.copy2(matches[0], dest_path)
                 os.chmod(dest_path, 0o666)  # Set wide permissions
                 found["vmlinuz"] = True
                 break
        
        # Initrd search
        for pattern in ["**/live/initrd*", "**/casper/initrd*", "**/initrd*", "**/initramfs*"]:
            matches = glob.glob(os.path.join(extract_path, pattern), recursive=True)
            if matches:
                 matches.sort(key=len)
                 dest_path = os.path.join(UPLOAD_DIR, "initrd.img")
                 shutil.copy2(matches[0], dest_path)
                 os.chmod(dest_path, 0o666)  # Set wide permissions
                 found["initrd"] = True
                 break
                 
        # SquashFS search
        for pattern in ["**/live/*.squashfs", "**/casper/*.squashfs", "**/*.squashfs"]:
            matches = glob.glob(os.path.join(extract_path, pattern), recursive=True)
            if matches:
                 matches.sort(key=len)
                 dest_path = os.path.join(UPLOAD_DIR, "rootfs.squashfs")
                 shutil.copy2(matches[0], dest_path)
                 os.chmod(dest_path, 0o666)
                 found["rootfs"] = True
                 break

        files_map = {
            "vmlinuz": "vmlinuz",
            "initrd.img": "initrd.img",
            "rootfs.squashfs": "rootfs.squashfs"
        }
        for src_name, dest_name in files_map.items():
            shutil.copy2(os.path.join(UPLOAD_DIR, src_name), os.path.join(RAM_DISK, dest_name))

        save_iso_name(file.filename)
        
        return {
            "status": "success",
            "message": "ISO extracted and loaded to RAM automatically",
            "extracted": found,
            "filename": file.filename
        }
    except Exception as e:
        if os.path.exists(extract_path): shutil.rmtree(extract_path)
        raise HTTPException(status_code=500, detail=f"ISO Extraction failed: {str(e)}")

@app.post("/api/deploy")
async def deploy_to_ram(token: str = Depends(verify_token)):
    try:
        # Expected names in UPLOAD_DIR (source)
        # Expected names in RAM_DISK (destination)
        files_map = {
            "vmlinuz": "vmlinuz",
            "initrd.img": "initrd.img",
            "rootfs.squashfs": "rootfs.squashfs"
        }
        
        for src_name, dest_name in files_map.items():
            src_path = os.path.join(UPLOAD_DIR, src_name)
            if not os.path.exists(src_path):
                 return JSONResponse(status_code=400, content={"message": f"Missing component: {src_name}. Please upload ISO first."})
            
            dest_path = os.path.join(RAM_DISK, dest_name)
            shutil.copy2(src_path, dest_path)
            
        return {"status": "success", "message": "PXE components loaded to RAM Cache"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/unload")
async def unload_from_ram(token: str = Depends(verify_token)):
    try:
        files = ["vmlinuz", "initrd.img", "rootfs.squashfs"]
        for f in files:
            path = os.path.join(RAM_DISK, f)
            if os.path.exists(path):
                os.remove(path)
        return {"status": "success", "message": "RAM Cache cleared"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/reset")
async def factory_reset(token: str = Depends(verify_token)):
    try:
        # 1. Thoroughly clear UPLOAD_DIR (data-source)
        for item in os.listdir(UPLOAD_DIR):
            item_path = os.path.join(UPLOAD_DIR, item)
            try:
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
            except Exception as e:
                print(f"Failed to delete {item_path}: {e}")
        
        for item in os.listdir(RAM_DISK):
            item_path = os.path.join(RAM_DISK, item)
            try:
                if os.path.isfile(item_path) or os.path.islink(item_path):
                    os.unlink(item_path)
            except Exception as e:
                print(f"Failed to delete RAM item {item_path}: {e}")
        
        try:
            log_file = "/var/log/nginx/access.log"
            if os.path.exists(log_file):
                with open(log_file, "w") as f:
                    f.truncate(0)
        except Exception as e:
            print(f"Failed to clear nginx logs: e")
            
        return {"status": "success", "message": "Full system wipe complete. All folders and logs cleared."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Reset failed: {str(e)}")

@app.get("/api/files")
async def list_files(token: str = Depends(verify_token)):
    uploaded = os.listdir(UPLOAD_DIR)
    boot_components = ["vmlinuz", "initrd.img", "rootfs.squashfs"]
    deployed = [f for f in os.listdir(RAM_DISK) if f in boot_components]
    return {
        "uploaded": uploaded, 
        "deployed": deployed,
        "active_iso": get_iso_name()
    }

@app.get("/api/logs")
async def get_logs(token: str = Depends(verify_token)):
    try:
        log_file = "/var/log/nginx/access.log"
        if not os.path.exists(log_file):
            return {"logs": ["Waiting for traffic..."]}
            
        # Read the last 100 lines to ensure we have enough after filtering
        result = subprocess.run(["tail", "-n", "100", log_file], capture_output=True, text=True)
        all_lines = result.stdout.splitlines()
        
        filtered = [
            line for line in all_lines 
            if "/api/stats" not in line and "/api/files" not in line and "/api/logs" not in line and "/favicon.ico" not in line
        ]
        
        # Return newest first, capped at 50
        filtered.reverse()
        return {"logs": filtered[:50]}
    except Exception as e:
        return {"logs": [f"Error reading logs: {str(e)}"]}

@app.get("/api/networks")
async def get_networks(token: str = Depends(verify_token)):
    """Returns a list of available network interfaces and their IPs."""
    interfaces = psutil.net_if_addrs()
    networks = []
    
    for iface, addrs in interfaces.items():
        # Filter out noisy virtual interfaces
        if iface == 'lo' or iface.startswith('docker') or iface.startswith('br-') or iface.startswith('veth'):
            continue
            
        for addr in addrs:
            if addr.family == socket.AF_INET: # Only IPv4
                networks.append({
                    "iface": iface,
                    "ip": addr.address
                })
    return networks

@app.get("/api/config")
async def read_config(token: str = Depends(verify_token)):
    return get_config()

@app.post("/api/config")
async def update_config(config: dict, token: str = Depends(verify_token)):
    if "server_ip" not in config:
        raise HTTPException(status_code=400, detail="server_ip is required")
    save_config(config)
    return {"status": "success", "message": "Configuration updated and iPXE scripts refreshed"}

@app.get("/api/verify-auth")
async def verify_auth(token: str = Depends(verify_token)):
    return {"status": "success", "message": "Authenticated"}

# Serve Frontend
app.mount("/", StaticFiles(directory="/app/frontend", html=True), name="frontend")
