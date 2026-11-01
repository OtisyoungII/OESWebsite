"""Small developer-only control panel for the native OES Eyeball renderer."""
from __future__ import annotations

import argparse
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .tuning import (CANONICAL_PARAMETERS, PARAMETER_LIMITS, default_paths,
                     load_preset, read_diagnostics, read_parameters, save_preset,
                     write_parameters)


LABELS = {
    'scale': 'Overall scale', 'x': 'X position', 'y': 'Y position',
    'rotation': 'Rotation', 'opacity': 'Opacity',
    'glow_intensity': 'Glow intensity', 'glow_radius': 'Glow radius',
    'brightness': 'Brightness', 'exposure': 'Exposure',
    'lighting_intensity': 'Lighting intensity', 'depth': 'Depth',
    'perspective_x': 'Perspective X', 'perspective_y': 'Perspective Y',
    'width': 'Window width', 'height': 'Window height',
}


class TuningPanel:
    def __init__(self, root, control_path, diagnostics_path):
        self.root = root
        self.control_path = Path(control_path)
        self.diagnostics_path = Path(diagnostics_path)
        self._write_pending = None
        self.variables = {}
        try:
            initial_parameters = read_parameters(self.control_path)
        except ValueError:
            initial_parameters = dict(CANONICAL_PARAMETERS)
        root.title('OES Eyeball — Developer Tuning')
        root.geometry('700x760')
        root.minsize(620, 650)
        icon = Path(__file__).resolve().parents[1] / 'oes_core_launcher' / 'assets' / 'oes-eyeball.ico'
        if icon.is_file():
            root.iconbitmap(default=str(icon))

        title = ttk.Label(root, text='OES EYEBALL — DEVELOPER TUNING',
                          font=('Segoe UI', 15, 'bold'))
        title.pack(pady=(12, 4))
        ttk.Label(root, text='Canonical identity is read-only; controls publish local parameters only.').pack()

        controls = ttk.Frame(root)
        controls.pack(fill='both', expand=True, padx=14, pady=10)
        for row, (name, default) in enumerate(initial_parameters.items()):
            ttk.Label(controls, text=LABELS[name]).grid(row=row, column=0, sticky='w', padx=5)
            variable = tk.DoubleVar(value=default)
            self.variables[name] = variable
            low, high = PARAMETER_LIMITS[name]
            resolution = 1 if name in ('width', 'height') else 0.01
            scale = tk.Scale(controls, variable=variable, from_=low, to=high,
                             resolution=resolution, orient='horizontal', length=350,
                             command=lambda _value, key=name: self._schedule_write(key))
            scale.grid(row=row, column=1, sticky='ew')
            value = ttk.Label(controls, width=9, anchor='e')
            value.grid(row=row, column=2, padx=5)
            variable.trace_add('write', lambda *_args, key=name, label=value:
                               label.config(text=self._display_value(key)))
            value.config(text=self._display_value(name))
        controls.columnconfigure(1, weight=1)

        actions = ttk.Frame(root)
        actions.pack(fill='x', padx=14, pady=4)
        ttk.Button(actions, text='Reset to Canonical', command=self.reset).pack(side='left', padx=4)
        ttk.Button(actions, text='Save Preset', command=self.save).pack(side='left', padx=4)
        ttk.Button(actions, text='Load Preset', command=self.load).pack(side='left', padx=4)

        self.diagnostics = ttk.LabelFrame(root, text='Renderer diagnostics')
        self.diagnostics.pack(fill='x', padx=14, pady=(6, 14))
        self.diagnostic_labels = {}
        for row, (key, title_text) in enumerate((
                ('adapter_name', 'Selected GPU'), ('device_type', 'Device'),
                ('feature_level', 'D3D feature level'), ('fps', 'Renderer FPS'),
                ('dimensions', 'Renderer dimensions'))):
            ttk.Label(self.diagnostics, text=title_text).grid(row=row, column=0, sticky='w', padx=8, pady=2)
            label = ttk.Label(self.diagnostics, text='Not available')
            label.grid(row=row, column=1, sticky='w', padx=8, pady=2)
            self.diagnostic_labels[key] = label

        self.status = ttk.Label(root, text='')
        self.status.pack(fill='x', padx=18, pady=(0, 8))
        self._write_now()
        self._refresh_diagnostics()

    def _display_value(self, name):
        value = self.variables[name].get()
        return str(int(round(value))) if name in ('width', 'height') else f'{value:.2f}'

    def _values(self):
        return {name: (int(round(variable.get())) if name in ('width', 'height')
                       else variable.get()) for name, variable in self.variables.items()}

    def _schedule_write(self, _name=None):
        if self._write_pending is not None:
            self.root.after_cancel(self._write_pending)
        self._write_pending = self.root.after(40, self._write_now)

    def _write_now(self):
        self._write_pending = None
        try:
            write_parameters(self.control_path, self._values())
            self.status.config(text='Live parameters published locally.')
        except (OSError, ValueError):
            self.status.config(text='Unable to publish renderer parameters.')

    def _apply(self, values):
        for name, value in values.items():
            self.variables[name].set(value)
        self._write_now()

    def reset(self):
        self._apply(CANONICAL_PARAMETERS)

    def save(self):
        path = filedialog.asksaveasfilename(title='Save OES Eyeball preset',
                                            defaultextension='.json',
                                            filetypes=(('OES renderer preset', '*.json'),))
        if not path:
            return
        try:
            save_preset(path, self._values())
            self.status.config(text='Preset saved. Canonical artwork was not modified.')
        except (OSError, ValueError):
            messagebox.showerror('OES Eyeball', 'The preset could not be saved.')

    def load(self):
        path = filedialog.askopenfilename(title='Load OES Eyeball preset',
                                          filetypes=(('OES renderer preset', '*.json'),))
        if not path:
            return
        try:
            self._apply(load_preset(path))
        except (OSError, ValueError):
            messagebox.showerror('OES Eyeball', 'The preset is invalid or unavailable.')

    def _refresh_diagnostics(self):
        value = read_diagnostics(self.diagnostics_path)
        if value:
            self.diagnostic_labels['adapter_name'].config(text=value.get('adapter_name', 'Unavailable'))
            device = value.get('device_type', 'unavailable')
            self.diagnostic_labels['device_type'].config(
                text='Hardware' if device == 'hardware' else ('WARP' if device == 'warp' else 'Unavailable'))
            self.diagnostic_labels['feature_level'].config(text=value.get('feature_level', 'Unavailable'))
            fps = value.get('fps')
            self.diagnostic_labels['fps'].config(text=f'{fps:.1f}' if isinstance(fps, (int, float)) else 'Unavailable')
            width, height = value.get('width'), value.get('height')
            dimensions = f'{width} × {height}' if isinstance(width, int) and isinstance(height, int) else 'Unavailable'
            self.diagnostic_labels['dimensions'].config(text=dimensions)
        self.root.after(1000, self._refresh_diagnostics)


def main(argv=None):
    control_default, diagnostics_default = default_paths()
    parser = argparse.ArgumentParser(description='OES Eyeball developer tuning panel')
    parser.add_argument('--control', type=Path, default=control_default)
    parser.add_argument('--diagnostics', type=Path, default=diagnostics_default)
    args = parser.parse_args(argv)
    root = tk.Tk()
    TuningPanel(root, args.control, args.diagnostics)
    root.mainloop()


if __name__ == '__main__':
    main()
