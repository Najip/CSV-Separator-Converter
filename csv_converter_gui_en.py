import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd
import os
from pathlib import Path
import subprocess
import platform

class ConfirmDialog(tk.Toplevel):
    def __init__(self, parent, title, message, callback):
        super().__init__(parent)
        self.title(title)
        self.message = message
        self.callback = callback
        self.parent = parent
        self.initialize_dialog()

    def initialize_dialog(self):
        self.transient(self.parent)
        self.grab_set()
        self.iconbitmap(self.get_icon_path())

        tk.Label(self, text=self.message).pack(padx=50, pady=20)
        
        btn_frame = tk.Frame(self)
        btn_frame.pack(pady=10)

        tk.Button(btn_frame, text="Replace", command=lambda: self.user_choice("replace")).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Cancel", command=lambda: self.user_choice("cancel")).pack(side=tk.LEFT, padx=10)
        tk.Button(btn_frame, text="Save with Number", command=lambda: self.user_choice("rename")).pack(side=tk.LEFT, padx=10)

        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.geometry("+%d+%d" % (self.parent.winfo_rootx()+50, self.parent.winfo_rooty()+50))

    def user_choice(self, choice):
        self.callback(choice)
        self.destroy()

    def on_close(self):
        self.destroy()

    @staticmethod
    def get_icon_path():
        return os.path.join(os.path.dirname(__file__), 'icon.ico')

class CSVSeparatorConverterApp:
    def __init__(self, root):
        self.root = root
        self.initialize_gui()
        self.input_file_path = ''
        self.output_directory = ''
        self.use_custom_location = False
        self.detected_separator = None
        self.output_file_path = ''

    def initialize_gui(self):
        self.root.title('CSV Separator Converter')
        self.root.iconbitmap(self.get_icon_path())

        tk.Label(self.root, text='Select File:').grid(row=0, column=0, sticky='w', pady=2)
        self.file_entry = tk.Entry(self.root, width=70)
        self.file_entry.grid(row=0, column=1, padx=5, pady=2, columnspan=3)
        tk.Button(self.root, text='Browse', command=self.browse_file).grid(row=0, column=4, padx=5, pady=2)

        self.toggle_location_button = tk.Checkbutton(self.root, text='Choose Different Location', command=self.toggle_location)
        self.toggle_location_button.grid(row=1, column=0, columnspan=5, sticky='w', pady=2)

        tk.Label(self.root, text='Select Destination Location:').grid(row=2, column=0, sticky='w', pady=2)
        self.output_entry = tk.Entry(self.root, width=70, state='disabled')
        self.output_entry.grid(row=2, column=1, padx=5, pady=2, columnspan=3)
        self.browse_output_button = tk.Button(self.root, text='Browse', command=self.browse_output, state='disabled')
        self.browse_output_button.grid(row=2, column=4, padx=5, pady=2)

        self.convert_button = tk.Button(self.root, text='Convert', command=self.convert_file, state='disabled')
        self.convert_button.grid(row=3, column=0, columnspan=5, padx=5, pady=10)

        self.notification_frame = tk.Frame(self.root)
        self.notification_frame.grid(row=4, column=0, columnspan=5, sticky='w')

        self.notification_label_text = tk.Label(self.notification_frame, text='')
        self.notification_label_text.pack(side=tk.LEFT)

        self.notification_label_link = tk.Label(self.notification_frame, text='', fg="blue", cursor="hand2")
        self.notification_label_link.pack(side=tk.LEFT)
        self.notification_label_link.bind("<Button-1>", self.on_link_click)

        self.separator_notification_label = tk.Label(self.root, text='', fg="red")
        self.separator_notification_label.grid(row=5, column=0, columnspan=5, sticky='w')

    def browse_file(self):
        file_path = filedialog.askopenfilename(filetypes=[('CSV Files', '*.csv')])
        if file_path:
            self.input_file_path = self.normalize_path(file_path)
            self.file_entry.delete(0, tk.END)
            self.file_entry.insert(0, self.input_file_path)
            self.detect_separator()
            self.convert_button['state'] = 'normal'

    def browse_output(self):
        directory = filedialog.askdirectory()
        if directory:
            self.output_directory = self.normalize_path(directory)
            self.output_entry.delete(0, tk.END)
            self.output_entry.insert(0, self.output_directory)

    def toggle_location(self):
        self.use_custom_location = not self.use_custom_location
        if self.use_custom_location:
            self.output_entry['state'] = 'normal'
            self.browse_output_button['state'] = 'normal'
        else:
            self.output_entry['state'] = 'disabled'
            self.browse_output_button['state'] = 'disabled'
            self.output_directory = ''

    def detect_separator(self):
        with open(self.input_file_path, 'r', encoding='utf-8') as file:
            first_line = file.readline()
            if ',' in first_line:
                self.detected_separator = ','
                self.separator_notification_label.config(text='"," detected. Press "Convert" to convert to ";".')
            elif ';' in first_line:
                self.detected_separator = ';'
                self.separator_notification_label.config(text='";" detected. Press "Convert" to convert to ",".')

    def convert_file(self):
        if not self.input_file_path:
            self.notification_label_text.config(text='Warning: Please select a CSV file first!')
            return

        output_file_name = self.prepare_output_filename()
        self.output_file_path = os.path.join(self.output_directory if self.use_custom_location else os.path.dirname(self.input_file_path), output_file_name)
        
        if os.path.exists(self.output_file_path):
            message = f"The file \"{output_file_name}\" already exists. Are you sure you want to replace the existing file?"
            ConfirmDialog(self.root, "Confirmation", message, self.handle_user_choice)
        else:
            self.write_to_csv(output_file_name)

    def handle_user_choice(self, choice):
        if choice == "replace":
            self.write_to_csv(self.output_file_path)
        elif choice == "rename":
            self.output_file_path = self.get_unique_filename(self.output_file_path)
            self.write_to_csv(self.output_file_path)

    def write_to_csv(self, output_file_name):
        try:
            df = pd.read_csv(self.input_file_path, sep=self.detected_separator)
            new_separator = ';' if self.detected_separator == ',' else ','
            df.to_csv(self.output_file_path, index=False, sep=new_separator)

            self.output_file_path = self.normalize_path(self.output_file_path)
            self.notification_label_text.config(text='Conversion Successful! Output file saved at: ')
            self.notification_label_link.config(text=f'{self.output_file_path}')
            self.open_file_location(self.output_file_path)
        except Exception as e:
            messagebox.showerror("Error", "Replacement failed! File is being used by another application.")

    def get_unique_filename(self, file_path):
        base, extension = os.path.splitext(file_path)
        counter = 1
        while os.path.exists(f"{base}_{counter}{extension}"):
            counter += 1
        return f"{base}_{counter}{extension}"

    def prepare_output_filename(self):
        input_filename = Path(self.input_file_path).stem
        output_extension = Path(self.input_file_path).suffix
        base_filename = input_filename.replace('-semicolon', '').replace('-comma', '')
        if self.detected_separator == ',':
            new_suffix = '-semicolon'
        else:
            new_suffix = '-comma'
        return f"{base_filename}{new_suffix}{output_extension}"

    def open_file_location(self, file_path):
        normalized_path = os.path.normpath(file_path)
        if platform.system() == "Windows":
            subprocess.Popen(f'explorer /select,"{normalized_path}"', shell=True)
        else:
            subprocess.Popen(['open', '-R', normalized_path], shell=False)

    def on_link_click(self, event=None):
        if self.output_file_path:
            self.open_file_location(self.output_file_path)

    @staticmethod
    def normalize_path(path):
        if platform.system() == "Windows":
            return path.replace('/', '\\')
        else:
            return path.replace('\\', '/')

    @staticmethod
    def get_icon_path():
        return os.path.join(os.path.dirname(__file__), 'icon.ico')

if __name__ == '__main__':
    root = tk.Tk()
    app = CSVSeparatorConverterApp(root)
    root.mainloop()
