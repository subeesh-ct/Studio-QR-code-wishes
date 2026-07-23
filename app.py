#!/usr/bin/env python3
"""
CT Wishlink Generator – Premium Windows Desktop App
Complete: PyInstaller support, dual live pickers with presets, scrollable output,
date dropdowns with manual year, sender name, message character limit, robust uploads with retry,
and dynamic Studio Name configuration.
"""

import subprocess
import sys
import importlib
import datetime
import os

# ==================== AUTO‑INSTALL BOOTSTRAP ====================
REQUIRED = {
    'customtkinter': 'customtkinter',
    'qrcode': 'qrcode',
    'PIL': 'pillow',
    'requests': 'requests'
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

# ==================== IMPORTS ====================
import json
import threading
import webbrowser
from io import BytesIO
import urllib.parse
import colorsys
from tkinter import Canvas
import tkinter.messagebox as msgbox

import customtkinter as ctk
from PIL import Image
import qrcode
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# ==================== CONFIG ====================
CONFIG_FILE = "config.json"
CATBOX_API = "https://catbox.moe/user/api.php"
MAX_AUDIO_MB = 6
MAX_IMAGE_MB = 3
MAX_MSG_LENGTH = 500

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ==================== HELPERS ====================
def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data.get("base_url", "").strip(), data.get("studio_name", "").strip()
    return "", ""

def save_config(url, studio_name):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump({
            "base_url": url.strip(),
            "studio_name": studio_name.strip()
        }, f, indent=4)

def center_window(win, width, height):
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    x = (sw - width) // 2
    y = (sh - height) // 2
    win.geometry(f"{width}x{height}+{x}+{y}")

def compress_image_to_webp(file_path, max_mb=MAX_IMAGE_MB):
    img = Image.open(file_path).convert("RGB")
    if max(img.size) > 2000:
        img.thumbnail((2000, 2000), Image.LANCZOS)
    buffer = BytesIO()
    quality = 90
    while True:
        buffer.seek(0)
        buffer.truncate()
        img.save(buffer, format="WEBP", quality=quality)
        if len(buffer.getvalue()) / (1024 * 1024) <= max_mb or quality <= 10:
            break
        quality -= 10
    buffer.seek(0)
    return buffer

def get_retry_session():
    session = requests.Session()
    retries = Retry(
        total=4,
        backoff_factor=1.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"]
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount('https://', adapter)
    session.mount('http://', adapter)
    return session

def upload_to_catbox(file_obj, filename):
    session = get_retry_session()
    try:
        resp = session.post(
            CATBOX_API,
            data={"reqtype": "fileupload"},
            files={"fileToUpload": (filename, file_obj)},
            timeout=(15, 300) 
        )
        resp.raise_for_status() 
        if resp.text.strip():
            return resp.text.strip()
        else:
            raise Exception("Empty response from Catbox API")
    except requests.exceptions.ConnectionError:
        raise Exception("Network connection failed. Please check your internet.")
    except requests.exceptions.Timeout:
        raise Exception("Upload timed out. The server took too long to respond.")
    except requests.exceptions.RequestException as e:
        raise Exception(f"Upload failed: {str(e)}")
    except Exception as e:
        raise e

# ==================== MODALS ====================
class AudioWarningModal(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Audio Too Large")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        w, h = 420, 180
        center_window(self, w, h)
        frame = ctk.CTkFrame(self, corner_radius=15)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        ctk.CTkLabel(frame, text="⚠️ File is too large!",
                     font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(15,10))
        ctk.CTkLabel(frame, text=f"Maximum allowed size is {MAX_AUDIO_MB} MB.",
                     font=ctk.CTkFont(size=13)).pack(pady=(0,10))
        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(pady=10)
        ctk.CTkButton(btn_frame, text="Go to Compressor Site", width=160,
                      command=self.open_compressor).pack(side="left", padx=5)
        ctk.CTkButton(btn_frame, text="Close", width=80,
                      command=self.destroy).pack(side="left", padx=5)

    def open_compressor(self):
        webbrowser.open("https://www.google.com/search?q=free+online+audio+compressor")
        self.destroy()

class SettingsModal(ctk.CTkToplevel):
    def __init__(self, parent, current_url, current_studio, on_save):
        super().__init__(parent)
        self.parent = parent
        self.current_url = current_url
        self.current_studio = current_studio
        self.on_save_callback = on_save
        self.title("Settings")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        
        w, h = 420, 280
        center_window(self, w, h)
        
        frame = ctk.CTkFrame(self, corner_radius=15)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        ctk.CTkLabel(frame, text="Base URL",
                     font=ctk.CTkFont(weight="bold")).pack(pady=(10,2))
        self.url_entry = ctk.CTkEntry(frame, width=360, placeholder_text="https://...")
        self.url_entry.insert(0, current_url)
        self.url_entry.pack(pady=(0,10), padx=20)
        
        ctk.CTkLabel(frame, text="Studio Name (Header Link)",
                     font=ctk.CTkFont(weight="bold")).pack(pady=(5,2))
        self.studio_entry = ctk.CTkEntry(frame, width=360, placeholder_text="e.g., CT Wishlink Generator")
        self.studio_entry.insert(0, current_studio)
        self.studio_entry.pack(pady=(0,5), padx=20)

        self.status = ctk.CTkLabel(frame, text="", text_color="green")
        self.status.pack(pady=2)
        ctk.CTkButton(frame, text="Save", width=120, command=self.save).pack(pady=(5,10))

    def save(self):
        new_url = self.url_entry.get().strip()
        new_studio = self.studio_entry.get().strip()
        
        if not new_url:
            self.status.configure(text="Base URL cannot be empty", text_color="red")
            return
        if not (new_url.startswith("http://") or new_url.startswith("https://")):
            self.status.configure(text="Must start with http:// or https://", text_color="red")
            return
            
        save_config(new_url, new_studio)
        self.on_save_callback(new_url, new_studio)
        self.status.configure(text="Successfully Saved!", text_color="green")
        self.after(1200, self.destroy)

class LoadingPopup(ctk.CTkToplevel):
    def __init__(self, parent):
        super().__init__(parent)
        self.title("Processing")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        w, h = 320, 120
        center_window(self, w, h)
        frame = ctk.CTkFrame(self, corner_radius=15)
        frame.pack(fill="both", expand=True, padx=20, pady=20)
        ctk.CTkLabel(frame, text="Processing & Uploading...\nPlease wait",
                     font=ctk.CTkFont(size=13)).pack(pady=(15,10))
        self.progress = ctk.CTkProgressBar(frame, mode="indeterminate", width=250)
        self.progress.pack(pady=10)
        self.progress.start()

    def stop(self):
        self.progress.stop()
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
        ctk.CTkLabel(self, text="✨ Create Your Wish",
                     font=ctk.CTkFont(size=20, weight="bold")).pack(pady=(15,10))

        ctk.CTkLabel(self, text="Recipient Name *",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10,2))
        self.name_entry = ctk.CTkEntry(self, placeholder_text="Enter name", height=40)
        self.name_entry.pack(fill="x", pady=(0,10))

        ctk.CTkLabel(self, text="Sender Name (Optional)",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5,2))
        self.sender_entry = ctk.CTkEntry(self, placeholder_text="Enter your name", height=36)
        self.sender_entry.pack(fill="x", pady=(0,10))

        ctk.CTkLabel(self, text="Theme",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5,2))
        self.theme_combo = ctk.CTkComboBox(self, values=["Girl Theme", "Boy Theme", "Both/Neutral"],
                                           state="readonly", height=36)
        self.theme_combo.set("Girl Theme")
        self.theme_combo.pack(fill="x", pady=(0,10))

        ctk.CTkLabel(self, text="Occasion",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(5,2))
        occasions = ["Birthday", "Anniversary", "Wedding", "Graduation", "Farewell",
                     "Valentine's Day", "Mother's Day", "Father's Day", "Diwali",
                     "Pongal", "Eid", "Christmas", "New Year", "Congratulations",
                     "Get Well Soon", "Custom"]
        self.occasion_combo = ctk.CTkComboBox(self, values=occasions,
                                              state="readonly", command=self._on_occasion_change,
                                              height=36)
        self.occasion_combo.set("Birthday")
        self.occasion_combo.pack(fill="x", pady=(0,5))
        
        self.custom_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.custom_entry = ctk.CTkEntry(self.custom_frame, placeholder_text="Your custom occasion")
        self.custom_entry.pack(fill="x")

        ctk.CTkLabel(self, text="Event Date (Optional)",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10,2))
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

        ctk.CTkLabel(self, text=f"Message * (Max {MAX_MSG_LENGTH} chars)",
                     font=ctk.CTkFont(weight="bold")).pack(anchor="w", pady=(10,2))
        self.msg_text = ctk.CTkTextbox(self, height=90)
        self.msg_text.pack(fill="x", pady=(0,10))
        
        self.msg_text._enforcing = False
        self.msg_text.bind("<KeyRelease>", self._on_msg_keyrelease)
        self.msg_text.bind("<<Modified>>", self._on_msg_modified)

        media_frame = ctk.CTkFrame(self, corner_radius=10)
        media_frame.pack(fill="x", pady=10, padx=10)
        media_frame.columnconfigure(0, weight=1, uniform="col")
        media_frame.columnconfigure(1, weight=1, uniform="col")

        ctk.CTkLabel(media_frame, text="Image (Optional)").grid(row=0, column=0, sticky="w", padx=15, pady=(10,2))
        self.img_label = ctk.CTkLabel(media_frame, text="No file selected", text_color="gray")
        self.img_label.grid(row=1, column=0, sticky="w", padx=15)
        ctk.CTkButton(media_frame, text="Select Image", width=130,
                      command=self.select_image).grid(row=2, column=0, padx=15, pady=(5,10), sticky="ew")

        ctk.CTkLabel(media_frame, text="Audio (Optional)").grid(row=0, column=1, sticky="w", padx=15, pady=(10,2))
        self.audio_label = ctk.CTkLabel(media_frame, text="No file selected", text_color="gray")
        self.audio_label.grid(row=1, column=1, sticky="w", padx=15)
        ctk.CTkButton(media_frame, text="Select Audio", width=130,
                      command=self.select_audio).grid(row=2, column=1, padx=15, pady=(5,10), sticky="ew")

        self.gen_btn = ctk.CTkButton(self, text="Generate Link & QR",
                                     command=self.app.start_generation,
                                     width=240, height=44, corner_radius=12,
                                     font=ctk.CTkFont(size=15, weight="bold"))
        self.gen_btn.pack(pady=20)

    def _on_occasion_change(self, choice):
        if choice == "Custom":
            self.custom_frame.pack(after=self.occasion_combo, fill="x", pady=(0,5))
        else:
            self.custom_frame.pack_forget()

    def _on_msg_keyrelease(self, event):
        self._enforce_msg_limit()

    def _on_msg_modified(self, event):
        self._enforce_msg_limit()
        self.msg_text.edit_modified(False)  

    def _enforce_msg_limit(self):
        if self.msg_text._enforcing:
            return
        self.msg_text._enforcing = True
        text = self.msg_text.get("1.0", "end-1c")
        if len(text) > MAX_MSG_LENGTH:
            self.msg_text.delete("1.0", "end")
            self.msg_text.insert("1.0", text[:MAX_MSG_LENGTH])
        self.msg_text._enforcing = False

    def select_image(self):
        path = ctk.filedialog.askopenfilename(
            title="Select an Image",
            filetypes=[("Images", "*.jpg *.jpeg *.png *.bmp *.webp"), ("All Files", "*.*")]
        )
        if path:
            self.img_path = path
            self.img_label.configure(text=os.path.basename(path), text_color="green")

    def select_audio(self):
        path = ctk.filedialog.askopenfilename(
            title="Select an Audio File",
            filetypes=[("Audio", "*.mp3 *.wav *.ogg *.m4a *.flac"), ("All Files", "*.*")]
        )
        if path:
            size_bytes = os.path.getsize(path)
            if size_bytes > MAX_AUDIO_MB * 1024 * 1024:
                AudioWarningModal(self)
                self.audio_path = None
                self.audio_label.configure(text="No file selected", text_color="gray")
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
        self.occasion_combo.set("Birthday")
        self.custom_frame.pack_forget()
        self.custom_entry.delete(0, "end")
        self.img_path = None
        self.audio_path = None
        self.img_label.configure(text="No file selected", text_color="gray")
        self.audio_label.configure(text="No file selected", text_color="gray")

# ==================== LIVE COLOR PICKER COMPONENT ====================
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
        self.preview = ctk.CTkLabel(preview_frame, text="", width=30, height=30,
                                    corner_radius=6, fg_color=initial_color)
        self.preview.pack(side="left", padx=(0,10))
        self.hex_label = ctk.CTkLabel(preview_frame, text=initial_color,
                                      font=ctk.CTkFont(weight="bold"))
        self.hex_label.pack(side="left")

        self.presets_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.presets_frame.pack(anchor="w", padx=15, pady=(5,10))

        self.canvas.bind("<Button-1>", self._on_canvas_click)
        self.canvas.bind("<B1-Motion>", self._on_canvas_click)

    def _draw_hue_gradient(self):
        width = 300
        height = 30
        for x in range(width):
            hue = x / width
            r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
            hex_color = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
            self.canvas.create_line(x, 0, x, height, fill=hex_color, width=1)

    def _on_canvas_click(self, event):
        width = self.canvas.winfo_width()
        if width <= 0:
            width = 300
        x = min(max(event.x, 0), width-1)
        hue = x / width
        r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
        hex_color = f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
        self.set_color(hex_color)

    def set_color(self, hex_color):
        self.color = hex_color
        self.preview.configure(fg_color=hex_color)
        self.hex_label.configure(text=hex_color)
        self.on_color_change(hex_color)

    def set_presets(self, preset_list):
        for widget in self.presets_frame.winfo_children():
            widget.destroy()
        for color in preset_list:
            btn = ctk.CTkButton(
                self.presets_frame,
                text="",
                width=24,
                height=24,
                corner_radius=4,
                fg_color=color,
                hover_color=color,
                command=lambda c=color: self.set_color(c)
            )
            btn.pack(side="left", padx=2, pady=2)

# ==================== OUTPUT FRAME (SCROLLABLE) ====================
class OutputFrame(ctk.CTkScrollableFrame):
    def __init__(self, master, app, url):
        super().__init__(master, corner_radius=12, fg_color="transparent",
                         orientation="vertical")
        self.app = app
        self.url = url
        self.fg_color = "#000000"
        self.bg_color = "#FFFFFF"
        self.qr_pil_image = None
        self._build()

    def _build(self):
        ctk.CTkLabel(self, text="🎉 Your Wish Link is Ready!",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(pady=(20,15))

        url_frame = ctk.CTkFrame(self, corner_radius=10, fg_color="#2B2B2B")
        url_frame.pack(fill="x", padx=30, pady=(5,15))
        self.url_entry = ctk.CTkEntry(
            url_frame,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color="#00C2FF",
            fg_color="#3A3A3A",
            state="normal"
        )
        self.url_entry.insert(0, self.url)
        self.url_entry.configure(state="readonly")
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(15,10), pady=12)
        ctk.CTkButton(url_frame, text="Copy Link", width=90,
                      command=self.copy_url).pack(side="right", padx=(0,15), pady=12)

        qr_container = ctk.CTkFrame(self, corner_radius=10)
        qr_container.pack(fill="x", padx=30, pady=(5,10))
        self.qr_label = ctk.CTkLabel(qr_container, text="", width=220, height=220,
                                     fg_color="white", corner_radius=8)
        self.qr_label.pack(pady=15)
        ctk.CTkButton(qr_container, text="Download QR (PNG)", width=180,
                      command=self.download_qr).pack(pady=(0,15))

        pickers_frame = ctk.CTkFrame(self, fg_color="transparent")
        pickers_frame.pack(fill="x", padx=30, pady=10)

        fg_picker = LiveColorPicker(pickers_frame, "Foreground Color", self.fg_color,
                                    on_color_change=self.set_fg_color)
        fg_picker.pack(fill="x", pady=(0,10))
        fg_presets = ["#000000", "#00008B", "#8B0000", "#006400", "#800080", "#FF8C00"]
        fg_picker.set_presets(fg_presets)
        self.fg_picker = fg_picker

        bg_picker = LiveColorPicker(pickers_frame, "Background Color", self.bg_color,
                                    on_color_change=self.set_bg_color)
        bg_picker.pack(fill="x")
        bg_presets = ["#FFFFFF", "#000000", "#D3D3D3", "#FFFF00", "#ADD8E6"]
        bg_picker.set_presets(bg_presets)
        self.bg_picker = bg_picker

        ctk.CTkButton(self, text="Create Another Wish", width=220,
                      command=self.app.go_back_to_form,
                      font=ctk.CTkFont(size=14, weight="bold")).pack(pady=25)

        self.regenerate_qr()

    def set_fg_color(self, hex_color):
        self.fg_color = hex_color
        self.regenerate_qr()

    def set_bg_color(self, hex_color):
        self.bg_color = hex_color
        self.regenerate_qr()

    def regenerate_qr(self):
        try:
            qr = qrcode.QRCode(
                version=None,
                error_correction=qrcode.constants.ERROR_CORRECT_M,
                box_size=8,
                border=2,
            )
            qr.add_data(self.url)
            qr.make(fit=True)
            img = qr.make_image(fill_color=self.fg_color, back_color=self.bg_color).convert("RGBA")
            self.qr_pil_image = img
            display_img = img.resize((220, 220), Image.LANCZOS)
            ctk_img = ctk.CTkImage(light_image=display_img, dark_image=display_img, size=(220, 220))
            self.qr_label.configure(image=ctk_img, text="")
        except Exception as e:
            msgbox.showerror("QR Error", str(e), parent=self)

    def copy_url(self):
        self.clipboard_clear()
        self.clipboard_append(self.url)
        msgbox.showinfo("Copied", "Link copied to clipboard.", parent=self)

    def download_qr(self):
        if not self.qr_pil_image:
            msgbox.showwarning("No QR", "No QR code to download.", parent=self)
            return
        path = ctk.filedialog.asksaveasfilename(
            defaultextension=".png",
            filetypes=[("PNG", "*.png")],
            title="Save QR Code"
        )
        if path:
            try:
                self.qr_pil_image.save(path)
                msgbox.showinfo("Saved", f"QR saved to:\n{path}", parent=self)
            except Exception as e:
                msgbox.showerror("Error", str(e), parent=self)

# ==================== MAIN APPLICATION ====================
class WishLinkApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # --- TITLE CHANGED HERE ---
        self.title("CT Wishlink Generator") 
        self.resizable(True, True)
        
        # --- WINDOW ICON SET HERE ---
        icon_path = resource_path("CT-Stdio.ico")
        if os.path.exists(icon_path):
            self.iconbitmap(icon_path)

        self.base_url, self.studio_name = load_config()

        win_w, win_h = 860, 900
        center_window(self, win_w, win_h)

        top = ctk.CTkFrame(self, corner_radius=0, fg_color="transparent")
        top.pack(fill="x", padx=20, pady=(20,5))
        
        # --- HEADER TEXT CHANGED HERE ---
        ctk.CTkLabel(top, text="CT Wishlink Generator",
                     font=ctk.CTkFont(size=22, weight="bold")).pack(side="left")
                     
        ctk.CTkButton(top, text="⚙️ Settings", width=90,
                      command=self.open_settings).pack(side="right")

        self.page_container = ctk.CTkFrame(self, fg_color="transparent")
        self.page_container.pack(fill="both", expand=True, padx=20, pady=(0,20))

        self.form_frame = FormFrame(self.page_container, self)
        self.form_frame.pack(fill="both", expand=True)
        self.output_frame = None

        if not self.base_url:
            self.after(200, self.open_settings)

    def open_settings(self):
        SettingsModal(self, self.base_url, self.studio_name, self.on_settings_save)

    def on_settings_save(self, new_url, new_studio):
        self.base_url = new_url
        self.studio_name = new_studio

    def start_generation(self):
        name = self.form_frame.name_entry.get().strip()
        if not name:
            msgbox.showerror("Missing Input", "Recipient Name is required.", parent=self)
            return
            
        sender = self.form_frame.sender_entry.get().strip()
        
        message = self.form_frame.msg_text.get("1.0", "end-1c").strip()
        if not message:
            msgbox.showerror("Missing Input", "Message is required.", parent=self)
            return
        
        occasion = self.form_frame.occasion_combo.get()
        if occasion == "Custom":
            custom = self.form_frame.custom_entry.get().strip()
            if not custom:
                msgbox.showerror("Missing Input", "Please enter a custom occasion.", parent=self)
                return
            occasion = custom

        d = self.form_frame.day_combo.get()
        m = self.form_frame.month_combo.get()
        y = self.form_frame.year_entry.get().strip()
        date_val = ""
        if d != "Day" and m != "Month" and y:
            date_val = f"{m} {d}, {y}"

        theme = self.form_frame.theme_combo.get()
        img_path = self.form_frame.img_path
        audio_path = self.form_frame.audio_path

        if not self.base_url:
            msgbox.showerror("Configuration", "Please set a Base URL in Settings first.", parent=self)
            return

        self.loading = LoadingPopup(self)
        self.form_frame.gen_btn.configure(state="disabled", text="Processing...")
        threading.Thread(target=self._process_generation,
                         args=(name, theme, occasion, message, img_path, audio_path, date_val, sender, self.studio_name),
                         daemon=True).start()

    def _process_generation(self, name, theme, occasion, message, img_path, audio_path, date_val, sender, studio_name):
        img_url = ""
        audio_url = ""
        try:
            if img_path:
                compressed_img = compress_image_to_webp(img_path, MAX_IMAGE_MB)
                img_url = upload_to_catbox(compressed_img, "wish_image.webp")
            if audio_path:
                with open(audio_path, "rb") as f:
                    audio_url = upload_to_catbox(f, os.path.basename(audio_path))

            params = {
                "name": name,
                "theme": theme,
                "occ": occasion,
                "msg": message,
            }
            if date_val:
                params["date"] = date_val
            if sender:
                params["sender"] = sender
            if studio_name:
                params["studio_name"] = studio_name
            if img_url:
                params["img"] = img_url
            if audio_url:
                params["audio"] = audio_url

            qs = urllib.parse.urlencode(params, quote_via=urllib.parse.quote)
            base = self.base_url.rstrip("/")
            final_url = f"{base}/?{qs}" if "?" not in base else f"{base}&{qs}"

            self.after(0, self._on_success, final_url)
        except Exception as e:
            self.after(0, self._on_error, str(e))

    def _on_success(self, url):
        self.loading.stop()
        self.form_frame.gen_btn.configure(state="normal", text="Generate Link & QR")
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

# ==================== LAUNCH ====================
if __name__ == "__main__":
    app = WishLinkApp()
    app.mainloop()