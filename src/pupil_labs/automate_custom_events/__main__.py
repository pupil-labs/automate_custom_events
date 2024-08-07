import tkinter as tk
from tkinter import ttk
import asyncio
from pathlib import Path
import pandas as pd
import os
from pupil_labs.automate_custom_events.control_modules import run_gaze_module, run_activity_recognition_module  # Ensure the main script is named main.py or adjust the import accordingly

def show_gaze_module_fields():
    # Clear previous fields
    clear_module_fields()

    # Show Gaze Module specific fields
    object_label.grid(row=7, column=0, padx=10, pady=5)
    object_entry.grid(row=7, column=1, padx=10, pady=5)
    description_label.grid(row=8, column=0, padx=10, pady=5)
    description_entry.grid(row=8, column=1, padx=10, pady=5)
    object_event_label.grid(row=9, column=0, padx=10, pady=5)
    object_event_entry.grid(row=9, column=1, padx=10, pady=5)

    run_button_gaze.grid(row=10, column=0, columnspan=2, pady=5)
    skip_button_gaze.grid(row=11, column=0, columnspan=2, pady=5)

def show_activity_recognition_module_fields():
    # Clear previous fields
    clear_module_fields()

    # Show Activity Recognition Module specific fields
    object_label.grid(row=7, column=0, padx=10, pady=5)
    object_entry.grid(row=7, column=1, padx=10, pady=5)
    activity1_label.grid(row=8, column=0, padx=10, pady=5)
    activity1_entry.grid(row=8, column=1, padx=10, pady=5)
    activity2_label.grid(row=9, column=0, padx=10, pady=5)
    activity2_entry.grid(row=9, column=1, padx=10, pady=5)
    code1_label.grid(row=10, column=0, padx=10, pady=5)
    code1_entry.grid(row=10, column=1, padx=10, pady=5)
    code2_label.grid(row=11, column=0, padx=10, pady=5)
    code2_entry.grid(row=11, column=1, padx=10, pady=5)
    run_button_activity.grid(row=12, column=0, columnspan=2, pady=5)
    skip_button_activity.grid(row=13, column=0, columnspan=2, pady=5)
    
def clear_module_fields():
    # Hide all module-specific fields and buttons
    for widget in [object_label, object_entry, description_label, description_entry,
                   activity1_label, activity1_entry, activity2_label, activity2_entry, code1_label, code1_entry, 
                   code2_label, code2_entry, object_event_label, object_event_entry,
                   run_button_gaze, skip_button_gaze, run_button_activity, skip_button_activity]:
        widget.grid_remove()


def on_run_gaze_click():
    rec_id = rec_id_entry.get()
    workspace_id = workspace_id_entry.get()
    cloud_token = cloud_token_entry.get()
    object_desc = object_entry.get()
    description = description_entry.get()
    event_code = object_event_entry.get()
    OPENAI_API_KEY = openai_key_entry.get()
    DOWNLOAD_PATH = Path(download_path_entry.get())
    recpath = Path(DOWNLOAD_PATH / rec_id)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_gaze_module(OPENAI_API_KEY, workspace_id, rec_id, cloud_token, DOWNLOAD_PATH, recpath, object_desc, description, event_code))

def on_run_activity_click():
    rec_id = rec_id_entry.get()
    workspace_id = workspace_id_entry.get()
    cloud_token = cloud_token_entry.get()
    object_desc = object_entry.get()
    activity1 = activity1_entry.get()
    activity2 = activity2_entry.get()
    event_code1 = code1_entry.get()
    event_code2 = code2_entry.get()
    OPENAI_API_KEY = openai_key_entry.get()
    DOWNLOAD_PATH = Path(download_path_entry.get())
    recpath = Path(DOWNLOAD_PATH / rec_id)

    loop = asyncio.get_event_loop()
    loop.run_until_complete(run_activity_recognition_module(OPENAI_API_KEY, workspace_id, rec_id, cloud_token, DOWNLOAD_PATH, recpath, object_desc, activity1, activity2, event_code1, event_code2))

# Create the main window
root = tk.Tk()
root.title("Module Controller")
root.geometry("600x800")

# Set a modern font
font_style = ('Helvetica', 15)

# General parameters
ttk.Label(root, text="Recording ID:",font=font_style).grid(row=0, column=0, padx=10, pady=5)
rec_id_entry = ttk.Entry(root,font=font_style)
rec_id_entry.grid(row=0, column=1, padx=10, pady=5)

ttk.Label(root, text="Workspace ID:",font=font_style).grid(row=1, column=0, padx=10, pady=5)
workspace_id_entry = ttk.Entry(root,font=font_style)
workspace_id_entry.grid(row=1, column=1, padx=10, pady=5)

ttk.Label(root, text="Cloud API Token:",font=font_style).grid(row=2, column=0, padx=10, pady=5)
cloud_token_entry = ttk.Entry(root,font=font_style)
cloud_token_entry.grid(row=2, column=1, padx=10, pady=5)

ttk.Label(root, text="OpenAI API Key:",font=font_style).grid(row=3, column=0, padx=10, pady=5)
openai_key_entry = ttk.Entry(root,font=font_style)
openai_key_entry.grid(row=3, column=1, padx=10, pady=5)

ttk.Label(root, text="Download Path:",font=font_style).grid(row=4, column=0, padx=10, pady=5)
download_path_entry = ttk.Entry(root,font=font_style)
download_path_entry.grid(row=4, column=1, padx=10, pady=5)

# Buttons for module selection
ttk.Button(root, text="Gaze Module", command=show_gaze_module_fields).grid(row=5, column=0, columnspan=2, pady=10)
ttk.Button(root, text="Activity Recognition Module", command=show_activity_recognition_module_fields).grid(row=6, column=0, columnspan=2, pady=10)

# Module-specific fields (initially hidden)
object_label = ttk.Label(root, text="Object description:",font=font_style)
object_entry = ttk.Entry(root,font=font_style)

description_label = ttk.Label(root, text="Detailed description:",font=font_style)
description_entry = ttk.Entry(root,font=font_style)

object_event_label = ttk.Label(root, text="Event for gaze module:",font=font_style)
object_event_entry = ttk.Entry(root,font=font_style)

activity1_label = ttk.Label(root, text="Activity 1:",font=font_style)
activity1_entry = ttk.Entry(root,font=font_style)

code1_label = ttk.Label(root, text="Event for Activity 1:",font=font_style)
code1_entry = ttk.Entry(root,font=font_style)

activity2_label = ttk.Label(root, text="Activity 2:",font=font_style)
activity2_entry = ttk.Entry(root,font=font_style)

code2_label = ttk.Label(root, text="Event for Activity 2:",font=font_style)
code2_entry = ttk.Entry(root,font=font_style)

# Themed buttons
style = ttk.Style()
style.configure('TButton', font=font_style, padding=10)
style.configure('Accent.TButton', foreground='blue')

run_button_gaze = ttk.Button(root, text="Run Gaze Module", command=on_run_gaze_click, style='Accent.TButton')
skip_button_gaze = ttk.Button(root, text="Skip Gaze Module", command=clear_module_fields, style='TButton')

run_button_activity = ttk.Button(root, text="Run Activity Recognition Module", command=on_run_activity_click, style='Accent.TButton')
skip_button_activity = ttk.Button(root, text="Skip Activity Recognition Module", command=clear_module_fields, style='TButton')

# Start the GUI event loop
root.mainloop()