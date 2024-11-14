from pathlib import Path
import tkinter as tk
from tkinter import ttk
from tkinter.font import Font
import sv_ttk
import asyncio
import threading
import logging
import re
from pupil_labs.automate_custom_events.tk_utils import TTKFormLayoutHelper
from pupil_labs.automate_custom_events.control_modules import run_modules


def extract_ids(url):
    # Use regex to extract the workspace ID and recording ID
    workspace_pattern = r"workspaces/([a-f0-9\-]+)/"
    recording_pattern = r"id=([a-f0-9\-]+)&"

    # Find matches using regex
    workspace_match = re.search(workspace_pattern, url)
    recording_match = re.search(recording_pattern, url)

    # Extract the values if they exist
    workspace_id = workspace_match.group(1) if workspace_match else None
    recording_id = recording_match.group(1) if recording_match else None

    return workspace_id, recording_id

# Create GUI handler for the GUI console
class TextHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        self.ansi_escape = re.compile(r"\x1B\[[0-?]*[ -/]*[@-~]")

    def emit(self, record):
        msg = self.format(record)
        # Clean ANSI escape codes
        msg = self.ansi_escape.sub("", msg)

        def append():
            self.text_widget.configure(state="normal")
            self.text_widget.insert(tk.END, msg + "\n")
            self.text_widget.see(tk.END)
            self.text_widget.configure(state="disabled")

        self.text_widget.after(0, append)

class App():
    def __init__(self):
        self.setup_gui()

        # Set up logging
        logger = logging.getLogger()
        logger.setLevel(logging.DEBUG)  # Set the root logger level

        # Create formatters
        formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

        # Remove any existing handlers
        logger.handlers = []

        # Create console handler for standard console output
        console_handler = logging.StreamHandler()
        console_handler.setLevel(logging.DEBUG)  # Adjust as needed
        console_handler.setFormatter(formatter)

        gui_handler = TextHandler(self.console_text)
        gui_handler.setLevel(logging.INFO)  # Adjust level as needed
        gui_handler.setFormatter(formatter)

        # Add handlers to the logger
        logger.addHandler(console_handler)
        logger.addHandler(gui_handler)

    def setup_gui(self):
        self.root = tk.Tk()
        self.root.title("Annotator Assistant")
        self.root.geometry("600x1000")  # Adjusted window size
        layout_helper = TTKFormLayoutHelper(self.root)

        self.main_frame = ttk.Frame(self.root, padding=(40, 20, 20, 20))  # Added left and right padding
        self.main_frame.grid(column=0, row=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Center the main_frame contents by configuring row and column weights
        for col in range(2):
            self.main_frame.columnconfigure(col, weight=1)

        self.setup_styles()
        
        # Center the main window
        self.root.update_idletasks()
        self.width = self.root.winfo_width()
        self.height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (self.width // 2)
        y = (self.root.winfo_screenheight() // 2) - (self.height // 2)
        self.root.geometry(f"+{x}+{y}")

        self.toggle_button = ttk.Button(
            self.main_frame, text="Select Recording", command=self.toggle_settings_form
        )
        self.toggle_button.grid(row=0, column=0, columnspan=2, pady=(10, 10), sticky="ew")
        
         # # General parameters (in a frame; hidden)
        self.general_frame = ttk.Frame(self.main_frame)
        self.general_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.general_frame.grid_remove()  # Hide at start

        self.settings_form = self.create_settings_form(self.general_frame)
        #self.settings_form.pack(fill="x", padx=(25, 0))

        # Layout helper reset for main_frame
        layout_helper = TTKFormLayoutHelper(self.main_frame)
        layout_helper.row_idx = 3  # Start from row 3 to ensure correct placement
        layout_helper.add_heading_2(
            "Analyze this egocentric video. The red circle in the overlay indicates where the wearer is looking. Note the times when...",
            self.heading_font,
        )

        self.prompt_entry = tk.Text(
            self.main_frame, height=5, width=80, bg="#000000", fg="white", insertbackground="white"
        )
        layout_helper.add_row(
            "", self.prompt_entry, {"pady": 10, "sticky": "ew"}
        )  
        layout_helper.add_heading("... and report them as the following events.")
        self.prompt_event_entry = tk.Text(
            self.main_frame, height=5, width=80, bg="#000000", fg="white", insertbackground="white"
        )
        layout_helper.add_row(
            "", self.prompt_event_entry, {"pady": 10, "sticky": "ew"}
        )  

        # Buttons
        self.clear_button = ttk.Button(
            self.main_frame, text="Reset Form", command=self.clear_module_fields, style="TButton"
        )
        self.clear_button.grid(
            row=layout_helper.row_idx, column=0, columnspan=2, pady=(10, 10), sticky="ew"
        )

        self.run_button = ttk.Button(
            self.main_frame, text="Compute", command=self.on_run_click, style="Compute.TButton"
        )
        self.run_button.grid(
            row=layout_helper.row_idx + 1, column=0, columnspan=2, pady=(10, 10), sticky="ew"
        )
    
        # Progress bar below the buttons
        self.progress_bar = ttk.Progressbar(
            self.main_frame, mode="indeterminate", style="Custom.Horizontal.TProgressbar"
        )
        self.progress_bar.grid(
            row=layout_helper.row_idx + 2, column=0, columnspan=2, pady=(10, 10), sticky="ew"
        )

        # Console output label and text area
        self.console_label = ttk.Label(self.main_frame, text="Console Output:", style="Heading.TLabel")
        self.console_label.grid(
            row=layout_helper.row_idx + 3, column=0, columnspan=2, pady=(10, 0), sticky="w"
        )

        self.console_text = tk.Text(
            self.main_frame,
            height=10,
            width=80,
            state="disabled",
            bg="#000000",
            fg="white",
            wrap="word",
        )
        self.console_text.grid(
            row=layout_helper.row_idx + 4, column=0, columnspan=2, pady=(5, 10), sticky="nsew"
        )

        # Configure row and column weights for console_text to expand
        self.main_frame.rowconfigure(layout_helper.row_idx + 4, weight=1)
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.columnconfigure(1, weight=1)
        
    def setup_styles(self):
        # Set up the style
        sv_ttk.set_theme("dark")
        style = ttk.Style()

        # Create custom styles
        style.configure("Compute.TButton", background="#6D7BE0", foreground="white", padding=6)

        style.map(
            "Compute.TButton",
            background=[("active", "dark blue"), ("pressed", "navy"), ("disabled", "#222222")],
            foreground=[("disabled", "#424242")],
        )

        style.layout(
            "Compute.TButton",
            [
                (
                    "Button.padding",
                    {"children": [("Button.label", {"sticky": "nswe"})], "sticky": "nswe"},
                )
            ],
        )

        style.configure(
            "Custom.Horizontal.TProgressbar", troughcolor="white", background="#6D7BE0"
        )

        style.configure(
            "Custom.TEntry",
            foreground="white",
            fieldbackground="#000000",
            background="#000000",
            insertcolor="white",
        )

        self.heading_font = Font(font=style.lookup("TLabel", "font"))
        self.heading_font.configure(size=self.heading_font.cget("size"))
        style.configure("TLabel", padding=(10, 5))
        style.configure("Heading.TLabel", font=self.heading_font, padding=(10, 10))
        style.configure("Accent.TButton", foreground="blue")

    def create_settings_form(self, container):
        settings_frame = ttk.Frame(container)
        settings_frame.grid_columnconfigure(1, weight=1)

        form_layout = TTKFormLayoutHelper(settings_frame)

        self.url_entry = form_layout.create_labeled_entry(
            container,
            "Recording Link",
            row=0,
            default_value="",
        )
        self.cloud_token_entry = form_layout.create_labeled_entry(
            container,
            "Cloud API Token",
            row=1,
            show="*",
            default_value="L",
        )
        self.openai_key_entry = form_layout.create_labeled_entry(
            container,
            "OpenAI API Key",
            row=2,
            show="*",
            default_value="",
        )
        self.download_path_entry = form_layout.create_labeled_folder_selector(
            container, "Download Path", row=3, default_path=Path.cwd()
        )
        self.batch_entry = form_layout.create_labeled_entry(
            container, "Frame batch", row=4, default_value=""
        )
        self.start_entry = form_layout.create_labeled_entry(
            container, "Start (s)", row=5, default_value=""
        )
        self.end_entry = form_layout.create_labeled_entry(
            container, "End (s)", row=6, default_value=""
        )

        return container
    
    def clear_module_fields(self):
        """Helper function to clear all general parameters and prompt fields."""
        widgets = [
            self.url_entry,
            self.cloud_token_entry,
            self.openai_key_entry,
            self.prompt_entry,
            self.prompt_event_entry,
            self.batch_entry,
            self.start_entry,
            self.end_entry,
        ]

        for widget in widgets:
            if isinstance(widget, tk.Text):
                widget.delete("1.0", tk.END)
            else:
                widget.delete(0, tk.END)

    # Function to toggle visibility of the general parameters frame
    def toggle_settings_form(self):
            if self.settings_form.winfo_ismapped():
                self.settings_form.pack_forget()
                self.settings_form.grid_remove()
                self.toggle_button.config(text="Select Recording")
            else:
                self.settings_form.grid(row=2, column=0, columnspan=2, sticky="ew")
                self.toggle_button.config(text="Select Recording")

    def on_run_click(self):
        def task():
            try:
                asyncio.run(self.run_task())
            except Exception as e:
                logging.error(e, exc_info=True)

                # Re-enable the run button and stop the progress bar in the main thread
                self.root.after(0, lambda: self.run_button.config(state="normal"))
                self.root.after(0, self.progress_bar.stop)

        self.progress_bar.start()  # Start progress bar
        self.run_button.config(state="disabled")  # Disable run button to prevent multiple clicks
        threading.Thread(target=task).start()

    async def run_task(self):
        url = self.url_entry.get()
        cloud_token = self.cloud_token_entry.get()
        prompt_description = self.prompt_entry.get("1.0", "end-1c")
        event_code = self.prompt_event_entry.get("1.0", "end-1c")
        batch_size = self.batch_entry.get()
        start_time_seconds = self.start_entry.get()
        end_time_seconds = self.end_entry.get()
        openai_api_key = self.openai_key_entry.get()
        download_path = Path(self.download_path_entry.get())
        workspace_id, rec_id = extract_ids(url)
        await run_modules(
            openai_api_key,
            workspace_id,
            rec_id,
            cloud_token,
            download_path,
            prompt_description,
            event_code,
            batch_size,
            start_time_seconds,
            end_time_seconds,
        )
    def execute(self):
        self.root.mainloop()
        self.root.quit()
    
def run_main():
    app = App()
    app.execute()
    
if __name__ == "__main__":
    run_main()

