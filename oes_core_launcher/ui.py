import threading
import tkinter as tk
from tkinter import messagebox, ttk
from pathlib import Path

from PIL import Image, ImageTk
import pystray

from .config import local_data_dir
from .controller import CoreController
from .credentials import WindowsCredentialStore
from .instance import SingleInstance
from .launch import launch_is_ready, reduced_motion_enabled
from .renderer_process import RENDERER_BUILD_COMMAND, NativeEyeballManager
from .telemetry import (TAB_METRICS, TelemetryStore, console_view, copy_text,
                        format_diagnostics, format_tab)
from oes_core_renderer.tuning import default_paths


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
        self._build_eyeball_controls()
        self.activity = self._build_event_tree(self.tabs['Activity'])
        self.audit = self._build_event_tree(self.tabs['Audit'])
        controls = tk.Frame(self.root)
        controls.pack(pady=5)
        tk.Button(controls, text='Restart OES Core', command=self.restart).pack(side='left', padx=4)
        tk.Button(controls, text='Stop OES Core', command=self.stop).pack(side='left', padx=4)
        self.controller = CoreController(secret_store=WindowsCredentialStore(),
                                         callback=self.on_status,
                                         telemetry_store=self.telemetry)
        _control, diagnostics = default_paths()
        self.native_eyeball = NativeEyeballManager(
            Path(__file__).resolve().parents[1], diagnostics)
        image = Image.open(icon_path)
        self.tray = pystray.Icon('oes-core', image, 'OES Core', pystray.Menu(
            pystray.MenuItem('Open Status', self.show, default=True),
            pystray.MenuItem('Restart OES Core', self.restart),
            pystray.MenuItem('Stop OES Core', self.stop),
            pystray.MenuItem('Exit', self.exit)))
        self.instance = SingleInstance(local_data_dir() / 'launcher.lock')
        self._build_launch_treatment(icon_path.parent)
        self.root.after(1000, self._refresh_loop)

    def _build_launch_treatment(self, asset_dir):
        background = '#061426'
        self._launch_reduced_motion = reduced_motion_enabled()
        self._launch_interacted = False
        self._launch_jobs = []
        self._launch_images = {}
        for name, filename in (
                ('base', 'eyeball-base-launch.png'),
                ('baseball', 'eyeball-baseball-launch.png')):
            image = Image.open(asset_dir / filename).convert('RGBA')
            image.thumbnail((220, 220), Image.Resampling.LANCZOS)
            self._launch_images[name] = ImageTk.PhotoImage(image)
        self.launch_frame = tk.Frame(self.root, bg=background)
        self.launch_frame.place(x=0, y=0, relwidth=1, relheight=1)
        content = tk.Frame(self.launch_frame, bg=background)
        content.place(relx=.5, rely=.47, anchor='center')
        self.launch_mark = tk.Label(
            content, image=self._launch_images['base'], bg=background, borderwidth=0
        )
        self.launch_mark.pack()
        tk.Label(
            content, text='EYEBALL', bg=background, fg='#e7f7ff',
            font=('Segoe UI', 20, 'bold')
        ).pack(pady=(2, 0))
        self.launch_status = tk.Label(
            content, text='Starting OES Core…', bg=background, fg='#7dd3fc',
            font=('Segoe UI', 10)
        )
        self.launch_status.pack(pady=(4, 0))
        if not self._launch_reduced_motion:
            self._launch_jobs.append(self.root.after(120, self._show_launch_interaction))
            self._launch_jobs.append(self.root.after(360, self._settle_launch_mark))

    def _show_launch_interaction(self):
        if self.launch_frame.winfo_exists():
            self._launch_interacted = True
            self.launch_mark.config(image=self._launch_images['baseball'])

    def _settle_launch_mark(self):
        if self.launch_frame.winfo_exists():
            self.launch_mark.config(image=self._launch_images['base'])

    def _finish_launch_treatment(self):
        if not self.launch_frame.winfo_exists():
            return
        for job in self._launch_jobs:
            try:
                self.root.after_cancel(job)
            except Exception:
                pass
        self._launch_jobs.clear()
        if self._launch_reduced_motion or not self._launch_interacted:
            self.launch_frame.destroy()
            return
        self._settle_launch_mark()
        self.root.after(100, self.launch_frame.destroy)

    def _build_metrics_tab(self, name, rows):
        frame = self.tabs[name]
        for index, (key, title) in enumerate(rows):
            ttk.Label(frame, text=title).grid(row=index, column=0, sticky='w', padx=14, pady=4)
            label = ttk.Label(frame, text='—')
            label.grid(row=index, column=1, sticky='w', padx=14, pady=4)
            self.metric_labels[key] = label
        frame.columnconfigure(1, weight=1)

    def _build_eyeball_controls(self):
        controls = ttk.LabelFrame(self.tabs['Eyeball'], text='Native 3D Eyeball', padding=10)
        controls.grid(row=len(TAB_METRICS['Eyeball']), column=0, columnspan=2,
                      sticky='ew', padx=12, pady=10)
        ttk.Button(controls, text='Open 3D Eyeball', command=self.open_3d_eyeball).pack(
            side='left', padx=4)
        ttk.Button(controls, text='Open 3D Tuner', command=self.open_3d_tuner).pack(
            side='left', padx=4)
        ttk.Button(controls, text='Close Eyeball', command=self.close_3d_eyeball).pack(
            side='left', padx=4)

    def _native_result(self, result):
        success, reason = result
        if success:
            return
        messages = {
            'already_running': 'The repaired 3D Eyeball is already open.',
            'tuner_already_running': 'The 3D Tuner is already open.',
            'missing_executable': (
                'The repaired 3D Eyeball has not been built in this OES Core checkout.\n\n'
                'Build it from the repository with:\n' + RENDERER_BUILD_COMMAND),
            'launch_failed': 'The repaired 3D Eyeball could not be opened.',
            'tuner_launch_failed': 'The 3D Tuner could not be opened.',
        }
        messagebox.showinfo('OES Core', messages.get(reason, 'The 3D Eyeball is unavailable.'))

    def open_3d_eyeball(self):
        self._native_result(self.native_eyeball.open_renderer())

    def open_3d_tuner(self):
        self._native_result(self.native_eyeball.open_tuner())

    def close_3d_eyeball(self):
        self.native_eyeball.close_all()

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
        if launch_is_ready(status):
            self._finish_launch_treatment()

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
            self.native_eyeball.close_all()
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
