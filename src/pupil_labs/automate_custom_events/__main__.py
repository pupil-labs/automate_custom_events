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


class App:
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
        # Create the main window
        self.root = tk.Tk()
        self.root.title("Annotator Assistant")
        self.root.geometry("600x1000")  # Adjusted window size

        # Center the main window
        self.root.update_idletasks()
        width = self.root.winfo_width()
        height = self.root.winfo_height()
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry(f"+{x}+{y}")

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

        heading_font = Font(font=style.lookup("TLabel", "font"))
        heading_font.configure(size=heading_font.cget("size"))
        style.configure("TLabel", padding=(10, 5))
        style.configure("Heading.TLabel", font=heading_font, padding=(10, 10))
        style.configure("Accent.TButton", foreground="blue")
        layout_helper = TTKFormLayoutHelper(self.root)

        # Main frame to center content with consistent margins
        main_frame = ttk.Frame(self.root, padding=(40, 20, 20, 20))  # Added left and right padding
        main_frame.grid(column=0, row=0, sticky="nsew")
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)

        # Center the main_frame contents by configuring row and column weights
        for col in range(2):
            main_frame.columnconfigure(col, weight=1)

        # Toggle Button for General Parameters at the top
        toggle_button = ttk.Button(
            main_frame, text="Select Recording", command=self.toggle_general_parameters
        )
        toggle_button.grid(row=0, column=0, columnspan=2, pady=(10, 10), sticky="ew")

        # General parameters (in a frame)
        self.general_frame = ttk.Frame(main_frame)

        # Create labeled entries for the general parameters using the helper functions
        bg = "#000000"
        entry_fg = "white"

        self.url_entry = layout_helper.create_labeled_entry(
            self.general_frame,
            "Recording Link",
            row=0,
            default_value="",
        )
        self.cloud_token_entry = layout_helper.create_labeled_entry(
            self.general_frame,
            "Cloud API Token",
            row=1,
            show="*",
            default_value="",
        )
        self.openai_key_entry = layout_helper.create_labeled_entry(
            self.general_frame,
            "OpenAI API Key",
            row=2,
            show="*",
            default_value="",
        )
        self.download_path_entry = layout_helper.create_labeled_folder_selector(
            self.general_frame, "Download Path", row=3, default_path=Path.cwd()
        )
        self.batch_entry = layout_helper.create_labeled_entry(
            self.general_frame, "Frame batch", row=4, default_value=""
        )
        self.start_entry = layout_helper.create_labeled_entry(
            self.general_frame, "Start (s)", row=5, default_value=""
        )
        self.end_entry = layout_helper.create_labeled_entry(
            self.general_frame, "End (s)", row=6, default_value=""
        )

        # Initially hide the general parameters section
        self.general_frame.grid(row=2, column=0, columnspan=2, sticky="ew")
        self.general_frame.grid_remove()  # Hide at start

        # Layout helper reset for main_frame
        layout_helper = TTKFormLayoutHelper(main_frame)

        # Prompts (always visible)
        layout_helper.row_idx = 3  # Start from row 3 to ensure correct placement

        layout_helper.add_heading_2(
            "Analyze this egocentric video. The red circle in the overlay indicates where the wearer is looking. Note the times when...",
            heading_font,
        )
        # Insert background for prompt entry
        self.prompt_entry = tk.Text(
            main_frame, height=5, width=80, bg=bg, fg=entry_fg, insertbackground="white"
        )
        layout_helper.add_row(
            "", self.prompt_entry, {"pady": 10, "sticky": "ew"}
        )  # Added sticky='ew' to ensure text fills the width

        layout_helper.add_heading("... and report them as the following events.")
        self.prompt_event_entry = tk.Text(
            main_frame, height=5, width=80, bg=bg, fg=entry_fg, insertbackground="white"
        )
        layout_helper.add_row(
            "", self.prompt_event_entry, {"pady": 10, "sticky": "ew"}
        )  # Added sticky='ew' to ensure text fills the width

        # Add buttons below the prompt entries
        clear_button = ttk.Button(
            main_frame, text="Reset Form", command=self.clear_module_fields, style="TButton"
        )
        clear_button.grid(
            row=layout_helper.row_idx, column=0, columnspan=2, pady=(10, 0), sticky="ew"
        )

        run_button = ttk.Button(
            main_frame, text="Compute", command=self.on_run_click, style="Compute.TButton"
        )
        run_button.grid(
            row=layout_helper.row_idx + 1, column=0, columnspan=2, pady=(10, 10), sticky="ew"
        )

        # Progress bar below the buttons
        progress_bar = ttk.Progressbar(
            main_frame, mode="indeterminate", style="Custom.Horizontal.TProgressbar"
        )
        progress_bar.grid(
            row=layout_helper.row_idx + 2, column=0, columnspan=2, pady=(10, 10), sticky="ew"
        )

        # Console output label and text area
        console_label = ttk.Label(main_frame, text="Console Output:", style="Heading.TLabel")
        console_label.grid(
            row=layout_helper.row_idx + 3, column=0, columnspan=2, pady=(10, 0), sticky="w"
        )

        self.console_text = tk.Text(
            main_frame,
            height=10,
            width=80,
            state="disabled",
            bg=bg,
            fg=entry_fg,
            wrap="word",
        )
        self.console_text.grid(
            row=layout_helper.row_idx + 4, column=0, columnspan=2, pady=(5, 10), sticky="nsew"
        )

        # Configure row and column weights for console_text to expand
        main_frame.rowconfigure(layout_helper.row_idx + 4, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.columnconfigure(1, weight=1)

    def on_run_click(self):
        def task():
            asyncio.run(self.run_task())
            # Re-enable the run button and stop the progress bar in the main thread
            self.root.after(0, lambda: self.run_button.config(state="normal"))
            self.root.after(0, self.progress_bar.stop)

        self.progress_bar.start()  # Start progress bar
        self.run_button.config(state="disabled")  # Disable run button to prevent multiple clicks
        threading.Thread(target=task).start()

    # Function to toggle visibility of the general parameters frame
    def toggle_general_parameters(self):
        if self.general_frame.winfo_viewable():
            self.general_frame.grid_remove()  # Hide the general parameters frame
        else:
            self.general_frame.grid(
                row=2, column=0, columnspan=2, sticky="ew"
            )  # Show the general parameters frame

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

    async def run_task(self):
        try:
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
            recpath = Path(download_path / rec_id)
            await run_modules(
                openai_api_key,
                workspace_id,
                rec_id,
                cloud_token,
                download_path,
                recpath,
                prompt_description,
                event_code,
                batch_size,
                start_time_seconds,
                end_time_seconds,
            )
        finally:
            pass

    def execute(self):
        # Start the GUI event loop
        self.root.mainloop()


def run_main():
    app = App()
    app.execute()

if __name__ == "__main__":
    run_main()