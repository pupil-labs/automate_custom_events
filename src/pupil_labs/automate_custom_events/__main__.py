from pathlib import Path
import tkinter as tk
from tkinter import ttk
from tkinter.font import Font
import sv_ttk
import asyncio
from pupil_labs.automate_custom_events.tk_utils import TTKFormLayoutHelper, FolderSelector
from pupil_labs.automate_custom_events.control_modules import run_modules


# Function to toggle visibility of the general parameters frame
def toggle_general_parameters():
    if general_frame.winfo_viewable():
        general_frame.grid_remove()  # Hide the general parameters frame
        general_title.grid_remove()  # Hide the general parameters title
    else:
        general_title.grid(row=layout_helper.row_idx)  # Show the title
        general_frame.grid(row=layout_helper.row_idx + 1, column=0, columnspan=2, sticky='ew')  # Show the general parameters frame


async def run_task():
    try:
        rec_id = rec_id_entry.get()
        workspace_id = workspace_id_entry.get()
        cloud_token = cloud_token_entry.get()
        prompt_description = prompt_entry.get("1.0", "end-1c")
        event_code = prompt_event_entry.get("1.0", "end-1c")
        batch_size = batch_entry.get()
        start_time_seconds = start_entry.get()
        end_time_seconds = end_entry.get()

        openai_api_key = openai_key_entry.get()
        download_path = Path(download_path_entry.get())
        recpath = Path(download_path / rec_id)

        await run_modules(openai_api_key, workspace_id, rec_id, cloud_token, download_path, recpath,
                          prompt_description, event_code, batch_size,
                          start_time_seconds, end_time_seconds)
    finally:
        progress_bar.stop()
        run_button.config(state="normal")


def clear_module_fields():
    """Helper function to clear all general parameters and prompt fields."""
    widgets = [
        rec_id_entry,
        workspace_id_entry,
        cloud_token_entry,
        openai_key_entry,
        prompt_entry,
        prompt_event_entry,
        batch_entry,
        start_entry,
        end_entry
    ]

    for widget in widgets:
        if isinstance(widget, tk.Text):
            widget.delete("1.0", tk.END)
        else:
            widget.delete(0, tk.END)


async def on_run_click():
    progress_bar.start()  # Start progress bar
    run_button.config(state="disabled")  # Disable run button to prevent multiple clicks
    await run_task()
    progress_bar.stop()


# Create the main window
root = tk.Tk()
root.title("Module Controller")
root.geometry("600x1000")

root.columnconfigure(0, weight=0)
root.columnconfigure(1, weight=1)

# Set a built-in ttk theme
sv_ttk.set_theme("dark")
style = ttk.Style(root)

heading_font = Font(font=style.lookup("TLabel", "font"), weight="bold")
heading_font.configure(size=heading_font.cget("size"))
style.configure("TLabel", padding=(20, 5))
style.configure("Heading.TLabel", font=heading_font, padding=(10, 20))
style.configure("Accent.TButton", foreground="blue")
layout_helper = TTKFormLayoutHelper(root)

# Title for General Parameters (initially hidden)
general_title = tk.Label(root, text="General Parameters", font=heading_font)

# General parameters (in a frame)
general_frame = ttk.Frame(root)

# Create labeled entries for the general parameters using the helper functions
rec_id_entry = layout_helper.create_labeled_entry(general_frame, 'Recording ID', row=0, default_value='006875b0-0b90-46f7-858d-c949495804fa')
workspace_id_entry = layout_helper.create_labeled_entry(general_frame, 'Workspace ID', row=1, default_value='d6bde22c-0c74-4d7d-8ab6-65b665c3cb4e')
cloud_token_entry = layout_helper.create_labeled_entry(general_frame, 'Cloud API Token', row=2, show='*', default_value='CgwCxAZy4weDcaxmzpsDjWKPKsqTYbUY4DmdgwrP8GTa')
openai_key_entry = layout_helper.create_labeled_entry(general_frame, 'OpenAI API Key', row=3, show='*', default_value='sk-r6tWCqoKli236HVXvHvgUO9ZPCzTJWmE31zu8d4zhQT3BlbkFJ88iso4ktkTr-CvkJzofYGblisQPYZFFR-w3zqHX-4A')
download_path_entry = layout_helper.create_labeled_folder_selector(general_frame, 'Download Path', row=4, default_path=Path.cwd())
batch_entry = layout_helper.create_labeled_entry(general_frame, 'Frame batch', row=5, default_value='20')
start_entry = layout_helper.create_labeled_entry(general_frame, 'Start (s)', row=6, default_value='60')
end_entry = layout_helper.create_labeled_entry(general_frame, 'End (s)', row=7, default_value='125')

# Toggle Button for General Parameters
toggle_button = ttk.Button(root, text="Select recording", command=toggle_general_parameters)
layout_helper.add_row('', toggle_button, {'pady': 10})

# Initially hide the general parameters section
general_frame.grid(row=layout_helper.row_idx, column=0, columnspan=2, sticky='ew')
general_frame.grid_remove()  # Hide at start
general_title.grid_remove()  # Hide title at start

# Prompts (always visible) in a separate frame
prompts_frame = ttk.Frame(root)
layout_helper.add_heading('Analyze this egocentric video, the red circle in the overlay indicates where the wearer is looking. \nNote the times when...')
prompt_entry = tk.Text(root, height=5, width=50, bg='gray', fg='white')
layout_helper.add_row(' ', prompt_entry, {'pady': 10})
layout_helper.add_heading('... and report them with the following event names.')
prompt_event_entry = tk.Text(root, height=5, width=50, bg='gray', fg='white')
layout_helper.add_row(' ', prompt_event_entry, {'pady': 10})

# Place the prompts frame initially below the general parameters
prompts_frame.grid(row=layout_helper.row_idx + 1, column=0, columnspan=2, sticky='ew')

# Buttons
layout_helper.add_spacer_row()
clear_button = ttk.Button(root, text="Reset form", command=clear_module_fields, style='TButton')
layout_helper.add_row('', clear_button, {'pady': 10})

run_button = ttk.Button(root, text="Compute", command=lambda: asyncio.run(on_run_click()), style='Accent.TButton')
layout_helper.add_row('', run_button, {'pady': 10})

# Progress bar
progress_bar = layout_helper.add_row('', ttk.Progressbar(root, mode='indeterminate'))

# Start the GUI event loop
root.mainloop()