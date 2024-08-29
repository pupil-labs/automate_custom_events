import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
import asyncio
from pathlib import Path
from pupil_labs.automate_custom_events.control_modules import run_modules

async def run_task():
    try:
        # Simulate long-running task
        await asyncio.sleep(5)
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

        OPENAI_API_KEY = openai_key_entry.get()
        DOWNLOAD_PATH = Path(download_path_entry.get())
        recpath = Path(DOWNLOAD_PATH / rec_id)

        await run_modules(OPENAI_API_KEY, workspace_id, rec_id, cloud_token, DOWNLOAD_PATH, recpath, 
                          gm_description, gm_event_code, arm_activity1, arm_event_code1, batch_size,
                          start_time_seconds, end_time_seconds)
    finally:
        progress_bar.stop()
        run_button.config(state="normal")

def clear_module_fields():
    # Hide all module-specific fields and buttons
    for widget in [description_label, description_entry,
                   activity1_label, activity1_entry, code1_label, code1_entry, 
                     object_event_label, object_event_entry, start_entry, start_label, end_entry, end_label,
                   run_button, clear_button]:
        widget.grid_remove()

async def on_run_click():
    progress_bar.start(10)  # Start progress bar
    run_button.config(state="disabled")  # Disable run button to prevent multiple clicks
    await run_task()

# Create the main window
root = tk.Tk()
root.title("Module Controller")
root.geometry("800x700")

#  Set a built-in ttk theme
style = ttk.Style(root)
root.tk.call('source', './src/pupil_labs/automate_custom_events/Azure-ttk-theme-main/azure.tcl')  # Put here the path of your theme file

# Set the theme with the theme_use method
root.tk.call("set_theme", "dark")

font_style = ('Helvetica', 15)
title_font_style = ('Helvetica', 18, 'bold')

# General parameters title
general_params_label = ttk.Label(root, text="General Parameters", font=title_font_style)
general_params_label.grid(row=0, column=0, columnspan=2, padx=10, pady=10)

# General parameters
ttk.Label(root, text="Recording ID:", font=font_style).grid(row=1, column=0, padx=10, pady=5)
rec_id_entry = ttk.Entry(root, font=font_style)
rec_id_entry.grid(row=1, column=1, padx=10, pady=5)
rec_id_entry.insert(0, '')

ttk.Label(root, text="Workspace ID:", font=font_style).grid(row=2, column=0, padx=10, pady=5)
workspace_id_entry = ttk.Entry(root, font=font_style)
workspace_id_entry.grid(row=2, column=1, padx=10, pady=5)
workspace_id_entry.insert(0, "")

ttk.Label(root, text="Cloud API Token:", font=font_style).grid(row=3, column=0, padx=10, pady=5)
cloud_token_entry = ttk.Entry(root, font=font_style, show='*')
cloud_token_entry.grid(row=3, column=1, padx=10, pady=5)
cloud_token_entry.insert(0, "")

ttk.Label(root, text="OpenAI API Key:", font=font_style).grid(row=4, column=0, padx=10, pady=5)
openai_key_entry = ttk.Entry(root, font=font_style, show='*')
openai_key_entry.grid(row=4, column=1, padx=10, pady=5)
openai_key_entry.insert(0, "")

ttk.Label(root, text="Download Path:", font=font_style).grid(row=5, column=0, padx=10, pady=5)
download_path_entry = ttk.Entry(root, font=font_style)
download_path_entry.grid(row=5, column=1, padx=10, pady=5)
download_path_entry.insert(0, "/Users/nadiapl/Downloads/recs.zip")

# Gaze Module prompts title
gaze_module_label = ttk.Label(root, text="Gaze Module Prompts", font=title_font_style)
gaze_module_label.grid(row=6, column=0, columnspan=2, padx=10, pady=10)

# Gaze Module fields
description_label = ttk.Label(root, text="Gaze behaviour description:", font=font_style)
description_entry = ttk.Entry(root, font=font_style, width=50)
description_label.grid(row=7, column=0, padx=10, pady=5)
description_entry.grid(row=7, column=1,  padx=20, pady=20, ipadx=10, ipady=10)
description_entry.insert(0, "")

object_event_label = ttk.Label(root, text="Event:", font=font_style)
object_event_entry = ttk.Entry(root, font=font_style)
object_event_label.grid(row=8, column=0, padx=10, pady=5)
object_event_entry.grid(row=8, column=1, padx=10, pady=5)
object_event_entry.insert(0, "")

# Activity Recognition prompts title
activity_recognition_label = ttk.Label(root, text="Activity Recognition Prompts", font=title_font_style)
activity_recognition_label.grid(row=9, column=0, columnspan=2, padx=10, pady=10)

# Activity Recognition fields
activity1_label = ttk.Label(root, text="Activity:", font=font_style)
activity1_entry = ttk.Entry(root, font=font_style, width=50)  # Adjust width to make it visually bigger
activity1_label.grid(row=10, column=0, padx=10, pady=5)
activity1_entry.grid(row=10, column=1, padx=20, pady=20, ipadx=10, ipady=10)  # Add internal padding for larger appearance
activity1_entry.insert(0, "")


code1_label = ttk.Label(root, text="Event:", font=font_style)
code1_entry = ttk.Entry(root, font=font_style)
code1_label.grid(row=11, column=0, padx=10, pady=5)
code1_entry.grid(row=11, column=1, padx=10, pady=5)
code1_entry.insert(0, "")

batch_label = ttk.Label(root, text="Frame batch:", font=font_style)
batch_entry = ttk.Entry(root, font=font_style)
batch_label.grid(row=12, column=0, padx=10, pady=5)
batch_entry.grid(row=12, column=1, padx=10, pady=5)
batch_entry.insert(0, 30)

start_label = ttk.Label(root, text="Start (s):", font=font_style)
start_entry = ttk.Entry(root, font=font_style)
start_label.grid(row=13, column=0, padx=10, pady=5)
start_entry.grid(row=13, column=1, padx=10, pady=5)
start_entry.insert(0, 0)

end_label = ttk.Label(root, text="End (s):", font=font_style)
end_entry = ttk.Entry(root, font=font_style)
end_label.grid(row=14, column=0, padx=10, pady=5)
end_entry.grid(row=14, column=1, padx=10, pady=5)
end_entry.insert(0, 15)

# Themed buttons
style.configure('TButton', font=font_style, padding=10)
style.configure('Accent.TButton', foreground='blue')

run_button = ttk.Button(root, text="Run Modules", command=lambda: asyncio.run(on_run_click()), style='Accent.TButton')
clear_button = ttk.Button(root, text="Clear Fields", command=clear_module_fields, style='TButton')
run_button.grid(row=15, column=0, columnspan=2, pady=5)
clear_button.grid(row=16, column=0, columnspan=2, pady=5)

# Progress bar
progress_bar = ttk.Progressbar(root, mode='indeterminate')
progress_bar.grid(row=17, column=0, columnspan=2, pady=10, sticky='ew')

# Start the GUI event loop
root.mainloop()
