#!/usr/init/env python3
"""
CT Wishlink Generator – Premium Windows Desktop App
Features: Direct Download of FFmpeg/FFprobe binaries into local 'ffmpeg_bin' with Live % Progress,
Live Terminal Logs, PyInstaller support, Smart Image Compression (<500KB skipped), 
Advanced Error Handling, Full Occasions List, Hidden CMD Window for Audio, Smart Live Theme Preview.
"""

import subprocess
import sys
import importlib
import os
import tempfile
import json
import threading
import webbrowser
from io import BytesIO
import urllib.parse
import colorsys
import zipfile
from tkinter import Canvas
import tkinter.messagebox as msgbox

# ==================== AUTO‑INSTALL BOOTSTRAP ====================
REQUIRED = {
    'customtkinter': 'customtkinter',
    'qrcode': 'qrcode',
    'PIL': 'pillow',
    'requests': 'requests',
    'pydub': 'pydub'
}

def bootstrap():
    if getattr(sys, 'frozen', False):
        return
        
    missing = []
    for mod, pkg in REQUIRED.items():
        try:
            importlib.import_module(mod)
        except ImportError:
            missing.append(pkg)
    if missing:
        print(f"Installing missing packages: {', '.join(missing)}")
        subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
        subprocess.check_call([sys.executable] + sys.argv)
        sys.exit(0)

bootstrap()

import customtkinter as ctk
from PIL import Image
import qrcode
import requests
from pydub import AudioSegment

# ==================== CONFIG & LOCAL BIN PATHS ====================
CONFIG_FILE = "config.json"
SETUP_MARKER = "ffmpeg_setup_done.flag"
LOCAL_BIN_DIR = os.path.join(os.path.abspath("."), "ffmpeg_bin")

MAX_FILE_BYTES = 10 * 1024 * 1024  # 10 MB limit
MAX_MSG_LENGTH = 150 
SMART_COMPRESS_LIMIT = 500 * 1024  # 500 KB limit for images

# 👇(PASTE YOUR YOUTUBE TUTORIAL LINK HERE) 👇
TUTORIAL_URL = "https://subeesh-ct.github.io/Studio-QR-code-wishes/redirect.html" 
# 👆 ------------------------------------------------------------------------- 👆

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ==================== HELPERS ====================
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def set_window_icon(window):
    icon_path = resource_path("CT-Stdio.ico")
    if os.path.exists(icon_path):
        try:
            window.iconbitmap(icon_path)
        except Exception:
            pass
        def apply_delayed_icon():
            try:
                window.iconbitmap(icon_path)
            except Exception:
                pass
        window.after(200, apply_delayed_icon)

def check_internet():
    try:
        requests.get("https://www.google.com", timeout=3)
        return True
    except Exception:
        return False

def format_size(size_bytes):
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    else:
        return f"{size_bytes / (1024 * 1024):.1f} MB"

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return (
                data.get("base_url", "").strip(), 
                data.get("studio_name", "").strip(),
                data.get("imgbb_api", "").strip(),
                data.get("cloud_name", "").strip(),
                data.get("upload_preset", "").strip()
            )
    return "", "", "", "", ""

def save_config(url, studio_name, imgbb_api, cloud_name, upload_preset):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "base_url": url.strip(),
            "studio_name": studio_name.strip(),
            "imgbb_api": imgbb_api.strip(),
            "cloud_name": cloud_name.strip(),
            "upload_preset": upload_preset.strip()
        }, f, indent=4)

def center_window(win, width, height):
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = (sw - width) // 2
    y = (sh - height) // 2
    win.geometry(f"{width}x{height}+{x}+{y}")

# ==================== INITIAL SETUP WINDOW (WITH LIVE % DOWNLOAD) ====================
class SetupWindow(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Initial Setup Required")
        self.resizable(False, False)
        set_window_icon(self)
        center_window(self, 520, 440)
        
        self.protocol("WM_DELETE_WINDOW", self.on_close)

        frame = ctk.CTkFrame(self, corner_radius=15)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(frame, text="⚙️ Component Installation", font=ctk.CTkFont(size=18, weight="bold")).pack(pady=(10, 5))
        ctk.CTkLabel(frame, text="Downloading FFmpeg/FFprobe binaries into local 'ffmpeg_bin'.\nPlease do not close this window.", 
                     font=ctk.CTkFont(size=12), text_color="gray", justify="center").pack(pady=(0, 10))

        # Determinate Progress Bar for accurate % loading
        self.progress = ctk.CTkProgressBar(frame, mode="determinate", width=440)
        self.progress.pack(pady=5)
        self.progress.set(0)

        self.log_box = ctk.CTkTextbox(frame, height=130, width=440, state="disabled", fg_color="#1E1E1E", text_color="#00FF00", font=ctk.CTkFont(family="Consolas", size=11))
        self.log_box.pack(pady=10)

        self.start_btn = ctk.CTkButton(frame, text="Download & Setup Now", width=200, height=36, command=self.run_setup)
        self.start_btn.pack(pady=(5, 10))

    def append_log(self, text):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", text + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")

    def run_setup(self):
        if not check_internet():
            msgbox.showerror("No Internet", "Please connect to the internet to download required components.", parent=self)
            return

        self.start_btn.configure(state="disabled")
        self.append_log(">>> Starting direct binary download...")

        threading.Thread(target=self._download_worker, daemon=True).start()

    def _download_worker(self):
        try:
            os.makedirs(LOCAL_BIN_DIR, exist_ok=True)
            self.after(0, self.append_log, ">>> Created local 'ffmpeg_bin' directory.")

            files_to_download = {
                "ffmpeg.exe": "https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v4.4.1/ffmpeg-4.4.1-win-64.zip",
                "ffprobe.exe": "https://github.com/ffbinaries/ffbinaries-prebuilt/releases/download/v4.4.1/ffprobe-4.4.1-win-64.zip"
            }

            total_files = len(files_to_download)
            current_index = 0

            for name, url in files_to_download.items():
                current_index += 1
                self.after(0, self.append_log, f">>> Downloading {name} ({current_index}/{total_files})...")
                
                response = requests.get(url, stream=True)
                response.raise_for_status()
                
                total_size = int(response.headers.get('content-length', 0))
                downloaded_size = 0
                chunk_data = bytearray()

                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        chunk_data.extend(chunk)
                        downloaded_size += len(chunk)
                        if total_size > 0:
                            file_pct = downloaded_size / total_size
                            # Overall progress calculation
                            overall_pct = ((current_index - 1) / total_files) + (file_pct / total_files)
                            self.after(0, self.progress.set, overall_pct)

                self.after(0, self.append_log, f">>> Extracting {name} into 'ffmpeg_bin'...")
                with zipfile.ZipFile(BytesIO(chunk_data)) as z:
                    z.extractall(LOCAL_BIN_DIR)
                
                self.after(0, self.append_log, f">>> Successfully saved: {name}")

            self.after(0, self.progress.set, 1.0)
            self.after(0, self.append_log, ">>> All files safely stored in your app folder!")

            with open(SETUP_MARKER, "w") as f:
                f.write("setup_completed")
            
            self.after(0, self.append_log, ">>> Setup 100% Completed!")
            self.after(1000, self._setup_success)
        except Exception as e:
            self.after(0, self._setup_error, str(e))

    def _setup_success(self):
        msgbox.showinfo("Success", "Components downloaded directly to folder! Click OK to launch.", parent=self)
        self.destroy()

    def _setup_error(self, err):
        self.start_btn.configure(state="normal")
        self.append_log(f"ERROR: {err}")
        msgbox.showerror("Error", f"Failed to download components:\n{err}", parent=self)

    def on_close(self):
        self.destroy()
        sys.exit(0)


# ==================== SMART MEDIA PROCESSORS (WITH HIDDEN CMD) ====================
def init_ffmpeg_path():
    ffmpeg_exe = os.path.join(LOCAL_BIN_DIR, "ffmpeg.exe")
    ffprobe_exe = os.path.join(LOCAL_BIN_DIR, "ffprobe.exe")
    
    if os.path.exists(ffmpeg_exe):
        AudioSegment.converter = ffmpeg_exe
    if os.path.exists(ffprobe_exe):
        AudioSegment.ffmpeg = ffmpeg_exe
        AudioSegment.ffprobe = ffprobe_exe
        os.environ["PATH"] += os.pathsep + LOCAL_BIN_DIR

    if os.name == 'nt':
        import subprocess
        subprocess.Popen = patch_subprocess_popen(subprocess.Popen)

    return AudioSegment

def patch_subprocess_popen(original_popen):
    class PatchedPopen(original_popen):
        def __init__(self, *args, **kwargs):
            if os.name == 'nt':
                creationflags = kwargs.get('creationflags', 0)
                kwargs['creationflags'] = creationflags | 0x08000000 # CREATE_NO_WINDOW
            super().__init__(*args, **kwargs)
    return PatchedPopen

def compress_image_to_webp(file_path):
    orig_size = os.path.getsize(file_path)
    
    if orig_size < SMART_COMPRESS_LIMIT:
        with open(file_path, "rb") as f:
            buffer = BytesIO(f.read())
        return buffer, False 

    img = Image.open(file_path).convert("RGB")
    if max(img.size) > 2000:
        img.thumbnail((2000, 2000), Image.LANCZOS)
    buffer = BytesIO()
    quality = 95 if orig_size < 1 * 1024 * 1024 else 85
    img.save(buffer, format="WEBP", quality=quality)
    buffer.seek(0)
    return buffer, True

def upload_to_imgbb(file_obj, api_key, is_compressed=True):
    url = "https://api.imgbb.com/1/upload"
    try:
        filename = "img.webp" if is_compressed else "img.orig"
        mime_type = "image/webp" if is_compressed else "application/octet-stream"
        
        resp = requests.post(url, data={"key": api_key}, files={"image": (filename, file_obj, mime_type)}, timeout=60)
        if not resp.ok:
             raise Exception(f"ImgBB Server Error ({resp.status_code}). Please check if your ImgBB API Key is correct.")

        json_data = resp.json()
        if json_data.get("success"):
            return json_data["data"]["url"]
        else:
            raise Exception(json_data.get("error", {}).get("message", "Unknown ImgBB Error"))
    except ValueError:
        raise Exception("ImgBB returned an invalid response. Your API Key might be wrong.")
    except Exception as e:
        raise Exception(f"ImgBB Upload failed: {str(e)}")

def compress_audio_to_mp3(file_path):
    AudioSegment = init_ffmpeg_path()
    temp_mp3 = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
    temp_mp3.close()
    
    audio = AudioSegment.from_file(file_path)
    orig_size = os.path.getsize(file_path)
    bitrate = "192k" if orig_size < 1 * 1024 * 1024 else "128k"
    
    audio.export(temp_mp3.name, format="mp3", bitrate=bitrate)
    return temp_mp3.name

def upload_to_cloudinary(file_path, cloud_name, upload_preset):
    url = f"https://api.cloudinary.com/v1_1/{cloud_name}/upload"
    try:
        with open(file_path, 'rb') as f:
            resp = requests.post(url, data={"upload_preset": upload_preset, "resource_type": "video"}, files={"file": f}, timeout=120)
            
        if not resp.ok:
            raise Exception(f"Cloudinary Error ({resp.status_code}). Please check your Cloud Name and Upload Preset in Settings.")

        json_data = resp.json()
        if "secure_url" in json_data:
            return json_data["secure_url"]
        else:
            raise Exception("Cloudinary URL not found in response.")
    except ValueError:
        raise Exception("Cloudinary returned an invalid response. Your Cloud Name or Upload Preset might be wrong.")
    except Exception as e:
        raise Exception(f"Cloudinary Upload failed: {str(e)}")

# ==================== MODALS ====================
class SettingsModal(ctk.CTkToplevel):
    def __init__(self, parent, c_url, c_studio, c_imgbb, c_cloud, c_preset, on_save, forced=False):
        super().__init__(parent)
        self.parent = parent
        self.on_save_callback = on_save
        self.forced = forced
        
        self.title("App Settings" if not forced else "Initial Setup Required")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        set_window_icon(self)
        
        if self.forced: self.protocol("WM_DELETE_WINDOW", self.on_forced_close)
        
        w, h = 480, 520
        center_window(self, w, h)
        
        frame = ctk.CTkFrame(self, corner_radius=15)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(frame, text="Base URL *", font=ctk.CTkFont(weight="bold")).pack(pady=(5,2))
        self.url_entry = ctk.CTkEntry(frame, width=380)
        self.url_entry.insert(0, c_url)
        self.url_entry.pack(pady=(0,10), padx=20)
        
        ctk.CTkLabel(frame, text="ImgBB API Key (For Images) *", font=ctk.CTkFont(weight="bold")).pack(pady=(2,2))
        self.imgbb_entry = ctk.CTkEntry(frame, width=380)
        self.imgbb_entry.insert(0, c_imgbb)
        self.imgbb_entry.pack(pady=(0,10), padx=20)

        ctk.CTkLabel(frame, text="Cloudinary Cloud Name (For Audio) *", font=ctk.CTkFont(weight="bold")).pack(pady=(2,2))
        self.cloud_entry = ctk.CTkEntry(frame, width=380)
        self.cloud_entry.insert(0, c_cloud)
        self.cloud_entry.pack(pady=(0,10), padx=20)

        ctk.CTkLabel(frame, text="Cloudinary Upload Preset *", font=ctk.CTkFont(weight="bold")).pack(pady=(2,2))
        self.preset_entry = ctk.CTkEntry(frame, width=380)
        self.preset_entry.insert(0, c_preset)
        self.preset_entry.pack(pady=(0,10), padx=20)

        ctk.CTkLabel(frame, text="Studio Name", font=ctk.CTkFont(weight="bold")).pack(pady=(2,2))
        self.studio_entry = ctk.CTkEntry(frame, width=380)
        self.studio_entry.insert(0, c_studio)
        self.studio_entry.pack(pady=(0,10), padx=20)

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=15)
        
        ctk.CTkButton(btn_frame, text="🎥 How to Setup", width=130,
                      command=lambda: webbrowser.open(TUTORIAL_URL)).pack(side="left")
        
        ctk.CTkButton(btn_frame, text="Save & Continue", width=130,
                      command=self.save).pack(side="right")

        self.status = ctk.CTkLabel(frame, text="", text_color="green")
        self.status.pack(pady=2)

    def save(self):
        new_url = self.url_entry.get().strip()
        new_studio = self.studio_entry.get().strip()
        new_imgbb = self.imgbb_entry.get().strip()
        new_cloud = self.cloud_entry.get().strip()
        new_preset = self.preset_entry.get().strip()
        
        if not all([new_url, new_imgbb, new_cloud, new_preset]):
            self.status.configure(text="All * fields are required!", text_color="red")
            return
            
        save_config(new_url, new_studio, new_imgbb, new_cloud, new_preset)
        self.on_save_callback(new_url, new_studio, new_imgbb, new_cloud, new_preset)
        
        if self.forced: self.parent.deiconify()
        self.destroy()

    def on_forced_close(self):
        msgbox.showwarning("Required", "You must fill in the Settings to use the application.")
        self.parent.destroy()

class LoadingPopup(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Processing")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        set_window_icon(self)
        center_window(self, 320, 120)
        frame = ctk.CTkFrame(self, corner_radius=15)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        ctk.CTkLabel(frame, text="Processing & Uploading...\nPlease wait", font=ctk.CTkFont(size=13)).pack(pady=(15,10))
        self.progress = ctk.CTkProgressBar(frame, mode="indeterminate", width=250)
        self.progress.pack(pady=10)
        self.progress.start()

    def stop(self):
        self.progress.stop()
        self.destroy()

class SuccessReportModal(ctk.CTkToplevel):
    def __init__(self, parent, report_data, on_ok_callback):
        super().__init__(parent)
        self.title("Upload Successful")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        set_window_icon(self)
        center_window(self, 400, 260)
        
        self.on_ok = on_ok_callback
        
        frame = ctk.CTkFrame(self, corner_radius=15)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(frame, text="✅ Upload Successful!", font=ctk.CTkFont(size=18, weight="bold"), text_color="#2FA37A").pack(pady=(10,15))
        
        if report_data.get('img'):
            i_orig = format_size(report_data['img']['orig'])
            i_new = format_size(report_data['img']['new'])
            
            if report_data['img'].get('skipped'):
                ctk.CTkLabel(frame, text=f"🖼️ Image: {i_orig} (Original Quality Maintained)", font=ctk.CTkFont(size=13)).pack(pady=2)
            else:
                ctk.CTkLabel(frame, text=f"🖼️ Image: {i_orig} ➔ {i_new}", font=ctk.CTkFont(size=13)).pack(pady=2)
            
        if report_data.get('audio'):
            a_orig = format_size(report_data['audio']['orig'])
            a_new = format_size(report_data['audio']['new'])
            ctk.CTkLabel(frame, text=f"🎵 Audio: {a_orig} ➔ {a_new}", font=ctk.CTkFont(size=13)).pack(pady=2)
            
        if not report_data.get('img') and not report_data.get('audio'):
            ctk.CTkLabel(frame, text="Generated without media files.", font=ctk.CTkFont(size=13)).pack(pady=5)
            
        ctk.CTkButton(frame, text="OK", width=120, command=self.close_modal).pack(pady=(20,10))

    def close_modal(self):
        self.on_ok()
        self.destroy()

# ==================== FORM FRAME ====================
class FormFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, app):
        super().__init__(master, corner_radius=12, fg_color="transparent")
        self.app = app
        self.img_path = None
        self.audio_path = None
        self._create_widgets()

    def _create_widgets(self):
        ctk.CTkLabel(self, text="✨ Create Your Wish", font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(15,10))

        ctk.CTkLabel(self, text="Recipient Name *", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10,2))
        self.name_entry = ctk.CTkEntry(self, placeholder_text="Enter name", height=40)
        self.name_entry.pack(fill="x", pady=(0,10))

        ctk.CTkLabel(self, text="Sender Name (Optional)", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5,2))
        self.sender_entry = ctk.CTkEntry(self, placeholder_text="Enter your name", height=36)
        self.sender_entry.pack(fill="x", pady=(0,10))

        ctk.CTkLabel(self, text="Theme *", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5,2))
        self.theme_combo = ctk.CTkComboBox(self, values=["Select Theme", "Girl Theme", "Boy Theme", "Both/Neutral"], state="readonly", height=36, command=self._on_theme_change)
        self.theme_combo.set("Select Theme")
        self.theme_combo.pack(fill="x", pady=(0,10))

        ctk.CTkLabel(self, text="Occasion Theme *", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5,2))
        
        occasions = [
            "Select Occasion", "Birthday", "Anniversary", "Wedding", "Graduation", "Farewell", 
            "Valentine's Day", "Mother's Day", "Father's Day", "Diwali", 
            "Pongal", "Eid", "Christmas", "New Year", "Congratulations", 
            "Get Well Soon", "Engagement"
        ]
        self.occasion_combo = ctk.CTkComboBox(self, values=occasions, state="readonly", command=self._on_occasion_change, height=36)
        self.occasion_combo.set("Select Occasion")
        self.occasion_combo.pack(fill="x", pady=(0,5))
        
        # --- Containers for dynamic elements ---
        # NOTE: Not packing them initially keeps them hidden without taking up space
        self.entry_container = ctk.CTkFrame(self, fg_color="transparent")
        self.custom_entry = ctk.CTkEntry(self.entry_container, placeholder_text="Enter Display Title")
        self.custom_entry.pack(fill="x")
        
        self.preview_container = ctk.CTkFrame(self, fg_color="transparent")
        self.preview_btn = ctk.CTkButton(self.preview_container, text="👁️ View Theme Demo", command=self.preview_theme, 
                                         fg_color="#34A853", hover_color="#2A8542", height=32, font=ctk.CTkFont(weight="bold"))
        self.preview_btn.pack(pady=0)

        ctk.CTkLabel(self, text="Event Date (Optional)", font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10,2))
        self.date_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.date_frame.pack(fill="x", pady=(0,10))
        
        days = ["Day"] + [str(i).zfill(2) for i in range(1, 32)]
        months = ["Month", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

        self.month_combo = ctk.CTkComboBox(self.date_frame, values=months, width=90, state="readonly")
        self.month_combo.set("Month")
        self.month_combo.pack(side="left", padx=(0,5))

        self.day_combo = ctk.CTkComboBox(self.date_frame, values=days, width=70, state="readonly")
        self.day_combo.set("Day")
        self.day_combo.pack(side="left", padx=5)

        self.year_entry = ctk.CTkEntry(self.date_frame, placeholder_text="Year", width=80)
        self.year_entry.pack(side="left", padx=5)

        msg_header_frame = ctk.CTkFrame(self, fg_color="transparent")
        msg_header_frame.pack(fill="x", pady=(10,2))
        ctk.CTkLabel(msg_header_frame, text="Message *", font=ctk.CTkFont(weight="bold")).pack(side="left")
        
        self.counter_label = ctk.CTkLabel(msg_header_frame, text=f"0 / {MAX_MSG_LENGTH} chars", text_color="gray", font=ctk.CTkFont(size=12))
        self.counter_label.pack(side="right")

        self.msg_text = ctk.CTkTextbox(self, height=90)
        self.msg_text.pack(fill="x", pady=(0,10))
        self.msg_text._enforcing = False
        self.msg_text.bind("<KeyRelease>", self._on_msg_keyrelease)
        self.msg_text.bind("<<Modified>>", self._on_msg_modified)

        # ====== MEDIA FRAME ======
        media_frame = ctk.CTkFrame(self, corner_radius=10)
        media_frame.pack(fill="x", pady=10, padx=10)
        media_frame.columnconfigure(0, weight=1, uniform="col")
        media_frame.columnconfigure(1, weight=1, uniform="col")

        # IMAGE COLUMN
        ctk.CTkLabel(media_frame, text="Image (Optional)").grid(row=0, column=0, sticky="w", padx=15, pady=(10,2))
        self.img_label = ctk.CTkLabel(media_frame, text="No file selected", text_color="gray")
        self.img_label.grid(row=1, column=0, sticky="w", padx=15)
        ctk.CTkButton(media_frame, text="Select Image", width=130, command=self.select_image).grid(row=2, column=0, padx=15, pady=(5,10), sticky="ew")

        # AUDIO COLUMN
        ctk.CTkLabel(media_frame, text="Audio File (Optional)").grid(row=0, column=1, sticky="w", padx=15, pady=(10,2))
        self.audio_label = ctk.CTkLabel(media_frame, text="No file selected", text_color="gray")
        self.audio_label.grid(row=1, column=1, sticky="w", padx=15)
        ctk.CTkButton(media_frame, text="Select Audio", width=130, command=self.select_audio).grid(row=2, column=1, padx=15, pady=(5,10), sticky="ew")

        self.gen_btn = ctk.CTkButton(self, text="Generate Link & QR", command=self.app.start_generation,
                                     width=240, height=44, corner_radius=12, font=ctk.CTkFont(size=15, weight="bold"))
        self.gen_btn.pack(pady=20)

    def _on_theme_change(self, choice):
        self._update_visibility()

    def _on_occasion_change(self, choice):
        if choice == "Select Occasion":
            self.custom_entry.delete(0, "end")
        else:
            default_titles = {
                "Birthday": "A BIRTHDAY WISH",
                "Anniversary": "HAPPY ANNIVERSARY",
                "Wedding": "HAPPY WEDDING",
                "Graduation": "HAPPY GRADUATION",
                "Farewell": "HAPPY FAREWELL",
                "Valentine's Day": "HAPPY VALENTINE'S DAY",
                "Mother's Day": "HAPPY MOTHER'S DAY",
                "Father's Day": "HAPPY FATHER'S DAY",
                "Diwali": "HAPPY DIWALI",
                "Pongal": "HAPPY PONGAL",
                "Eid": "EID MUBARAK",
                "Christmas": "MERRY CHRISTMAS",
                "New Year": "HAPPY NEW YEAR",
                "Congratulations": "CONGRATULATIONS",
                "Get Well Soon": "GET WELL SOON",
                "Engagement": "HAPPY ENGAGEMENT"
            }
            self.custom_entry.delete(0, "end")
            self.custom_entry.insert(0, default_titles.get(choice, f"HAPPY {choice.upper()}"))
            
        self._update_visibility()

    def _update_visibility(self):
        theme = self.theme_combo.get()
        occ = self.occasion_combo.get()
        
        # 1. Text Box Container (pack immediately AFTER the occasion dropdown so it stays in place!)
        if occ != "Select Occasion":
            if not self.entry_container.winfo_manager():
                self.entry_container.pack(after=self.occasion_combo, fill="x", pady=(0, 5))
        else:
            if self.entry_container.winfo_manager():
                self.entry_container.pack_forget()

        # 2. Preview Button Container (pack immediately AFTER the Text Box!)
        if theme != "Select Theme" and occ != "Select Occasion":
            if not self.preview_container.winfo_manager():
                self.preview_container.pack(after=self.entry_container, fill="x", pady=(0, 10))
        else:
            if self.preview_container.winfo_manager():
                self.preview_container.pack_forget()

    def preview_theme(self):
        theme = self.theme_combo.get()
        occ = self.occasion_combo.get()
        title = self.custom_entry.get().strip()
            
        if not self.app.base_url:
            msgbox.showerror("Settings Missing", "Base URL is required to generate a preview. Please update Settings.", parent=self.app)
            return
            
        # Magic Shortcut: If Engagement, pass "custom" so HTML uses the special background
        url_occ = "custom" if occ == "Engagement" else occ

        params = {
            "name": "Your Name",
            "theme": theme,
            "occ": url_occ,
            "title": title if title else f"HAPPY {occ.upper()}",
            "msg": "Artificial intelligence is rapidly transforming how we live, work, and communicate. By processing massive amounts of data in seconds, advanced algorit",
            "date": "Jan 14, 2026",
            "sender": "Sender Name",
            "img": "https://i.ibb.co/hxngQbss/img.jpg",
            "audio": "https://res.cloudinary.com/lx8tfhkq/video/upload/v1785059729/kfsjbdpk28zvqpoy8u3g.mp3"
        }
        
        if self.app.studio_name:
            params["studio_name"] = self.app.studio_name
        else:
            params["studio_name"] = "Coding Theriyuma ¿" 
            
        qs = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
        base = self.app.base_url.rstrip("/")
        preview_url = f"{base}/?{qs}" if "?" not in base else f"{base}&{qs}"
        
        webbrowser.open(preview_url)

    def _on_msg_keyrelease(self, event): self._enforce_msg_limit()
    def _on_msg_modified(self, event): 
        self._enforce_msg_limit()
        self.msg_text.edit_modified(False)  

    def _enforce_msg_limit(self):
        if self.msg_text._enforcing: return
        self.msg_text._enforcing = True
        text = self.msg_text.get("1.0", "end-1c")
        if len(text) > MAX_MSG_LENGTH:
            self.msg_text.delete("1.0", "end")
            self.msg_text.insert("1.0", text[:MAX_MSG_LENGTH])
        current_len = len(self.msg_text.get("1.0", "end-1c"))
        self.counter_label.configure(text=f"{current_len} / {MAX_MSG_LENGTH} chars", text_color="orange" if current_len >= MAX_MSG_LENGTH else "gray")
        self.msg_text._enforcing = False

    def select_image(self):
        path = ctk.filedialog.askopenfilename(title="Select an Image", filetypes=[("All Files", "*.*")])
        if path:
            if os.path.getsize(path) > MAX_FILE_BYTES:
                msgbox.showerror("File Too Large", "Please select an image smaller than 10 MB.", parent=self)
                return
            self.img_path = path
            self.img_label.configure(text=os.path.basename(path), text_color="green")

    def select_audio(self):
        path = ctk.filedialog.askopenfilename(title="Select Audio", filetypes=[("All Files", "*.*")])
        if path:
            if os.path.getsize(path) > MAX_FILE_BYTES:
                msgbox.showerror("File Too Large", "Please select an audio file smaller than 10 MB.", parent=self)
                return
            self.audio_path = path
            self.audio_label.configure(text=os.path.basename(path), text_color="green")

    def reset_form(self):
        self.name_entry.delete(0, "end")
        self.sender_entry.delete(0, "end")
        self.month_combo.set("Month")
        self.day_combo.set("Day")
        self.year_entry.delete(0, "end")
        self.msg_text.delete("1.0", "end")
        self.counter_label.configure(text=f"0 / {MAX_MSG_LENGTH} chars", text_color="gray")
        
        self.theme_combo.set("Select Theme")
        self.occasion_combo.set("Select Occasion")
        self.custom_entry.delete(0, "end")
        self._update_visibility()
        
        self.img_path = None
        self.img_label.configure(text="No file selected", text_color="gray")
        self.audio_path = None
        self.audio_label.configure(text="No file selected", text_color="gray")

# ==================== LIVE COLOR PICKER ====================
class LiveColorPicker(ctk.CTkFrame):
    def __init__(self, master, title, initial_color, on_color_change):
        super().__init__(master, corner_radius=10)
        self.color = initial_color
        self.on_color_change = on_color_change
        ctk.CTkLabel(self, text=title, font=ctk.CTkFont(weight="bold")).pack(anchor="w", padx=15, pady=(10,5))
        self.canvas = Canvas(self, width=300, height=30, highlightthickness=0, bg="#0a0a0a")
        self.canvas.pack(padx=15, pady=(0,5))
        self._draw_hue_gradient()
        preview_frame = ctk.CTkFrame(self, fg_color="transparent")
        preview_frame.pack(anchor="w", padx=15, pady=(5,5))
        self.preview = ctk.CTkLabel(preview_frame, text="", width=30, height=30, corner_radius=6, fg_color=initial_color)
        self.preview.pack(side="left", padx=(0,10))
        self.hex_label = ctk.CTkLabel(preview_frame, text=initial_color, font=ctk.CTkFont(weight="bold"))
        self.hex_label.pack(side="left")
        self.presets_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.presets_frame.pack(anchor="w", padx=15, pady=(5,10))
        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_click)

    def _draw_hue_gradient(self):
        for x in range(300):
            r, g, b = colorsys.hsv_to_rgb(x / 300, 1.0, 1.0)
            self.canvas.create_line(x, 0, x, 30, fill=f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}", width=1)

    def _on_canvas_click(self, event):
        w = self.canvas.winfo_width()
        x = min(max(event.x, 0), w-1)
        r, g, b = colorsys.hsv_to_rgb(x / w, 1.0, 1.0)
        self.set_color(f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}")

    def set_color(self, hex_color):
        self.color = hex_color
        self.preview.configure(fg_color=hex_color)
        self.hex_label.configure(text=hex_color)
        self.on_color_change(hex_color)

    def set_presets(self, preset_list):
        for widget in self.presets_frame.winfo_children(): widget.destroy()
        for color in preset_list:
            ctk.CTkButton(self.presets_frame, text="", width=24, height=24, corner_radius=4, fg_color=color, hover_color=color, command=lambda c=color: self.set_color(c)).pack(side="left", padx=2, pady=2)

class OutputFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, app, url):
        super().__init__(master, corner_radius=12, fg_color="transparent", orientation="vertical")
        self.app = app
        self.url = url
        self.fg_color, self.bg_color = "#000000", "#FFFFFF"
        self.qr_pil_image = None
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="🎉 Your Wish Link is Ready!", font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(20,15))
        url_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#2B2B2B")
        url_frame.pack(fill="x", padx=30, pady=(5,15))
        self.url_entry = ctk.CTkEntry(url_frame, height=40, font=ctk.CTkFont(size=13, weight="bold"), text_color="#00C2FF", state="normal")
        self.url_entry.insert(0, self.url)
        self.url_entry.configure(state="readonly")
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(15,10), pady=12)
        ctk.CTkButton(url_frame, text="Copy Link", width=90, command=self.copy_url).pack(side="right", padx=(0,15), pady=12)

        qr_container = ctk.CTkFrame(self, corner_radius=10)
        qr_container.pack(fill="x", padx=30, pady=(5,10))
        self.qr_label = ctk.CTkLabel(qr_container, text="", width=240, height=240, fg_color="white", corner_radius=8)
        self.qr_label.pack(pady=15)
        ctk.CTkButton(qr_container, text="Download QR (PNG)", width=180, command=self.download_qr).pack(pady=(0,15))

        pickers_frame = ctk.CTkFrame(self, fg_color="transparent")
        pickers_frame.pack(fill="x", padx=30, pady=10)
        fg_picker = LiveColorPicker(pickers_frame, "Foreground Color", self.fg_color, on_color_change=self.set_fg_color)
        fg_picker.pack(fill="x", pady=(0,10))
        fg_picker.set_presets(["#000000", "#00008B", "#8B0000", "#006400", "#800080", "#FF8C00"])
        
        bg_picker = LiveColorPicker(pickers_frame, "Background Color", self.bg_color, on_color_change=self.set_bg_color)
        bg_picker.pack(fill="x")
        bg_picker.set_presets(["#FFFFFF", "#000000", "#D3D3D3", "#FFFF00", "#ADD8E6"])

        ctk.CTkButton(self, text="Create Another Wish", width=220, command=self.app.go_back_to_form, font=ctk.CTkFont(size=14, weight="bold")).pack(pady=25)
        self.regenerate_qr()

    def set_fg_color(self, hex_color): self.fg_color = hex_color; self.regenerate_qr()
    def set_bg_color(self, hex_color): self.bg_color = hex_color; self.regenerate_qr()

    def regenerate_qr(self):
        try:
            qr = qrcode.QRCode(version=None, error_correction=qrcode.constants.ERROR_CORRECT_L, box_size=12, border=2)
            qr.add_data(self.url)
            qr.make(fit=True)
            img = qr.make_image(fill_color=self.fg_color, back_color=self.bg_color).convert("RGBA")
            self.qr_pil_image = img
            display_img = img.resize((240, 240), Image.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=display_img, dark_image=display_img, size=(240, 240))
            self.qr_label.configure(image=ctk_img, text="")
        except Exception: pass

    def copy_url(self):
        self.clipboard_clear(); self.clipboard_append(self.url)
        msgbox.showinfo("Copied", "Link copied to clipboard.", parent=self)

    def download_qr(self):
        if not self.qr_pil_image: return
        path = ctk.filedialog.asksaveasfilename(defaultextension=".png", filetypes=[("PNG", "*.png")])
        if path: self.qr_pil_image.save(path); msgbox.showinfo("Saved", f"QR saved to:\n{path}", parent=self)

# ==================== MAIN APPLICATION ====================
class WishLinkApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("CT Wishlink Generator") 
        self.resizable(True, True)
        set_window_icon(self)

        self.base_url, self.studio_name, self.imgbb_api, self.cloud_name, self.upload_preset = load_config()

        center_window(self, 860, 900)

        top = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(20,5))
        ctk.CTkLabel(top, text="CT Wishlink Generator", font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")
        ctk.CTkButton(top, text="⚙️ Settings", width=90, command=self.open_settings).pack(side="right")

        self.page_container = ctk.CTkFrame(self, fg_color="transparent")
        self.page_container.pack(fill="both", expand=True, padx=20, pady=(0,20))

        self.form_frame = FormFrame(self.page_container, self)
        self.form_frame.pack(fill="both", expand=True)
        self.output_frame = None

        if not all([self.base_url, self.imgbb_api, self.cloud_name, self.upload_preset]):
            self.withdraw()
            self.after(200, self.open_settings_forced)

    def open_settings(self):
        SettingsModal(self, self.base_url, self.studio_name, self.imgbb_api, self.cloud_name, self.upload_preset, self.on_settings_save)
        
    def open_settings_forced(self):
        SettingsModal(self, self.base_url, self.studio_name, self.imgbb_api, self.cloud_name, self.upload_preset, self.on_settings_save, forced=True)

    def on_settings_save(self, url, studio, imgbb, cloud, preset):
        self.base_url, self.studio_name, self.imgbb_api, self.cloud_name, self.upload_preset = url, studio, imgbb, cloud, preset

    def start_generation(self):
        if not check_internet():
            msgbox.showwarning("Internet Lost", "No internet connection detected.", parent=self); return

        name = self.form_frame.name_entry.get().strip()
        message = self.form_frame.msg_text.get("1.0", "end-1c").strip()
        
        theme = self.form_frame.theme_combo.get()
        occasion_theme = self.form_frame.occasion_combo.get()
        
        if theme == "Select Theme" or occasion_theme == "Select Occasion":
            msgbox.showerror("Missing Input", "Please select a Theme and an Occasion.", parent=self); return

        if not name or not message:
            msgbox.showerror("Missing Input", "Recipient Name and Message are required.", parent=self); return
            
        custom_title = self.form_frame.custom_entry.get().strip()
        if not custom_title:
            msgbox.showerror("Missing Input", "Enter a Display Title.", parent=self); return

        if not all([self.base_url, self.imgbb_api, self.cloud_name, self.upload_preset]):
            msgbox.showerror("Configuration", "Fill all required API fields in Settings.", parent=self); return

        self.loading = LoadingPopup(self)
        self.form_frame.gen_btn.configure(state="disabled", text="Processing...")
        
        args = (name, theme, occasion_theme, custom_title, message, 
                self.form_frame.img_path, self.form_frame.audio_path, 
                f"{self.form_frame.month_combo.get()} {self.form_frame.day_combo.get()}, {self.form_frame.year_entry.get().strip()}", 
                self.form_frame.sender_entry.get().strip())
        
        threading.Thread(target=self._process_generation, args=args, daemon=True).start()

    def _process_generation(self, name, theme, occasion_theme, custom_title, message, img_path, audio_path, date_val, sender):
        img_url, audio_url = "", ""
        report_data = {}
        
        try:
            if img_path:
                orig_size = os.path.getsize(img_path)
                compressed_img, is_compressed = compress_image_to_webp(img_path)
                new_size = len(compressed_img.getvalue())
                img_url = upload_to_imgbb(compressed_img, self.imgbb_api, is_compressed)
                report_data['img'] = {'orig': orig_size, 'new': new_size, 'skipped': not is_compressed}

            if audio_path:
                orig_size = os.path.getsize(audio_path)
                mp3_path = compress_audio_to_mp3(audio_path)
                new_size = os.path.getsize(mp3_path)
                audio_url = upload_to_cloudinary(mp3_path, self.cloud_name, self.upload_preset)
                report_data['audio'] = {'orig': orig_size, 'new': new_size}
                os.remove(mp3_path) # Cleanup temp file

            # Magic Shortcut: If Engagement, pass "custom" so HTML uses the special background
            url_occ = "custom" if occasion_theme == "Engagement" else occasion_theme

            params = {"name": name, "theme": theme, "occ": url_occ, "title": custom_title, "msg": message}
            if date_val and "Day" not in date_val: params["date"] = date_val
            if sender: params["sender"] = sender
            if self.studio_name: params["studio_name"] = self.studio_name
            if img_url: params["img"] = img_url
            if audio_url: params["audio"] = audio_url 

            qs = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
            base = self.base_url.rstrip("/")
            final_url = f"{base}/?{qs}" if "?" not in base else f"{base}&{qs}"
            
            self.after(0, self._show_success_report, report_data, final_url)
        except Exception as e:
            self.after(0, self._on_error, str(e))

    def _show_success_report(self, report_data, url):
        self.loading.stop()
        self.form_frame.gen_btn.configure(state="normal", text="Generate Link & QR")
        SuccessReportModal(self, report_data, lambda: self._on_success(url))

    def _on_success(self, url):
        self.form_frame.pack_forget()
        self.output_frame = OutputFrame(self.page_container, self, url)
        self.output_frame.pack(fill="both", expand=True)

    def _on_error(self, error_msg):
        self.loading.stop()
        self.form_frame.gen_btn.configure(state="normal", text="Generate Link & QR")
        msgbox.showerror("Processing Error", f"An error occurred:\n{error_msg}", parent=self)

    def go_back_to_form(self):
        if self.output_frame:
            self.output_frame.pack_forget()
            self.output_frame.destroy()
            self.output_frame = None
        self.form_frame.reset_form()
        self.form_frame.pack(fill="both", expand=True)

# ==================== LAUNCH CHECK ====================
if __name__ == "__main__":
    if not os.path.exists(SETUP_MARKER):
        setup_app = SetupWindow()
        setup_app.mainloop()
        
    if os.path.exists(SETUP_MARKER):
        app = WishLinkApp()
        app.mainloop()
