import tkinter as tk
from tkinter import ttk, filedialog


class TTKFormLayoutHelper:
    def __init__(self, frame, vertical_spacing=5):
        self.row_idx = 0
        self.frame = frame
        self.vertical_spacing = vertical_spacing

    def add_row(self, label_text, widget, widget_grid_args=None):
        if widget is None:
            widget = ttk.Entry(self.frame)

        if widget_grid_args is None:
            widget_grid_args = {}

        label = ttk.Label(self.frame, text=label_text)
        label.grid(row=self.row_idx, column=0, sticky="w")

        widget_grid_args = {
            "pady": self.vertical_spacing,
            "sticky": "ew",
            **widget_grid_args
        }

        widget.grid(row=self.row_idx, column=1, padx=10, **widget_grid_args)

        self.row_idx += 1
        return widget

    def add_spacer_row(self):
        return self.add_row("")

    def create_labeled_entry(self, parent, label_text, *args, **kwargs):
        """Helper function to create a label and entry widget in a given parent."""
        entry = ttk.Entry(parent, *args, **kwargs)
        return self.add_row(label_text, entry)

        return entry


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


class WrappedLabel(ttk.Label):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.bind('<Configure>', lambda _: self.config(wraplength=self.winfo_width()))


class ConsoleText(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        super().__init__(parent)
        self._text = tk.Text(self, *args, **kwargs)

        self.scrollbar_y = tk.Scrollbar(self)
        self.scrollbar_x = tk.Scrollbar(self, orient="horizontal")

        self._text.config(yscrollcommand=self.scrollbar_y.set, xscrollcommand=self.scrollbar_x.set)
        self.scrollbar_y.config(command=self._text.yview)
        self.scrollbar_x.config(command=self._text.xview)

        self.scrollbar_y.pack(side="right", fill="y")
        self.scrollbar_x.pack(side="bottom", fill="x")
        self._text.pack(side="left", fill="both", expand=True)

        self._text.tag_configure("ERROR", foreground="red")
        self._text.tag_configure("WARNING", foreground="orange")

    def __getattr__(self, name):
        return getattr(self._text, name)

    def configure(self, **kwargs):
        self._text.configure(**kwargs)
