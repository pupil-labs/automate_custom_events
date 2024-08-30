from pathlib import Path

import tkinter as tk
from tkinter import ttk
from tkinter.font import Font

import sv_ttk
import asyncio

from pupil_labs.automate_custom_events.tk_utils import TTKFormLayoutHelper, FolderSelector
from pupil_labs.automate_custom_events.control_modules import run_modules


async def run_task():
    try:
        rec_id = rec_id_entry.get()
        workspace_id = workspace_id_entry.get()
        cloud_token = cloud_token_entry.get()
        gm_description = description_entry.get()
        gm_event_code = object_event_entry.get()
        arm_activity1 = activity1_entry.get()
        arm_event_code1 = code1_entry.get()
        batch_size = batch_entry.get()
        start_time_seconds = start_entry.get()
        end_time_seconds = end_entry.get()

        openai_api_key = openai_key_entry.get()
        download_path = Path(download_path_entry.get())
        recpath = Path(download_path / rec_id)

        await run_modules(openai_api_key, workspace_id, rec_id, cloud_token, download_path, recpath,
                          gm_description, gm_event_code, arm_activity1, arm_event_code1, batch_size,
                          start_time_seconds, end_time_seconds)
    finally:
        progress_bar.stop()
        run_button.config(state="normal")


def clear_module_fields():
    # Hide all module-specific fields and buttons
    widgets = [
        description_entry,
        activity1_entry,
        code1_entry,
        object_event_entry,
        batch_entry,
        start_entry,
        end_entry
    ]

    for widget in widgets:
        widget.delete(0, tk.END)


async def on_run_click():
    progress_bar.start()  # Start progress bar
    run_button.config(state="disabled")  # Disable run button to prevent multiple clicks
    await run_task()
    progress_bar.stop()


# Create the main window
root = tk.Tk()
root.title("Module Controller")
root.geometry("600x800")

root.columnconfigure(0, weight=0)
root.columnconfigure(1, weight=1)

#  Set a built-in ttk theme
sv_ttk.set_theme("dark")
style = ttk.Style(root)

heading_font = Font(font=style.lookup("TLabel", "font"), weight="bold")
heading_font.configure(size=heading_font.cget("size"))
style.configure("TLabel", padding=(20, 5))
style.configure("Heading.TLabel", font=heading_font, padding=(10, 20))
style.configure("Accent.TButton", foreground="blue")

layout_helper = TTKFormLayoutHelper(root)

# General parameters
layout_helper.add_heading('General Parameters')
rec_id_entry = layout_helper.add_row('Recording ID')
workspace_id_entry = layout_helper.add_row('Workspace ID')
cloud_token_entry = layout_helper.add_row('Cloud API Token')
cloud_token_entry.configure(show='*')
openai_key_entry = layout_helper.add_row('OpenAI API Key')
openai_key_entry.configure(show='*')
download_path_entry = FolderSelector(root, Path.cwd())
layout_helper.add_row('Download Path', download_path_entry)

# Gaze Module fields
layout_helper.add_heading('Gaze Module Prompts')
description_entry = layout_helper.add_row('Gaze behaviour Description')
object_event_entry = layout_helper.add_row('Event')

# Activity Recognition fields
layout_helper.add_heading('Activity Recognition Prompts')
activity1_entry = layout_helper.add_row('Activity')
code1_entry = layout_helper.add_row('Event')
batch_entry = layout_helper.add_row('Frame batch')
start_entry = layout_helper.add_row('Start (s)')
end_entry = layout_helper.add_row('End (s)')

# Buttons
layout_helper.add_spacer_row()
clear_button = ttk.Button(root, text="Reset form", command=clear_module_fields, style='TButton')
layout_helper.add_row('', clear_button, {'pady': 10})

run_button = ttk.Button(root, text="Run Modules", command=lambda: asyncio.run(on_run_click()), style='Accent.TButton')
layout_helper.add_row('', run_button, {'pady': 10})

# Progress bar
progress_bar = layout_helper.add_row('', ttk.Progressbar(root, mode='indeterminate'))

# Start the GUI event loop
root.mainloop()
