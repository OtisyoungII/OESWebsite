import threading
import tkinter as tk
from tkinter import messagebox
from pathlib import Path

from PIL import Image
import pystray

from .config import local_data_dir
from .controller import CoreController
from .credentials import WindowsCredentialStore
from .instance import SingleInstance


class LauncherUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('OES Core')
        self.root.geometry('410x260')
        self.root.resizable(False, False)
        self.root.protocol('WM_DELETE_WINDOW', self.hide)
        icon_path = Path(__file__).parent / 'assets' / 'oes-eyeball.ico'
        self.root.iconbitmap(default=str(icon_path))
        self.labels = {}
        tk.Label(self.root, text='OES CORE', font=('Segoe UI', 20, 'bold')).pack(pady=(18, 12))
        for key in ('core', 'worker', 'ollama', 'relay'):
            row = tk.Frame(self.root)
            row.pack(fill='x', padx=28, pady=3)
            tk.Label(row, text=key.title(), width=10, anchor='w').pack(side='left')
            self.labels[key] = tk.Label(row, text='Unknown', anchor='w')
            self.labels[key].pack(side='left', fill='x', expand=True)
        self.detail = tk.Label(self.root, text='', fg='#b91c1c', wraplength=350)
        self.detail.pack(padx=20, pady=10)
        controls = tk.Frame(self.root)
        controls.pack(pady=6)
        tk.Button(controls, text='Restart OES Core', command=self.restart).pack(side='left', padx=4)
        tk.Button(controls, text='Stop OES Core', command=self.stop).pack(side='left', padx=4)
        self.controller = CoreController(secret_store=WindowsCredentialStore(),
                                         callback=self.on_status)
        image = Image.open(icon_path)
        self.tray = pystray.Icon('oes-core', image, 'OES Core', pystray.Menu(
            pystray.MenuItem('Open Status', self.show, default=True),
            pystray.MenuItem('Restart OES Core', self.restart),
            pystray.MenuItem('Stop OES Core', self.stop),
            pystray.MenuItem('Exit', self.exit)))
        self.instance = SingleInstance(local_data_dir() / 'launcher.lock')

    def on_status(self, status):
        self.root.after(0, lambda: self._render(status))

    def _render(self, status):
        for key in self.labels:
            self.labels[key].config(text=getattr(status, key))
        self.detail.config(text=status.detail)
        self.tray.title = f'OES Core — {status.core}'

    def show(self, *_):
        self.root.after(0, self.root.deiconify)

    def hide(self):
        self.root.withdraw()

    def restart(self, *_):
        threading.Thread(target=self.controller.restart, daemon=True).start()

    def stop(self, *_):
        threading.Thread(target=self.controller.stop, daemon=True).start()

    def exit(self, *_):
        def close():
            self.controller.close()
            self.tray.stop()
            self.instance.release()
            self.root.after(0, self.root.destroy)
        threading.Thread(target=close, daemon=True).start()

    def run(self):
        if not self.instance.acquire():
            messagebox.showinfo('OES Core', 'OES Core is already running.')
            self.root.destroy()
            return
        self.tray.run_detached()
        threading.Thread(target=self.controller.start, daemon=True).start()
        self.root.mainloop()
