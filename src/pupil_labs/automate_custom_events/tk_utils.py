import tkinter as tk
from tkinter import ttk, filedialog


class TTKFormLayoutHelper:
    def __init__(self, root):
        self.row_idx = 0
        self.root = root

    def add_heading(self, text):
        label = ttk.Label(self.root, text=text, style="Heading.TLabel")
        label.grid(row=self.row_idx, column=0, columnspan=2, sticky="w")

        self.row_idx += 1

    def add_row(self, text, widget=None, widget_grid_args=None):
        if widget is None:
            widget = ttk.Entry(self.root)

        if widget_grid_args is None:
            widget_grid_args = {}

        label = ttk.Label(self.root, text=text)
        label.grid(row=self.row_idx, column=0, sticky="w")
        widget.grid(row=self.row_idx, column=1, sticky="ew", padx=10, **widget_grid_args)

        self.row_idx += 1
        return widget

    def add_spacer_row(self):
        label = ttk.Label(self.root)
        label.grid(row=self.row_idx, column=0, sticky="w")

        self.row_idx += 1


class FolderSelector(ttk.Frame):
    def __init__(self, parent, start_path=None, *args, **kwargs):
        super().__init__(parent, *args, **kwargs)

        self.entry = ttk.Entry(self)
        self.entry.pack(side="left", fill="x", expand=True)

        self.button = ttk.Button(self, text="...", command=self.select_folder)
        self.button.pack(side="right", padx=10)

        if start_path is not None:
            self.entry.insert(0, start_path)

    def select_folder(self):
        folder_path = filedialog.askdirectory(title="Select a Folder")
        if folder_path:
            self.entry.delete(0, tk.END)
            self.entry.insert(0, folder_path)

    def get(self):
        return self.entry.get()
