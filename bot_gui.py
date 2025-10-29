import tkinter as tk
from tkinter import scrolledtext, ttk
import threading
import sys
import os
from datetime import datetime
from io import StringIO
import asyncio
from bot import Client
from dotenv import load_dotenv

class BotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Avalore Discord Bot Manager")
        self.root.geometry("800x600")
        self.root.resizable(True, True)
        
        # Bot state
        self.bot_running = False
        self.bot_thread = None
        self.bot_task = None
        
        # Load environment variables
        load_dotenv()
        self.bot_token = os.getenv('DISCORD_BOT_TOKEN')
        
        # Create GUI elements
        self.create_widgets()
        
        # Redirect stdout to capture print statements
        self.setup_logging()
        
    def create_widgets(self):
        # Title Frame
        title_frame = tk.Frame(self.root, bg="#5865F2", height=60)
        title_frame.pack(fill=tk.X, padx=0, pady=0)
        title_frame.pack_propagate(False)
        
        title_label = tk.Label(
            title_frame, 
            text="🤖 Avalore Discord Bot Manager", 
            font=("Arial", 16, "bold"),
            bg="#5865F2",
            fg="white"
        )
        title_label.pack(pady=15)
        
        # Control Frame
        control_frame = tk.Frame(self.root, bg="#f0f0f0", height=80)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        control_frame.pack_propagate(False)
        
        # Status indicator
        self.status_frame = tk.Frame(control_frame, bg="#f0f0f0")
        self.status_frame.pack(side=tk.LEFT, padx=10)
        
        tk.Label(self.status_frame, text="Status:", font=("Arial", 10), bg="#f0f0f0").pack(side=tk.LEFT, padx=5)
        
        self.status_indicator = tk.Canvas(self.status_frame, width=20, height=20, bg="#f0f0f0", highlightthickness=0)
        self.status_indicator.pack(side=tk.LEFT, padx=5)
        self.status_circle = self.status_indicator.create_oval(2, 2, 18, 18, fill="#ff4444", outline="")
        
        self.status_label = tk.Label(
            self.status_frame, 
            text="Stopped", 
            font=("Arial", 10, "bold"),
            fg="#ff4444",
            bg="#f0f0f0"
        )
        self.status_label.pack(side=tk.LEFT, padx=5)
        
        # Buttons
        button_frame = tk.Frame(control_frame, bg="#f0f0f0")
        button_frame.pack(side=tk.RIGHT, padx=10)
        
        self.start_button = tk.Button(
            button_frame,
            text="▶ Start Bot",
            command=self.start_bot,
            bg="#43b581",
            fg="white",
            font=("Arial", 10, "bold"),
            width=12,
            height=2,
            relief=tk.FLAT,
            cursor="hand2"
        )
        self.start_button.pack(side=tk.LEFT, padx=5)
        
        self.stop_button = tk.Button(
            button_frame,
            text="⏹ Stop Bot",
            command=self.stop_bot,
            bg="#f04747",
            fg="white",
            font=("Arial", 10, "bold"),
            width=12,
            height=2,
            relief=tk.FLAT,
            cursor="hand2",
            state=tk.DISABLED
        )
        self.stop_button.pack(side=tk.LEFT, padx=5)
        
        self.clear_button = tk.Button(
            button_frame,
            text="🗑 Clear Log",
            command=self.clear_log,
            bg="#7289da",
            fg="white",
            font=("Arial", 10, "bold"),
            width=12,
            height=2,
            relief=tk.FLAT,
            cursor="hand2"
        )
        self.clear_button.pack(side=tk.LEFT, padx=5)
        
        # Log Frame
        log_frame = tk.Frame(self.root)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))
        
        tk.Label(
            log_frame, 
            text="📋 Bot Activity Log", 
            font=("Arial", 11, "bold"),
            anchor=tk.W
        ).pack(fill=tk.X, pady=(0, 5))
        
        # Scrolled text widget for logs
        self.log_text = scrolledtext.ScrolledText(
            log_frame,
            wrap=tk.WORD,
            font=("Consolas", 9),
            bg="#2c2f33",
            fg="#ffffff",
            insertbackground="white",
            state=tk.DISABLED
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Configure text tags for colored output
        self.log_text.tag_config("info", foreground="#43b581")
        self.log_text.tag_config("error", foreground="#f04747")
        self.log_text.tag_config("warning", foreground="#faa61a")
        self.log_text.tag_config("success", foreground="#43b581")
        
        # Footer
        footer_frame = tk.Frame(self.root, bg="#f0f0f0", height=30)
        footer_frame.pack(fill=tk.X, side=tk.BOTTOM)
        footer_frame.pack_propagate(False)
        
        footer_label = tk.Label(
            footer_frame,
            text="GitHub Auto-Monitor: Checks every 5 minutes | Made for Avalore",
            font=("Arial", 8),
            bg="#f0f0f0",
            fg="#666666"
        )
        footer_label.pack(pady=5)
        
    def setup_logging(self):
        """Redirect stdout to capture print statements"""
        class TextRedirector:
            def __init__(self, widget, tag="info"):
                self.widget = widget
                self.tag = tag
                self.buffer = ""
                
            def write(self, text):
                self.buffer += text
                if '\n' in self.buffer:
                    lines = self.buffer.split('\n')
                    for line in lines[:-1]:
                        if line.strip():
                            self.widget.append_log(line, self.tag)
                    self.buffer = lines[-1]
                    
            def flush(self):
                if self.buffer.strip():
                    self.widget.append_log(self.buffer, self.tag)
                    self.buffer = ""
        
        sys.stdout = TextRedirector(self, "info")
        sys.stderr = TextRedirector(self, "error")
        
    def append_log(self, text, tag="info"):
        """Append text to log with timestamp"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        self.log_text.config(state=tk.NORMAL)
        self.log_text.insert(tk.END, f"[{timestamp}] ", "info")
        self.log_text.insert(tk.END, f"{text}\n", tag)
        self.log_text.see(tk.END)
        self.log_text.config(state=tk.DISABLED)
        
    def clear_log(self):
        """Clear the log text"""
        self.log_text.config(state=tk.NORMAL)
        self.log_text.delete(1.0, tk.END)
        self.log_text.config(state=tk.DISABLED)
        self.append_log("Log cleared", "info")
        
    def update_status(self, running):
        """Update status indicator"""
        if running:
            self.status_indicator.itemconfig(self.status_circle, fill="#43b581")
            self.status_label.config(text="Running", fg="#43b581")
            self.start_button.config(state=tk.DISABLED)
            self.stop_button.config(state=tk.NORMAL)
        else:
            self.status_indicator.itemconfig(self.status_circle, fill="#ff4444")
            self.status_label.config(text="Stopped", fg="#ff4444")
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            
    def start_bot(self):
        """Start the Discord bot in a separate thread"""
        if not self.bot_running:
            if not self.bot_token or self.bot_token == "":
                self.append_log("ERROR: DISCORD_BOT_TOKEN not found in .env file!", "error")
                return
                
            self.bot_running = True
            self.update_status(True)
            self.append_log("Starting Avalore Discord Bot...", "success")
            
            # Start bot in separate thread
            self.bot_thread = threading.Thread(target=self.run_bot, daemon=True)
            self.bot_thread.start()
            
    def run_bot(self):
        """Run the bot (called in separate thread)"""
        try:
            # Create new event loop for this thread
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            # Run the bot
            if self.bot_token:
                loop.run_until_complete(Client.start(self.bot_token))
        except KeyboardInterrupt:
            self.append_log("Bot stopped by user", "info")
        except Exception as e:
            self.append_log(f"ERROR: {str(e)}", "error")
            self.bot_running = False
            self.root.after(0, self.update_status, False)
            
    def stop_bot(self):
        """Stop the Discord bot"""
        if self.bot_running:
            self.append_log("Stopping bot...", "warning")
            self.bot_running = False
            
            try:
                # Close the bot
                asyncio.run_coroutine_threadsafe(Client.close(), Client.loop)
                self.append_log("Bot stopped successfully", "info")
            except Exception as e:
                self.append_log(f"Error stopping bot: {str(e)}", "error")
            
            self.update_status(False)
            
    def on_closing(self):
        """Handle window closing"""
        if self.bot_running:
            self.stop_bot()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = BotGUI(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
