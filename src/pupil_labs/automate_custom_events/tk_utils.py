import tkinter as tk
from tkinter import ttk, filedialog


class TTKFormLayoutHelper:
    def __init__(self, root):
        self.row_idx = 0
        self.root = root

    def add_heading_2(self, text, heading_font):
        # Use tk.Text to control line spacing
        text_widget = tk.Text(self.root, height=3, wrap="word", borderwidth=0, font=heading_font)
        text_widget.insert("1.0", text)
        # text_widget.tag_configure("center", justify='full')  # Optional centering
        text_widget.tag_add("center", "1.0", "end")

        # Adjust line spacing with spacing2 (spacing between lines)
        text_widget.configure(spacing2=5, state="disabled")  # spacing2 adds space between lines
        text_widget.grid(row=self.row_idx, column=0, columnspan=2, sticky="ew", pady=10)

        self.row_idx += 2

    def add_heading(self, text):
        label = ttk.Label(self.root, text=text, wraplength=500, style="Heading.TLabel")
        label.grid(row=self.row_idx, column=0, columnspan=2, sticky="w", pady=10)

        self.row_idx += 1

    def add_row(self, text, widget=None, widget_grid_args=None):
        # Get the background and foreground colors from the ttk Entry widget style
        if widget is None:
            widget = ttk.Entry(self.root)

        if widget_grid_args is None:
            widget_grid_args = {}

        label = ttk.Label(self.root, text=text)
        label.grid(row=self.row_idx, column=0, sticky="w")
        # widget.grid(row=self.row_idx, column=1, sticky="ew", padx=10, **widget_grid_args)
        widget.grid(row=self.row_idx, column=1, padx=10, **widget_grid_args)

        self.row_idx += 1
        return widget

    def add_spacer_row(self):
        label = ttk.Label(self.root)
        label.grid(row=self.row_idx, column=0, sticky="w")

        self.row_idx += 1

    # Function to create a labeled entry
    def create_labeled_entry(self, parent, label_text, row, show=None, default_value=None):
        """Helper function to create a label and entry widget in a given parent."""
        label = ttk.Label(parent, text=label_text, style="Heading.TLabel")
        label.grid(row=row, column=0, sticky='w', padx=5, pady=5)
        entry_kwargs = {'style': 'Custom.TEntry'}
        if show:
            entry_kwargs['show'] = show

        entry = ttk.Entry(parent, show=show) if show else ttk.Entry(parent)
        entry.grid(row=row, column=1, sticky='ew', padx=5, pady=5)

        if default_value:
            entry.insert(0, default_value)

        return entry

    # Function to create a labeled folder selector
    def create_labeled_folder_selector(self, parent, label_text, row, default_path):
        """Helper function to create a label and folder selector widget in a given parent."""
        label = ttk.Label(parent, text=label_text, style="Heading.TLabel")
        label.grid(row=row, column=0, sticky='w', padx=5, pady=5)

        folder_selector = FolderSelector(parent, default_path)
        folder_selector.grid(row=row, column=1, sticky='ew', padx=5, pady=5)

        return folder_selector


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
