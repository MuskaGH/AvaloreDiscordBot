import tkinter as tk
from tkinter import scrolledtext, ttk
import threading
import sys
import os
from datetime import datetime
import asyncio
import constants
from bot import (
    Client,
    force_github_commit_check,
    get_github_check_interval,
    set_github_check_interval,
)
from dotenv import load_dotenv

class BotGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("CommitsBot Manager")
        self.root.geometry("1000x600")
        self.root.minsize(980, 600)
        self.root.resizable(True, True)
        self.gui_thread_id = threading.get_ident()
        
        # Bot state
        self.bot_running = False
        self.bot_thread = None
        self.bot_task = None
        self.force_check_running = False
        self.interval_options = list(constants.GITHUB_CHECK_INTERVAL_OPTIONS)
        self.interval_by_label = {label: seconds for label, seconds in self.interval_options}
        self.interval_label_by_seconds = {seconds: label for label, seconds in self.interval_options}
        self.check_interval_seconds = get_github_check_interval()
        
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
            text="🤖 CommitsBot Manager",
            font=("Arial", 16, "bold"),
            bg="#5865F2",
            fg="white"
        )
        title_label.pack(pady=15)
        
        # Control Frame
        control_frame = tk.Frame(self.root, bg="#f0f0f0", height=88)
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

        # Interval selector
        interval_frame = tk.Frame(control_frame, bg="#f0f0f0")
        interval_frame.pack(side=tk.LEFT, padx=18)

        tk.Label(
            interval_frame,
            text="Check every:",
            font=("Arial", 10),
            bg="#f0f0f0"
        ).pack(side=tk.LEFT, padx=5)

        self.interval_var = tk.StringVar(value=self.get_interval_label(self.check_interval_seconds))
        self.interval_combo = ttk.Combobox(
            interval_frame,
            textvariable=self.interval_var,
            values=[label for label, _ in self.interval_options],
            state="readonly",
            width=12
        )
        self.interval_combo.pack(side=tk.LEFT, padx=5)
        self.interval_combo.bind("<<ComboboxSelected>>", self.on_interval_selected)
        
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

        self.force_check_button = tk.Button(
            button_frame,
            text="🔄 Check Now",
            command=self.force_check_now,
            bg="#faa61a",
            fg="white",
            font=("Arial", 10, "bold"),
            width=12,
            height=2,
            relief=tk.FLAT,
            cursor="hand2",
            state=tk.DISABLED
        )
        self.force_check_button.pack(side=tk.LEFT, padx=5)
        
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
        
    def get_interval_label(self, seconds):
        """Return the dropdown label for an interval."""
        return self.interval_label_by_seconds.get(seconds, f"{seconds} seconds")

    def get_selected_interval_seconds(self):
        """Return the selected GitHub check interval in seconds."""
        return self.interval_by_label.get(self.interval_var.get(), constants.GITHUB_CHECK_INTERVAL)

    def get_bot_loop(self):
        """Return the Discord bot loop when it is ready."""
        loop = getattr(Client, "loop", None)

        if loop and hasattr(loop, "call_soon_threadsafe") and not loop.is_closed():
            return loop

        return None

    def on_interval_selected(self, event=None):
        """Apply the selected GitHub check interval."""
        self.check_interval_seconds = self.get_selected_interval_seconds()

        if self.bot_running:
            loop = self.get_bot_loop()
            if not loop:
                try:
                    set_github_check_interval(self.check_interval_seconds)
                except Exception as e:
                    self.append_log(f"Error setting check interval: {str(e)}", "error")
                return

            loop.call_soon_threadsafe(self.apply_interval_on_bot_loop, self.check_interval_seconds)
            return

        try:
            set_github_check_interval(self.check_interval_seconds)
        except Exception as e:
            self.append_log(f"Error setting check interval: {str(e)}", "error")

    def apply_interval_on_bot_loop(self, seconds):
        """Apply interval changes from the Discord bot thread."""
        try:
            set_github_check_interval(seconds)
        except Exception as e:
            self.append_log(f"Error setting check interval: {str(e)}", "error")
        
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
        if threading.get_ident() != self.gui_thread_id:
            try:
                self.root.after(0, self.append_log, text, tag)
            except tk.TclError:
                pass
            return

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
            self.force_check_button.config(state=tk.DISABLED if self.force_check_running else tk.NORMAL)
        else:
            self.status_indicator.itemconfig(self.status_circle, fill="#ff4444")
            self.status_label.config(text="Stopped", fg="#ff4444")
            self.start_button.config(state=tk.NORMAL)
            self.stop_button.config(state=tk.DISABLED)
            self.force_check_button.config(state=tk.DISABLED)
            
    def start_bot(self):
        """Start the Discord bot in a separate thread"""
        if not self.bot_running:
            if not self.bot_token or self.bot_token == "":
                self.append_log("ERROR: DISCORD_BOT_TOKEN not found in .env file!", "error")
                return

            try:
                set_github_check_interval(self.check_interval_seconds)
            except Exception as e:
                self.append_log(f"ERROR: Could not set GitHub check interval: {str(e)}", "error")
                return
                
            self.bot_running = True
            self.update_status(True)
            self.append_log("Starting CommitsBot...", "success")
            
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

    def force_check_now(self):
        """Run an immediate GitHub commit check."""
        if not self.bot_running:
            self.append_log("Start the bot before running a manual check.", "warning")
            return

        loop = self.get_bot_loop()
        if not loop:
            self.append_log("Bot event loop is not ready yet; try again in a moment.", "warning")
            return

        self.force_check_running = True
        self.update_status(True)
        self.append_log("Manual GitHub check queued.", "info")

        future = asyncio.run_coroutine_threadsafe(force_github_commit_check(), loop)
        future.add_done_callback(self.on_force_check_done)

    def on_force_check_done(self, future):
        """Handle completion of a manual GitHub check."""
        def finish():
            self.force_check_running = False
            self.update_status(self.bot_running)

            try:
                future.result()
            except Exception as e:
                self.append_log(f"Manual GitHub check failed: {str(e)}", "error")

        try:
            self.root.after(0, finish)
        except tk.TclError:
            pass
            
    def stop_bot(self):
        """Stop the Discord bot"""
        if self.bot_running:
            self.append_log("Stopping bot...", "warning")
            self.bot_running = False
            self.force_check_running = False
            
            try:
                # Close the bot
                loop = self.get_bot_loop()
                if loop:
                    asyncio.run_coroutine_threadsafe(Client.close(), loop)
                    self.append_log("Bot stopped successfully", "info")
                else:
                    self.append_log("Bot event loop was already stopped", "warning")
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
