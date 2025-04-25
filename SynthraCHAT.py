import os
import sys
import tkinter as tk
from tkinter import messagebox, simpledialog
import webbrowser
from PIL import Image, ImageTk
import pyttsx3
import ctypes as ct
from tkinter import ttk
from screeninfo import get_monitors
import socket
import tkinter.filedialog as fd
import time
import threading
import pygame
import pyautogui
import string
import sys, asyncio
import base64
import io
import traceback
import json
import cv2
import pyaudio
import PIL.Image
import mss
from mss import tools as mss_tools
from typing import Optional, Dict, Callable, Any
import customtkinter as ctk
from tkinter import scrolledtext

# SynthraChat imports and config
from google import genai
from google.genai import types


# Audio config
FORMAT = pyaudio.paInt16
CHANNELS = 1
SEND_SAMPLE_RATE = 16000
RECEIVE_SAMPLE_RATE = 24000
CHUNK_SIZE = 1024

# Gemini model
MODEL = "models/gemini-2.0-flash-live-001"

# Default settings (will be updated by GUI)
DEFAULT_MODE = "audio"
API_KEY = ""
DEFAULT_PERSONA = """You are SynthraCHAT, a helpful AI assistant. 
Respond concisely and helpfully to user requests."""
DEFAULT_VOICE = "Puck"
MAX_CONVERSATION_HISTORY = 100000000000000  # Characters
MAX_QUEUE_SIZE = 10

# Initialize client (will be updated after GUI)
client = None
CONFIG = None

# PyAudio init
pya = pyaudio.PyAudio()

# Storage for saved configurations
SAVED_CONFIGS_FILE = "synthra_configs.json"

# Global variables
voice_interaction_enabled = False
fullscreen = False
menu_visible = False
stop_listening = None
sound_muted = False
menu_animation_id = None
synthra_config = None
synthra_client = None
synthra_running = False
synthra_audio_loop = None
synthra_audio_loop_thread = None
synthra_event_loop = None

# Indicator settings
indicator_colors = {
    'active': 'DodgerBlue',
    'inactive': 'black',
    'outline': 'black'
}

# Initialize pyttsx3 engine
engine = pyttsx3.init()
engine.setProperty('rate', 150)

# Initialize pygame mixer
pygame.mixer.init()

def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.dirname(sys.argv[0])
    return os.path.join(base_path, relative_path)

# Default sound paths
bing_sound_path = resource_path('Button.mp3')
menu_sound_path = resource_path('Click.mp3')
Hover_sound_path = resource_path('Hover.mp3')

def play_sound(sound_type):
    """Play the appropriate sound based on type if not muted"""
    if sound_muted:
        return
    try:
        if sound_type == "menu":
            sound_to_play = menu_sound_path if os.path.exists(menu_sound_path) else resource_path('Click.mp3')
        elif sound_type == "main":
            sound_to_play = bing_sound_path if os.path.exists(bing_sound_path) else resource_path('Button.mp3')
        elif sound_type == "Hover":
            sound_to_play = Hover_sound_path if os.path.exists(Hover_sound_path) else resource_path('Hover.mp3')
        
        pygame.mixer.music.load(sound_to_play)
        pygame.mixer.music.play()
    except Exception as e:
        print(f"Error playing sound: {e}")

def toggle_mute():
    """Toggle sound mute state"""
    global sound_muted
    sound_muted = not sound_muted
    # Update the mute button text
    for widget in menu_frame.winfo_children():
        if isinstance(widget, ttk.Button) and widget['text'] in ["Mute", "Unmute"]:
            widget.config(text="Unmute" if sound_muted else "Mute")
            break

def on_enter(event):
    """Handle mouse enter events for main button"""
    if event.widget == button_label:
        event.widget.config(bg='navy')

def on_leave(event):
    """Handle mouse leave events for main button"""
    if event.widget == button_label:
        event.widget.config(bg='SystemButtonFace')

def get_monitor(window):
    """Get monitor info where window resides"""
    window_x = window.winfo_rootx()
    window_y = window.winfo_rooty()

    for monitor in get_monitors():
        if monitor.x <= window_x <= monitor.x + monitor.width and monitor.y <= window_y <= monitor.y + monitor.height:
            return monitor
    return get_monitors()[0]

def is_connected():
    """Check internet connectivity"""
    try:
        socket.create_connection(("www.google.com", 80), timeout=5)
        return True
    except OSError:
        return False

def toggle_fullscreen(event=None):
    """Toggle between fullscreen and windowed mode"""
    global fullscreen
    current_monitor = get_monitor(root)

    screen_width = current_monitor.width
    screen_height = current_monitor.height
    monitor_x = current_monitor.x
    monitor_y = current_monitor.y

    if fullscreen:
        root.overrideredirect(False)
        root.geometry("400x300")
        fullscreen = False
    else:
        root.overrideredirect(True)
        root.geometry(f"{screen_width}x{screen_height}+{monitor_x}+{monitor_y}")
        fullscreen = True

def dark_title_bar(window):
    """Apply dark mode title bar (Windows 10/11 only)"""
    window.update()
    DWMWA_USE_IMMERSIVE_DARK_MODE = 20
    set_window_attribute = ct.windll.dwmapi.DwmSetWindowAttribute
    hwnd = ct.windll.user32.GetParent(window.winfo_id())
    value = ct.c_int(2)
    result = set_window_attribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ct.byref(value), ct.sizeof(value))
    if result != 0:  # If failed, try with value = 1 (older Windows 10 versions)
        value = ct.c_int(1)
        set_window_attribute(hwnd, DWMWA_USE_IMMERSIVE_DARK_MODE, ct.byref(value), ct.sizeof(value))

def speak_text(text):
    """Text-to-speech function"""
    try:
        engine.stop()
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"Error in speak_text: {e}")

def on_close():
    """Gracefully exit the application"""
    global stop_listening, synthra_running, synthra_audio_loop, synthra_event_loop
    
    try:
        if stop_listening:
            stop_listening(wait_for_stop=False)
        
        if synthra_running and synthra_audio_loop:
            synthra_running = False
            synthra_audio_loop.stop()
            if synthra_event_loop:
                synthra_event_loop.stop()
            if synthra_audio_loop_thread:
                synthra_audio_loop_thread.join(timeout=1)
            
        engine.stop()
        pygame.mixer.quit()
        pya.terminate()
    except Exception as e:
        print(f"Error in on_close: {e}")
    root.destroy()

def center_window_on_parent(child, width, height):
    """Center child window on parent window"""
    parent_x = root.winfo_x()
    parent_y = root.winfo_y()
    parent_width = root.winfo_width()
    parent_height = root.winfo_height()
    
    x = parent_x + (parent_width // 2) - (width // 2)
    y = parent_y + (parent_height // 2) - (height // 2)
    child.geometry(f'{width}x{height}+{x}+{y}')

def show_rules():
    """Display the rules window"""
    play_sound("menu")
    rules_window = tk.Toplevel(root)
    rules_window.title("Rules")
    rules_window.geometry('400x300')
    center_window_on_parent(rules_window, 400, 300)

    rules_label = tk.Label(rules_window, 
                         text="SynthraChat - AI Voice Assistant\n\n"
                              "Click the button to start/stop your AI companion!\n\n"
                              "⚡ HINT: Try different voice personalities in settings\n\n"
                              "Features:\n"
                              "• Natural voice conversations\n"
                              "• Screen/Camera/Audio mode\n"
                              "• 8 unique AI voices\n"
                              "• Google Search grounding\n"
                              "• Code execution capabilities\n\n"
                              "SynthraChat | Created by Caleb W. Broussard",
                         font=("Helvetica", 12),
                         wraplength=380,
                         justify='center')
    rules_label.pack(padx=10, pady=10)

    close_button = tk.Button(rules_window, 
                           text="Close", 
                           command=lambda: [play_sound("menu"), rules_window.destroy()], 
                           font=("Helvetica", 10))
    close_button.pack(pady=5)

def change_wallpaper():
    """Open file explorer to change wallpaper"""
    play_sound("menu")
    file_path = fd.askopenfilename(initialdir=os.getcwd(), title="Select Wallpaper", filetypes=[("Image Files", "*.png;*.jpg;*.jpeg;*.bmp")])
    if file_path:
        try:
            background_image = Image.open(file_path)
            background_photo = ImageTk.PhotoImage(background_image)
            canvas.create_image(0, 0, anchor=tk.NW, image=background_photo)
            canvas.image = background_photo
        except Exception as e:
            print(f"Failed to update wallpaper: {e}")

def change_icon():
    """Open file explorer to change icon"""
    play_sound("menu")
    file_path = fd.askopenfilename(initialdir=os.getcwd(), title="Select Icon", filetypes=[("Image Files", "*.png;*.gif;*.ico")])
    if file_path:
        try:
            if file_path.endswith(".gif"):
                gif_image = Image.open(file_path)
                gif_frames = []
                for frame in range(gif_image.n_frames):
                    gif_image.seek(frame)
                    frame_image = ImageTk.PhotoImage(gif_image.copy())
                    gif_frames.append(frame_image)
                
                def update_gif(frame=0):
                    button_label.config(image=gif_frames[frame])
                    button_label.image = gif_frames[frame]
                    root.after(100, update_gif, (frame + 1) % len(gif_frames))
                
                update_gif()
            else:
                new_button_image = Image.open(file_path)
                new_button_image = new_button_image.resize((150, 150), Image.LANCZOS)
                new_button_photo = ImageTk.PhotoImage(new_button_image)
                button_label.config(image=new_button_photo)
                button_label.image = new_button_photo
        except Exception as e:
            print(f"Failed to update button: {e}")

def change_sound():
    """Change sound settings"""
    play_sound("menu")
    sound_window = tk.Toplevel(root)
    sound_window.title("Sound")
    sound_window.geometry('300x200')
    center_window_on_parent(sound_window, 300, 200)
    
    def select_sound(sound_type):
        play_sound("menu")
        file_path = fd.askopenfilename(initialdir=os.getcwd(), title=f"Select {sound_type} Sound",
                                    filetypes=[("Sound Files", "*.mp3;*.wav")])
        if file_path:
            try:
                global bing_sound_path, menu_sound_path, Hover_sound_path
                if sound_type == "Menu Button":
                    menu_sound_path = file_path
                elif sound_type == "Main Button":
                    bing_sound_path = file_path
                elif sound_type == "Hover":
                    Hover_sound_path = file_path
                play_sound("menu" if sound_type == "Menu Button" else "main")
            except Exception as e:
                print(f"Failed to update sound: {e}")
        sound_window.destroy()
    
    menu_sound_btn = ttk.Button(sound_window, text="Click Sound", command=lambda: select_sound("Menu Button"))
    menu_sound_btn.pack(pady=5)
    main_sound_btn = ttk.Button(sound_window, text="Main Button Sound", command=lambda: select_sound("Main Button"))
    main_sound_btn.pack(pady=5)
    Hover_sound_btn = ttk.Button(sound_window, text="Hover Sound", command=lambda: select_sound("Hover"))
    Hover_sound_btn.pack(pady=5)

def update_listening_indicators():
    """Update all listening indicators based on the listening state"""
    if synthra_running:
        active_indicator_top_right.lift()
        active_indicator_bottom_right.lift()
        active_indicator_bottom_left.lift()
    else:
        active_indicator_top_right.lower(listening_indicator_top_right)
        active_indicator_bottom_right.lower(listening_indicator_bottom_right)
        active_indicator_bottom_left.lower(listening_indicator_bottom_left)

def change_indicator_colors():
    """Allow user to change indicator colors"""
    play_sound("menu")
    color_window = tk.Toplevel(root)
    color_window.title("Colors")
    color_window.geometry('350x250')
    center_window_on_parent(color_window, 350, 250)
    
    color_examples = [
        "Red", "Green", "Blue", "Yellow", "Purple", 
        "Orange", "Pink", "Cyan", "Magenta", "Lime",
        "DodgerBlue", "Gold", "Violet", "Turquoise", "Salmon",
        "White", "Black", "Gray", "Maroon", "Olive"
    ]
    
    active_frame = tk.Frame(color_window)
    active_frame.pack(pady=5)
    tk.Label(active_frame, text="Active Color:", font=("Helvetica", 10)).pack()
    active_entry = tk.Entry(active_frame, width=20, font=("Helvetica", 10))
    active_entry.insert(0, indicator_colors['active'])
    active_entry.pack(pady=5)
    
    inactive_frame = tk.Frame(color_window)
    inactive_frame.pack(pady=5)
    tk.Label(inactive_frame, text="Inactive Color:", font=("Helvetica", 10)).pack()
    inactive_entry = tk.Entry(inactive_frame, width=20, font=("Helvetica", 10))
    inactive_entry.insert(0, indicator_colors['inactive'])
    inactive_entry.pack(pady=5)
    
    examples_label = tk.Label(color_window, 
                            text=f"Color examples: {', '.join(color_examples)}",
                            font=("Helvetica", 8),
                            wraplength=330)
    examples_label.pack(pady=5)
    
    def apply_colors():
        play_sound("menu")
        new_active = active_entry.get()
        new_inactive = inactive_entry.get()
        
        try:
            test_label = tk.Label(color_window)
            test_label.config(bg=new_active)
            test_label.config(bg=new_inactive)
            
            indicator_colors['active'] = new_active
            indicator_colors['inactive'] = new_inactive
            
            # Update active indicators
            active_indicator_top_right.config(bg=new_active)
            active_indicator_bottom_right.config(bg=new_active)
            active_indicator_bottom_left.config(bg=new_active)
            
            # Update inactive indicators
            listening_indicator_top_right.config(bg=new_inactive)
            listening_indicator_bottom_right.config(bg=new_inactive)
            listening_indicator_bottom_left.config(bg=new_inactive)
            
            color_window.destroy()
        except tk.TclError:
            pass
    
    button_frame = tk.Frame(color_window)
    button_frame.pack(pady=5)
    tk.Button(button_frame, text="Apply", command=apply_colors, font=("Helvetica", 8)).pack(side=tk.LEFT, padx=5)
    tk.Button(button_frame, text="Close", command=lambda: [play_sound("menu"), color_window.destroy()], 
              font=("Helvetica", 8)).pack(side=tk.LEFT, padx=5)

def animate_menu(step, direction):
    """Animate the menu sliding in/out"""
    global menu_animation_id, menu_visible
    
    menu_width = 120
    menu_height = 217  # Reduced height to remove empty space
    
    if direction == "in":
        new_x = -menu_width + (step * 12)
        if new_x >= 0:
            new_x = 0
            menu_visible = True
            menu_button.place_forget()
        else:
            menu_animation_id = root.after(10, animate_menu, step + 1, direction)
    else:
        new_x = 0 - (step * 12)
        if new_x <= -menu_width:
            new_x = -menu_width
            menu_visible = False
            menu_button.place(relx=0, rely=0, x=10, y=10)
        else:
            menu_animation_id = root.after(10, animate_menu, step + 1, direction)
    
    menu_frame.place(x=new_x, y=0, width=menu_width, height=menu_height)
    
    if new_x == 0 or new_x == -menu_width:
        menu_animation_id = None

def toggle_menu():
    """Toggle menu visibility with animation"""
    global menu_animation_id, menu_visible
    
    play_sound("menu")
    
    if menu_animation_id:
        root.after_cancel(menu_animation_id)
        menu_animation_id = None
    
    if menu_visible:
        animate_menu(1, "out")
    else:
        animate_menu(1, "in")

def close_menu_if_open(event):
    """Close menu if clicked outside of it"""
    if menu_visible:
        x, y = event.x, event.y
        if x > menu_frame.winfo_width() or y > menu_frame.winfo_height():
            toggle_menu()

class SynthraChatConfig:
    def __init__(self, parent):
        self.parent = parent
        self.window = tk.Toplevel(parent)
        self.window.title("SynthraCHAT Configuration")
        self.window.geometry('1000x720')
        center_window_on_parent(self.window, 1000, 720)
        self.window.protocol("WM_DELETE_WINDOW", self.on_close)
        
        self.saved_configs = self.load_saved_configs()
        self.show_api_key = False
        
        # Set appearance
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        # Create main frame with grid layout
        self.main_frame = ctk.CTkFrame(self.window)
        self.main_frame.pack(pady=10, padx=10, fill="both", expand=True)
        
        # Mode Selection
        ctk.CTkLabel(self.main_frame, text="Input Mode:").pack(pady=(10,0))
        self.mode_var = ctk.StringVar(value=DEFAULT_MODE)
        mode_frame = ctk.CTkFrame(self.main_frame)
        mode_frame.pack()
        ctk.CTkRadioButton(mode_frame, text="Camera", variable=self.mode_var, value="camera").pack(side=tk.LEFT, padx=5)
        ctk.CTkRadioButton(mode_frame, text="Screen", variable=self.mode_var, value="screen").pack(side=tk.LEFT, padx=5)
        ctk.CTkRadioButton(mode_frame, text="Audio Only", variable=self.mode_var, value="audio").pack(side=tk.LEFT, padx=5)
        
        # Voice Selection
        ctk.CTkLabel(self.main_frame, text="Voice:").pack(pady=(10,0))
        self.voice_var = ctk.StringVar(value=DEFAULT_VOICE)
        voice_frame = ctk.CTkFrame(self.main_frame)
        voice_frame.pack()
        voices = ["Puck", "Charon", "Kore", "Fenrir", "Aoede", "Leda", "Orus", "Zephyr"]
        for voice in voices:
            ctk.CTkRadioButton(voice_frame, text=voice, variable=self.voice_var, value=voice).pack(side=tk.LEFT, padx=5)
        
        # Tools Configuration - MODIFY THIS SECTION
        ctk.CTkLabel(self.main_frame, text="AI Tools:").pack(pady=(10,0))
        self.tools_frame = ctk.CTkFrame(self.main_frame)
        self.tools_frame.pack()

        self.google_search_var = ctk.BooleanVar(value=True)
        self.code_execution_var = ctk.BooleanVar(value=True)

        # Create a sub-frame for horizontal layout
        tools_checkbox_frame = ctk.CTkFrame(self.tools_frame, fg_color="transparent")
        tools_checkbox_frame.pack()

        # Place checkboxes side by side with padding
        ctk.CTkCheckBox(tools_checkbox_frame, text="Google Search", variable=self.google_search_var).pack(side=tk.LEFT, padx=10, pady=2)
        ctk.CTkCheckBox(tools_checkbox_frame, text="Code Execution", variable=self.code_execution_var).pack(side=tk.LEFT, padx=10, pady=2)

        # Persona Configuration
        ctk.CTkLabel(self.main_frame, text="Persona Configuration:").pack(pady=(10,0))
        self.persona_text = ctk.CTkTextbox(self.main_frame, width=600, height=200, wrap=tk.WORD)
        self.persona_text.insert(tk.INSERT, DEFAULT_PERSONA)
        self.persona_text.pack(pady=(0,10))
        
        # API Key section
        ctk.CTkLabel(self.main_frame, text="Google Gemini API Key:").pack(pady=(10,0))
        
        # API Key entry and toggle button in same frame
        api_entry_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        api_entry_frame.pack(pady=(0,10))
        
        self.api_key_entry = ctk.CTkEntry(
            api_entry_frame,
            width=400,
            placeholder_text="Enter your API key",
            show="*"
        )
        self.api_key_entry.pack(side=tk.LEFT, padx=(0,5))
        
        self.toggle_btn = ctk.CTkButton(
            api_entry_frame,
            text="👁️",
            width=30,
            command=self.toggle_api_visibility
        )
        self.toggle_btn.pack(side=tk.LEFT)
        
        # Saved Configurations section
        ctk.CTkLabel(self.main_frame, text="Saved Configurations:").pack(pady=(10,5))
        
        # Config dropdown and buttons
        config_controls = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        config_controls.pack()
        
        self.saved_config_var = ctk.StringVar()
        self.saved_config_dropdown = ctk.CTkComboBox(
            config_controls, 
            variable=self.saved_config_var,
            values=list(self.saved_configs.keys()) if self.saved_configs else ["No saved configs"],
            width=200
        )
        self.saved_config_dropdown.pack(side=tk.LEFT, padx=(0,5))
        
        ctk.CTkButton(
            config_controls, 
            text="Load", 
            command=self.load_selected_config,
            width=80
        ).pack(side=tk.LEFT, padx=(0,5))
        
        ctk.CTkButton(
            config_controls, 
            text="Save", 
            command=self.save_current_config,
            width=80
        ).pack(side=tk.LEFT, padx=(0,5))
        
        # Back button at bottom center
        self.back_button = ctk.CTkButton(
            self.main_frame,
            text="BACK",
            command=self.save_and_close,
            width=200,
            height=50,
            fg_color="#32CD32",  # Lime green
            hover_color="#228B22",
            font=("Arial", 14, "bold")
        )
        self.back_button.pack(pady=(40,10))
        
        # Loading indicator (hidden by default)
        self.loading_indicator = ctk.CTkLabel(
            self.main_frame,
            text="",
            font=("Arial", 12)
        )
        self.loading_indicator.pack(pady=(0,10))
    
    def toggle_api_visibility(self):
        """Toggle visibility of the API key in the entry field"""
        self.show_api_key = not self.show_api_key
        self.api_key_entry.configure(show="" if self.show_api_key else "*")
        self.toggle_btn.configure(text="👁️" if self.show_api_key else "👁️")
    
    def load_saved_configs(self) -> Dict[str, Any]:
        """Load saved configurations from file"""
        try:
            if os.path.exists(SAVED_CONFIGS_FILE):
                with open(SAVED_CONFIGS_FILE, 'r') as f:
                    loaded_configs = json.load(f)
                    # Filter out any non-dictionary entries or improperly formatted configs
                    return {name: config for name, config in loaded_configs.items() 
                           if isinstance(config, dict) and 
                           all(key in config for key in ['api_key', 'mode', 'voice', 'persona', 'tools'])}
        except Exception as e:
            print(f"Error loading saved configs: {e}")
        return {}
    
    def save_configs_to_file(self):
        """Save current configurations to file"""
        try:
            with open(SAVED_CONFIGS_FILE, 'w') as f:
                json.dump(self.saved_configs, f)
        except Exception as e:
            print(f"Error saving configs: {e}")
    
    def load_selected_config(self):
        """Load the selected configuration from saved configs"""
        selected_name = self.saved_config_var.get()
        if selected_name and selected_name in self.saved_configs:
            config = self.saved_configs[selected_name]
            self.persona_text.delete("1.0", tk.END)
            self.persona_text.insert(tk.INSERT, config.get('persona', DEFAULT_PERSONA))
            self.mode_var.set(config.get('mode', DEFAULT_MODE))
            self.voice_var.set(config.get('voice', DEFAULT_VOICE))
            self.api_key_entry.delete(0, tk.END)
            self.api_key_entry.insert(0, config.get('api_key', ""))
            
            # Load tools configuration
            tools_config = config.get('tools', {})
            self.google_search_var.set(tools_config.get('google_search', True))
            self.code_execution_var.set(tools_config.get('code_execution', True))
    
    def save_current_config(self):
        """Save current configuration with a name"""
        x = self.window.winfo_x() + (self.window.winfo_width() // 2) - 150
        y = self.window.winfo_y() + (self.window.winfo_height() // 2) - 75
        
        dialog = ctk.CTkInputDialog(
            text="Enter a name for this configuration:", 
            title="Save Configuration"
        )
        dialog.geometry(f"+{x}+{y}")
        
        config_name = dialog.get_input()
        
        if config_name:
            # Only save if we have valid configuration data
            if self.validate_config():
                self.saved_configs[config_name] = {
                    'api_key': self.api_key_entry.get(),
                    'mode': self.mode_var.get(),
                    'voice': self.voice_var.get(),
                    'persona': self.persona_text.get("1.0", tk.END).strip(),
                    'tools': {
                        'google_search': self.google_search_var.get(),
                        'code_execution': self.code_execution_var.get()
                    }
                }
                self.save_configs_to_file()
                # Update dropdown with only the named configurations
                self.saved_config_dropdown.configure(values=list(self.saved_configs.keys()))
                self.saved_config_var.set(config_name)
    
    def validate_config(self) -> bool:
        """Validate the current configuration"""
        api_key = self.api_key_entry.get().strip()
        persona = self.persona_text.get("1.0", tk.END).strip()
        
        if not api_key:
            messagebox.showerror("Error", "Please enter a valid API key")
            return False
            
        if not persona:
            messagebox.showerror("Error", "Persona configuration cannot be empty")
            return False
            
        return True
    
    def save_and_close(self):
        """Save configuration and close window"""
        global synthra_config, API_KEY, DEFAULT_MODE, DEFAULT_PERSONA, DEFAULT_VOICE
        
        if not self.validate_config():
            return
            
        API_KEY = self.api_key_entry.get().strip()
        DEFAULT_MODE = self.mode_var.get()
        DEFAULT_PERSONA = self.persona_text.get("1.0", tk.END).strip()
        DEFAULT_VOICE = self.voice_var.get()
        
        synthra_config = {
            'api_key': API_KEY,
            'mode': DEFAULT_MODE,
            'voice': DEFAULT_VOICE,
            'persona': DEFAULT_PERSONA,
            'tools': {
                'google_search': self.google_search_var.get(),
                'code_execution': self.code_execution_var.get()
            }
        }
        
        self.window.destroy()
    
    def show_loading(self, message: str):
        """Show loading indicator with message"""
        self.loading_indicator.configure(text=message)
        self.back_button.configure(state="disabled")
    
    def hide_loading(self):
        """Hide loading indicator"""
        self.loading_indicator.configure(text="")
        self.back_button.configure(state="normal")
    
    def on_close(self):
        """Handle window close event"""
        self.window.destroy()

def show_synthra_chat():
    """Show SynthraCHAT configuration window"""
    play_sound("menu")
    SynthraChatConfig(root)

def run_synthra_loop():
    """Run the SynthraCHAT audio loop in a separate thread"""
    global synthra_audio_loop, synthra_event_loop
    
    try:
        synthra_event_loop = asyncio.new_event_loop()
        asyncio.set_event_loop(synthra_event_loop)
        synthra_event_loop.run_until_complete(synthra_audio_loop.run())
    except Exception as e:
        print(f"Error in SynthraCHAT loop: {e}")
        traceback.print_exc()
    finally:
        if synthra_audio_loop:
            synthra_audio_loop.cleanup()

def toggle_synthra_chat():
    """Toggle SynthraCHAT on/off"""
    global synthra_running, synthra_audio_loop, synthra_audio_loop_thread, synthra_config, client, CONFIG
    
    play_sound("main")  # Added sound when button is clicked
    
    if not synthra_config:
        messagebox.showwarning("Warning", "Please configure SynthraCHAT first")
        return
    
    if not synthra_running:
        # Start SynthraCHAT
        try:
            # Initialize client and config
            client = genai.Client(
                http_options={"api_version": "v1beta"},
                api_key=synthra_config['api_key']
            )
            
            # Prepare tools based on configuration
            tools = []
            if synthra_config['tools']['google_search']:
                tools.append(types.Tool(google_search=types.GoogleSearch()))
            if synthra_config['tools']['code_execution']:
                tools.append(types.Tool(code_execution=types.ToolCodeExecution()))
            
            CONFIG = types.LiveConnectConfig(
                response_modalities=["audio"],
                speech_config=types.SpeechConfig(
                    voice_config=types.VoiceConfig(
                        prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=synthra_config['voice'])
                    )
                ),
                system_instruction=types.Content(
                    parts=[types.Part.from_text(
                        text=synthra_config['persona']
                    )],
                    role="user"
                ),
                tools=tools if tools else None
            )
            
            # Start audio loop
            synthra_audio_loop = AudioLoop(
                video_mode=synthra_config['mode'],
                update_conversation_callback=None,
                update_status_callback=None
            )
            
            synthra_audio_loop_thread = threading.Thread(
                target=run_synthra_loop,
                daemon=True
            )
            synthra_running = True
            synthra_audio_loop_thread.start()
            update_listening_indicators()
            
        except Exception as e:
            synthra_running = False
            update_listening_indicators()
            messagebox.showerror("Error", f"Failed to start SynthraCHAT: {str(e)}")
    else:
        # Stop SynthraCHAT
        synthra_running = False
        update_listening_indicators()
        
        if synthra_audio_loop:
            synthra_audio_loop.stop()
            if synthra_audio_loop_thread:
                synthra_audio_loop_thread.join(timeout=1)
        
        synthra_audio_loop = None
        synthra_audio_loop_thread = None

class AudioLoop:
    def __init__(self, 
                 video_mode: str = DEFAULT_MODE, 
                 update_conversation_callback: Optional[Callable] = None,
                 update_status_callback: Optional[Callable] = None):
        self.video_mode = video_mode
        self.audio_in_queue: Optional[asyncio.Queue] = None
        self.out_queue: Optional[asyncio.Queue] = None
        self.session = None
        self.audio_stream = None
        self.is_listening = True
        self.update_conversation = update_conversation_callback
        self.update_status = update_status_callback
        self.running = True
        self.loop = None
        self.cap = None
        self.sct = None

    def stop(self):
        """Stop the audio processing loop"""
        self.running = False
        if self.update_status:
            self.update_status("AI stopped")

    def cleanup(self):
        """Clean up resources safely"""
        try:
            if self.audio_stream:
                self.audio_stream.stop_stream()
                self.audio_stream.close()
            if self.cap and self.cap.isOpened():
                self.cap.release()
            if hasattr(self, 'sct') and self.sct:
                try:
                    self.sct.close()
                except AttributeError:
                    pass  # Ignore MSS cleanup errors
        except Exception as e:
            print(f"Cleanup error: {e}")

    def _get_frame(self, cap) -> Optional[Dict[str, Any]]:
        """Capture a frame from camera"""
        try:
            ret, frame = cap.read()
            if not ret:
                return None
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            img = PIL.Image.fromarray(frame_rgb)
            img.thumbnail([1024, 1024])
            image_io = io.BytesIO()
            img.save(image_io, format="jpeg", quality=85)
            image_io.seek(0)
            return {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(image_io.read()).decode()
            }
        except Exception as e:
            if self.update_status:
                self.update_status(f"Camera error: {str(e)}")
            return None

    async def get_frames(self):
        """Continuously get frames from camera"""
        self.cap = await asyncio.to_thread(cv2.VideoCapture, 0)
        if not self.cap.isOpened():
            if self.update_status:
                self.update_status("Error: Could not open camera")
            return
            
        while self.running:
            frame = await asyncio.to_thread(self._get_frame, self.cap)
            if frame is None:
                break
            try:
                await self.out_queue.put(frame)
                await asyncio.sleep(0.5)
            except asyncio.QueueFull:
                await asyncio.sleep(0.1)

    def _get_screen(self) -> Optional[Dict[str, Any]]:
        """Capture a screenshot"""
        try:
            if not hasattr(self, 'sct') or not self.sct:
                self.sct = mss.mss()
            monitor = self.sct.monitors[0]
            screenshot = self.sct.grab(monitor)
            image_bytes = mss_tools.to_png(screenshot.rgb, screenshot.size)
            img = PIL.Image.open(io.BytesIO(image_bytes))
            img.thumbnail([1024, 1024])
            image_io = io.BytesIO()
            img.save(image_io, format="jpeg", quality=85)
            image_io.seek(0)
            return {
                "mime_type": "image/jpeg",
                "data": base64.b64encode(image_io.read()).decode()
            }
        except Exception as e:
            if self.update_status:
                self.update_status(f"Screen capture error: {str(e)}")
            return None

    async def get_screen(self):
        """Continuously capture screenshots"""
        while self.running:
            frame = await asyncio.to_thread(self._get_screen)
            if frame is None:
                break
            try:
                await self.out_queue.put(frame)
                await asyncio.sleep(0.5)
            except asyncio.QueueFull:
                await asyncio.sleep(0.1)

    async def send_realtime(self):
        """Send data to the AI in real-time"""
        while self.running:
            try:
                msg = await asyncio.wait_for(self.out_queue.get(), timeout=1.0)
                await self.session.send(input=msg)
                if self.update_status:
                    self.update_status("AI is processing...")
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                if self.update_status:
                    self.update_status(f"Error: {str(e)}")
                traceback.print_exc()

    async def listen_audio(self):
        """Capture audio from microphone"""
        try:
            mic_info = pya.get_default_input_device_info()
            self.audio_stream = await asyncio.to_thread(
                pya.open,
                format=FORMAT,
                channels=CHANNELS,
                rate=SEND_SAMPLE_RATE,
                input=True,
                input_device_index=mic_info["index"],
                frames_per_buffer=CHUNK_SIZE,
            )
            
            kwargs = {"exception_on_overflow": False} if __debug__ else {}
            while self.running:
                if self.is_listening:
                    data = await asyncio.to_thread(self.audio_stream.read, CHUNK_SIZE, **kwargs)
                    if len(data) > 0:
                        try:
                            await self.out_queue.put({"data": data, "mime_type": "audio/pcm"})
                        except asyncio.QueueFull:
                            await asyncio.sleep(0.01)
                else:
                    await asyncio.sleep(0.01)
        except Exception as e:
            if self.update_status:
                self.update_status(f"Audio error: {str(e)}")
            traceback.print_exc()

    async def receive_audio(self):
        """Receive audio responses from AI"""
        while self.running:
            try:
                turn = self.session.receive()
                async for response in turn:
                    if not self.running:
                        break
                        
                    if response.data:
                        self.is_listening = False
                        if self.update_status:
                            self.update_status("AI is responding...")
                        self.audio_in_queue.put_nowait(response.data)
                        continue

                # Clear any remaining audio in queue
                while not self.audio_in_queue.empty():
                    self.audio_in_queue.get_nowait()

                self.is_listening = True
                
            except Exception as e:
                if self.update_status:
                    self.update_status(f"Receive error: {str(e)}")
                traceback.print_exc()
                await asyncio.sleep(1)

    async def play_audio(self):
        """Play received audio responses"""
        try:
            stream = await asyncio.to_thread(
                pya.open,
                format=FORMAT,
                channels=CHANNELS,
                rate=RECEIVE_SAMPLE_RATE,
                output=True,
            )
            
            while self.running:
                try:
                    bytestream = await asyncio.wait_for(self.audio_in_queue.get(), timeout=1.0)
                    await asyncio.to_thread(stream.write, bytestream)
                except asyncio.TimeoutError:
                    continue
                    
            stream.close()
        except Exception as e:
            if self.update_status:
                self.update_status(f"Playback error: {str(e)}")
            traceback.print_exc()

    async def run(self):
        """Main processing loop"""
        try:
            async with (
                client.aio.live.connect(model=MODEL, config=CONFIG) as session,
                asyncio.TaskGroup() as tg
            ):
                self.session = session
                self.audio_in_queue = asyncio.Queue()
                self.out_queue = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)

                tasks = [
                    tg.create_task(self.send_realtime()),
                    tg.create_task(self.receive_audio()),
                    tg.create_task(self.listen_audio()),
                    tg.create_task(self.play_audio()),
                ]

                if self.video_mode == "camera":
                    tasks.append(tg.create_task(self.get_frames()))
                elif self.video_mode == "screen":
                    tasks.append(tg.create_task(self.get_screen()))

                while self.running:
                    await asyncio.sleep(0.1)

        except Exception as e:
            if self.update_status:
                self.update_status(f"Connection error: {str(e)}")
            traceback.print_exc()
        finally:
            self.cleanup()

# GUI Initialization
root = tk.Tk()
root.title('SynthraChat')
root.minsize(400, 300)
root.maxsize(1920, 1080)

# Apply dark title bar immediately
root.withdraw()
root.update()
dark_title_bar(root)
root.deiconify()

icon_path = resource_path('Icon.png')
if os.path.exists(icon_path):
    root.iconphoto(True, tk.PhotoImage(file=icon_path))

root.geometry('400x300')
root.update_idletasks()
x = (root.winfo_screenwidth() // 2) - (400 // 2)
y = (root.winfo_screenheight() // 2) - (300 // 2)
root.geometry(f'400x300+{x}+{y}')

# Periodic title bar refresh
def ensure_dark_title():
    dark_title_bar(root)
    root.after(100, ensure_dark_title)
root.after(100, ensure_dark_title)

# Background Setup
background_path = resource_path('Wallpaper.png')
if os.path.exists(background_path):
    try:
        background_image = Image.open(background_path)
        background_photo = ImageTk.PhotoImage(background_image)
        canvas = tk.Canvas(root, width=400, height=300, highlightthickness=0, bd=0)
        canvas.pack(fill="both", expand=True)
        canvas.create_image(0, 0, anchor=tk.NW, image=background_photo)
    except Exception as e:
        print(f"Failed to load background image: {e}")

# Menu Frame
menu_frame = tk.Frame(root, bg='#000000', bd=0)
menu_frame.place(x=-120, y=0, width=120, height=217)  # Reduced height

# Menu Buttons (added SynthraCHAT button)
button_pady = 3
menu_buttons = [
    ("Rules", show_rules),
    ("SynthraCHAT", show_synthra_chat),
    ("Colors", change_indicator_colors),
    ("Wallpaper", change_wallpaper),
    ("Icon", change_icon),
    ("Sound", change_sound),
    ("Mute", toggle_mute)
]

for text, command in menu_buttons:
    btn = ttk.Button(
        menu_frame, 
        text=text, 
        command=command, 
        style='Small.TButton'
    )
    btn.pack(pady=button_pady, padx=5, fill=tk.X)
    btn.bind("<Enter>", lambda e: play_sound("Hover"))
    btn.bind("<Leave>", lambda e: None)

style = ttk.Style()
style.configure('Small.TButton', 
               borderwidth=1, 
               padding=(1,1),
               font=('Helvetica', 9))

# Main Button Setup
image_path = resource_path('Button.png')
if os.path.exists(image_path):
    try:
        button_image = Image.open(image_path)
        button_image = button_image.resize((150, 150), Image.LANCZOS)
        button_image = ImageTk.PhotoImage(button_image)

        button_label = tk.Label(root, image=button_image, bd=0, highlightthickness=0, borderwidth=2, relief=tk.RAISED)
        button_label.place(relx=0.5, rely=0.5, anchor=tk.CENTER, y=-10)
        button_label.bind("<Button-1>", lambda e: toggle_synthra_chat())  # Changed to toggle SynthraCHAT
        button_label.bind("<Enter>", on_enter)
        button_label.bind("<Leave>", on_leave)
    except Exception as e:
        print(f"Failed to load button image: {e}")

# Hamburger Menu Button
menu_button = ttk.Button(
    root, 
    text="☰", 
    command=toggle_menu, 
    style='Small.TButton', 
    width=2
)
menu_button.place(relx=0, rely=0, x=10, y=10)

# Listening Indicators - All 2x1 size with proper outlines
# Inactive indicators (black with thin border)
listening_indicator_top_right = tk.Label(root, width=2, height=1, bg='black', bd=1, relief='solid')
listening_indicator_top_right.place(relx=1.0, rely=0, x=-25, y=10)

listening_indicator_bottom_right = tk.Label(root, width=2, height=1, bg='black', bd=1, relief='solid')
listening_indicator_bottom_right.place(relx=1.0, rely=1.0, x=-25, y=-25)

listening_indicator_bottom_left = tk.Label(root, width=2, height=1, bg='black', bd=1, relief='solid')
listening_indicator_bottom_left.place(relx=0, rely=1.0, x=10, y=-25)

# Active indicators (blue with thick black outline)
active_indicator_top_right = tk.Label(root, width=2, height=1, bg='azure', bd=2, relief='solid')
active_indicator_top_right.place(relx=1.0, rely=0, x=-25, y=10)
active_indicator_top_right.lower(listening_indicator_top_right)

active_indicator_bottom_right = tk.Label(root, width=2, height=1, bg='azure', bd=2, relief='solid')
active_indicator_bottom_right.place(relx=1.0, rely=1.0, x=-25, y=-25)
active_indicator_bottom_right.lower(listening_indicator_bottom_right)

active_indicator_bottom_left = tk.Label(root, width=2, height=1, bg='azure', bd=2, relief='solid')
active_indicator_bottom_left.place(relx=0, rely=1.0, x=10, y=-25)
active_indicator_bottom_left.lower(listening_indicator_bottom_left)

# Window Management
root.protocol('WM_DELETE_WINDOW', on_close)
root.bind('<Escape>', toggle_fullscreen)
root.bind('<Button-1>', close_menu_if_open)

root.mainloop()
