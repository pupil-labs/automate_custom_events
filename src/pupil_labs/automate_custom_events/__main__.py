from pathlib import Path
import tkinter as tk
from tkinter import ttk
from tkinter.font import Font
import sv_ttk
import asyncio
import threading
import logging
import re

from pupil_labs.automate_custom_events.tk_utils import TTKFormLayoutHelper, FolderSelector, ConsoleText, WrappedLabel
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
            self.text_widget.insert(tk.END, msg + "\n", record.levelname)
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
        self.root.geometry("600x1000")
        self.root.configure(padx=10, pady=10)

        self.setup_styles()

        self.toggle_button = ttk.Label(self.root, text="⯆ Settings", style="Heading.TLabel")
        self.toggle_button.bind("<Button-1>", lambda _: self.toggle_settings_form())
        self.toggle_button.pack(fill="x")

        self.settings_form = self.create_settings_form(self.root)
        self.settings_form.pack(fill="x", padx=(25, 0))

        heading = WrappedLabel(
            self.root,
            text="Analyze this egocentric video. The red circle in the overlay indicates where the wearer is looking. Note the times when...",
            style="Heading.TLabel",
        )
        heading.pack(fill="x")

        # Insert background for prompt entry
        self.prompt_entry = tk.Text(self.root, height=5, width=80)
        self.prompt_entry.pack(fill="x", padx=(25, 0))

        heading = WrappedLabel(
            self.root,
            text="Report them as the following events.",
            style="Heading.TLabel"
        )
        heading.pack(fill="x")

        self.prompt_event_entry = tk.Text(self.root, height=5, width=80)
        self.prompt_event_entry.pack(fill="x", padx=(25, 0))

        # Add buttons below the prompt entries
        self.run_button = ttk.Button(
            self.root, text="Compute", command=self.on_run_click, style="Compute.TButton"
        )
        self.run_button.pack(fill="x", pady=10)

        # Progress bar below the buttons
        self.progress_bar = ttk.Progressbar(
            self.root, mode="indeterminate", style="Custom.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(fill="x")

        # Console output label and text area
        heading = WrappedLabel(self.root, text="Console Output", style="Heading.TLabel")
        heading.pack(fill="x")

        self.console_text = ConsoleText(
            self.root,
            state="disabled",
            bg="#000000",
            fg="#ffffff",
            wrap="none",
        )
        self.console_text.pack(fill="both", expand=True)

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
            [(
                "Button.padding",
                {
                    "children": [("Button.label", {"sticky": "nswe"})],
                    "sticky": "nswe"
                },
            )],
        )

        style.configure(
            "Custom.Horizontal.TProgressbar", troughcolor="white", background="#6D7BE0"
        )

        heading_font = Font(font=style.lookup("TLabel", "font"))
        heading_font.configure(size=heading_font.cget("size"))
        style.configure("TLabel", padding=(10, 5))
        style.configure("Heading.TLabel", font=heading_font, padding=(10, 10))
        style.configure("Accent.TButton", foreground="blue")

    def create_settings_form(self, container):
        frame = ttk.Frame(container)
        frame.grid_columnconfigure(1, weight=1)

        form_layout = TTKFormLayoutHelper(frame)

        self.url_entry = form_layout.create_labeled_entry(frame, "Recording Link")
        self.cloud_token_entry = form_layout.create_labeled_entry(frame, "Cloud API Token", show="*")
        self.openai_key_entry = form_layout.create_labeled_entry(frame, "OpenAI API Key", show="*")

        self.download_path_entry = FolderSelector(frame, Path.cwd())
        form_layout.add_row("Download Path", self.download_path_entry)

        self.batch_entry = form_layout.create_labeled_entry(frame, "Frame batch")
        self.start_entry = form_layout.create_labeled_entry(frame, "Start (s)")
        self.end_entry = form_layout.create_labeled_entry(frame, "End (s)")

        clear_button = ttk.Button(
            frame, text="Reset Form", command=self.clear_module_fields, style="TButton"
        )
        form_layout.add_row("", clear_button)

        return frame

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

    def toggle_settings_form(self):
        if self.settings_form.winfo_ismapped():
            self.settings_form.pack_forget()
            self.toggle_button.config(text="⯈ Settings")
        else:
            self.settings_form.pack(fill="x", after=self.toggle_button, padx=(25, 0))
            self.toggle_button.config(text="⯆ Settings")

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

    def execute(self):
        self.root.mainloop()


def run_main():
    app = App()
    app.execute()

if __name__ == "__main__":
    run_main()