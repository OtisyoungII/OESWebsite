import threading
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path

from PIL import Image
import pystray

from .config import local_data_dir
from .controller import CoreController
from .credentials import WindowsCredentialStore
from .instance import SingleInstance
from .telemetry import (TAB_METRICS, TelemetryStore, console_view, copy_text,
                        format_diagnostics, format_tab)


def telemetry_refresh_allowed(window_state):
    return window_state not in ('withdrawn', 'iconic')


class LauncherUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title('OES Core')
        self.root.geometry('820x610')
        self.root.minsize(760, 540)
        self.root.protocol('WM_DELETE_WINDOW', self.hide)
        icon_path = Path(__file__).parent / 'assets' / 'oes-eyeball.ico'
        self.root.iconbitmap(default=str(icon_path))
        self.telemetry = None
        try:
            self.telemetry = TelemetryStore()
        except Exception:
            pass
        self.labels, self.metric_labels, self.current_view = {}, {}, None
        tk.Label(self.root, text='OES CORE', font=('Segoe UI', 20, 'bold')).pack(pady=(12, 4))
        status_bar = tk.Frame(self.root)
        status_bar.pack(fill='x', padx=20)
        for key in ('core', 'worker', 'ollama', 'relay'):
            cell = tk.Frame(status_bar)
            cell.pack(side='left', fill='x', expand=True)
            tk.Label(cell, text=key.title(), font=('Segoe UI', 9, 'bold')).pack()
            self.labels[key] = tk.Label(cell, text='Unknown')
            self.labels[key].pack()
        self.detail = tk.Label(self.root, text='', fg='#b91c1c', wraplength=350)
        self.detail.pack(padx=20, pady=4)
        selector = tk.Frame(self.root)
        selector.pack(fill='x', padx=16, pady=4)
        tk.Label(selector, text='Range').pack(side='left')
        self.range = tk.StringVar(value='today')
        range_box = ttk.Combobox(selector, textvariable=self.range, state='readonly', width=12,
                                 values=('today', '7 days', '30 days', 'all time'))
        range_box.pack(side='left', padx=6)
        range_box.bind('<<ComboboxSelected>>', lambda _: self.refresh_telemetry())
        tk.Button(selector, text='Copy Tab', command=self.copy_tab).pack(side='right', padx=4)
        tk.Button(selector, text='Copy Diagnostics',
                  command=self.copy_diagnostics).pack(side='right', padx=4)
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill='both', expand=True, padx=12, pady=4)
        self.tabs = {name: ttk.Frame(self.notebook) for name in
                     ('Overview', 'Eyeball', 'Activity', 'Health', 'Audit')}
        for name, frame in self.tabs.items():
            self.notebook.add(frame, text=name)
        for tab in ('Overview', 'Eyeball', 'Health'):
            self._build_metrics_tab(tab, TAB_METRICS[tab])
        self.activity = self._build_event_tree(self.tabs['Activity'])
        self.audit = self._build_event_tree(self.tabs['Audit'])
        controls = tk.Frame(self.root)
        controls.pack(pady=5)
        tk.Button(controls, text='Restart OES Core', command=self.restart).pack(side='left', padx=4)
        tk.Button(controls, text='Stop OES Core', command=self.stop).pack(side='left', padx=4)
        self.controller = CoreController(secret_store=WindowsCredentialStore(),
                                         callback=self.on_status,
                                         telemetry_store=self.telemetry)
        image = Image.open(icon_path)
        self.tray = pystray.Icon('oes-core', image, 'OES Core', pystray.Menu(
            pystray.MenuItem('Open Status', self.show, default=True),
            pystray.MenuItem('Restart OES Core', self.restart),
            pystray.MenuItem('Stop OES Core', self.stop),
            pystray.MenuItem('Exit', self.exit)))
        self.instance = SingleInstance(local_data_dir() / 'launcher.lock')
        self.root.after(1000, self._refresh_loop)

    def _build_metrics_tab(self, name, rows):
        frame = self.tabs[name]
        for index, (key, title) in enumerate(rows):
            ttk.Label(frame, text=title).grid(row=index, column=0, sticky='w', padx=14, pady=4)
            label = ttk.Label(frame, text='—')
            label.grid(row=index, column=1, sticky='w', padx=14, pady=4)
            self.metric_labels[key] = label
        frame.columnconfigure(1, weight=1)

    @staticmethod
    def _build_event_tree(frame):
        tree = ttk.Treeview(frame, columns=('time', 'event'), show='headings')
        tree.heading('time', text='Time')
        tree.heading('event', text='Event')
        tree.column('time', width=150, stretch=False)
        tree.column('event', width=590)
        tree.pack(fill='both', expand=True, padx=8, pady=8)
        return tree

    def _set_metric(self, key, value):
        self.metric_labels[key].config(text=str(value))

    def refresh_telemetry(self):
        if not self.telemetry:
            return
        try:
            data = self.telemetry.snapshot(self.range.get())
        except Exception:
            return
        self.current_view = console_view(data, self.controller.status)
        for key, value in self.current_view['values'].items():
            if key in self.metric_labels:
                self._set_metric(key, value)
        self._render_events(self.activity, self.current_view['Activity'])
        self._render_events(self.audit, self.current_view['Audit'])

    def _render_events(self, tree, events):
        tree.delete(*tree.get_children())
        for stamp, text in events[:100]:
            tree.insert('', 'end', values=(stamp, text))

    def _selected_tab(self):
        selected = self.notebook.select()
        return self.notebook.tab(selected, 'text') if selected else 'Overview'

    def copy_tab(self):
        if self.current_view:
            copy_text(self.root, format_tab(self.current_view, self._selected_tab()))

    def copy_diagnostics(self):
        if self.current_view:
            copy_text(self.root, format_diagnostics(self.current_view))

    def _refresh_loop(self):
        if telemetry_refresh_allowed(self.root.state()):
            self.refresh_telemetry()
        self.root.after(5000, self._refresh_loop)

    def on_status(self, status):
        self.root.after(0, lambda: self._render(status))

    def _render(self, status):
        for key in self.labels:
            self.labels[key].config(text=getattr(status, key))
        self.detail.config(text=status.detail)
        self.tray.title = f'OES Core — {status.core}'

    def show(self, *_):
        self.root.after(0, self.root.deiconify)
        self.root.after(0, self.refresh_telemetry)

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
