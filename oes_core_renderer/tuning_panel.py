"""Developer visual workspace for tuning the real native OES Eyeball renderer."""
from __future__ import annotations

import argparse
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .preview_host import NativePreviewHost
from .tuning import (CANONICAL_PARAMETERS, PARAMETER_LIMITS, default_paths,
                     load_preset, read_diagnostics, read_parameters, save_preset,
                     write_parameters)


GROUPS = (
    ('Object transform', ('scale', 'x', 'y', 'z',
                          'rotation_x', 'rotation_y', 'rotation_z')),
    ('Camera & lighting', ('camera_fov', 'camera_z', 'brightness',
                           'exposure', 'lighting_intensity')),
    ('Face geometry', ('iris_scale', 'iris_depth', 'pupil_scale', 'pupil_depth',
                       'logo_scale', 'logo_depth')),
    ('Shell & energy', ('glass_intensity', 'rim_intensity',
                        'orbit_intensity', 'particle_intensity')),
    ('Surface', ('width', 'height')),
)

LABELS = {
    'scale': 'Scale', 'x': 'X position', 'y': 'Y position', 'z': 'Z position',
    'rotation_x': 'Rotation X', 'rotation_y': 'Rotation Y',
    'rotation_z': 'Rotation Z',
    'brightness': 'Brightness', 'exposure': 'Exposure',
    'lighting_intensity': 'Lighting', 'camera_fov': 'Camera FOV',
    'camera_z': 'Camera Z', 'iris_scale': 'Iris scale',
    'iris_depth': 'Iris depth', 'pupil_scale': 'Pupil scale',
    'pupil_depth': 'Pupil depth', 'glass_intensity': 'Glass',
    'rim_intensity': 'Rim', 'orbit_intensity': 'Orbits',
    'particle_intensity': 'Particles', 'logo_scale': 'Logo scale',
    'logo_depth': 'Logo depth',
    'width': 'Width', 'height': 'Height',
}


class TuningPanel:
    def __init__(self, root, control_path, diagnostics_path, preview=None):
        self.root = root
        self.control_path = Path(control_path)
        self.diagnostics_path = Path(diagnostics_path)
        self.preview = preview or NativePreviewHost()
        self._write_pending = None
        self._suspend_writes = False
        self._canonical_hold = None
        self.variables = {}
        try:
            initial_parameters = read_parameters(self.control_path)
        except ValueError:
            initial_parameters = dict(CANONICAL_PARAMETERS)

        root.title('OES Eyeball — Native Visual Tuner')
        root.geometry('1260x850')
        root.minsize(1080, 720)
        root.protocol('WM_DELETE_WINDOW', self.close)
        icon = Path(__file__).resolve().parents[1] / 'oes_core_launcher' / 'assets' / 'oes-eyeball.ico'
        if icon.is_file():
            root.iconbitmap(default=str(icon))

        header = ttk.Frame(root, padding=(16, 10))
        header.pack(fill='x')
        ttk.Label(header, text='OES EYEBALL — NATIVE VISUAL TUNER',
                  font=('Segoe UI', 17, 'bold')).pack(side='left')
        ttk.Label(header, text='Real D3D11 renderer · canonical identity remains read-only').pack(
            side='right', pady=(7, 0))

        workspace = ttk.Panedwindow(root, orient='horizontal')
        workspace.pack(fill='both', expand=True, padx=14, pady=(0, 8))

        preview_card = ttk.LabelFrame(workspace, text='Live native preview', padding=10)
        controls_card = ttk.Frame(workspace)
        workspace.add(preview_card, weight=3)
        workspace.add(controls_card, weight=2)

        self.preview_surface = tk.Frame(preview_card, bg='#101827', width=650, height=650,
                                        highlightthickness=1, highlightbackground='#334155')
        self.preview_surface.pack(fill='both', expand=True)
        self.preview_surface.pack_propagate(False)
        self.preview_message = tk.Label(
            self.preview_surface,
            text='Waiting for the native renderer…\nLaunch oes-eyeball-renderer.exe separately.',
            bg='#101827', fg='#cbd5e1', font=('Segoe UI', 12), justify='center')
        self.preview_message.place(relx=.5, rely=.5, anchor='center')
        self.preview_surface.bind('<Configure>', self._preview_resized)

        control_canvas = tk.Canvas(controls_card, highlightthickness=0, width=470)
        scrollbar = ttk.Scrollbar(controls_card, orient='vertical', command=control_canvas.yview)
        self.control_body = ttk.Frame(control_canvas)
        self.control_body.bind('<Configure>',
                               lambda _event: control_canvas.configure(
                                   scrollregion=control_canvas.bbox('all')))
        control_canvas.create_window((0, 0), window=self.control_body, anchor='nw', width=445)
        control_canvas.configure(yscrollcommand=scrollbar.set)
        control_canvas.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')

        for group_name, names in GROUPS:
            group = ttk.LabelFrame(self.control_body, text=group_name, padding=(8, 5))
            group.pack(fill='x', padx=5, pady=4)
            group.columnconfigure(1, weight=1)
            for row, name in enumerate(names):
                self._build_parameter(group, row, name, initial_parameters[name])

        compare = ttk.LabelFrame(self.control_body, text='Preset & comparison', padding=8)
        compare.pack(fill='x', padx=5, pady=4)
        ttk.Button(compare, text='Reset to Canonical', command=self.reset).pack(
            side='left', padx=(0, 5))
        hold = ttk.Button(compare, text='Hold Canonical')
        hold.pack(side='left', padx=5)
        hold.bind('<ButtonPress-1>', self._hold_canonical)
        hold.bind('<ButtonRelease-1>', self._release_canonical)
        ttk.Button(compare, text='Save Preset', command=self.save).pack(side='left', padx=5)
        ttk.Button(compare, text='Load Preset', command=self.load).pack(side='left', padx=5)

        footer = ttk.Frame(root, padding=(16, 5, 16, 10))
        footer.pack(fill='x')
        self.diagnostic_text = ttk.Label(footer, text='Renderer diagnostics unavailable')
        self.diagnostic_text.pack(anchor='w')
        self.status = ttk.Label(footer, text='')
        self.status.pack(anchor='w', pady=(3, 0))

        self._write_now()
        root.after(150, self._attach_preview)
        self._refresh_diagnostics()

    def _build_parameter(self, parent, row, name, default):
        ttk.Label(parent, text=LABELS[name], width=15).grid(
            row=row, column=0, sticky='w', padx=(2, 6), pady=2)
        variable = tk.DoubleVar(value=default)
        self.variables[name] = variable
        low, high = PARAMETER_LIMITS[name]
        resolution = 1 if name in ('width', 'height') else .01
        scale = tk.Scale(parent, variable=variable, from_=low, to=high,
                         resolution=resolution, orient='horizontal', length=235,
                         showvalue=False, highlightthickness=0,
                         command=lambda _value: self._schedule_write())
        scale.grid(row=row, column=1, sticky='ew', padx=3, pady=1)
        spinbox = ttk.Spinbox(parent, textvariable=variable, from_=low, to=high,
                              increment=resolution, width=9,
                              command=self._schedule_write)
        spinbox.grid(row=row, column=2, padx=(5, 2), pady=2)
        spinbox.bind('<Return>', lambda _event: self._write_now())
        spinbox.bind('<FocusOut>', lambda _event: self._write_now())
        variable.trace_add('write', lambda *_args: self._variable_changed())

    def _variable_changed(self):
        if not self._suspend_writes:
            self._schedule_write()

    def _values(self):
        values = {}
        for name, variable in self.variables.items():
            value = variable.get()
            values[name] = int(round(value)) if name in ('width', 'height') else value
        return values

    def _schedule_write(self):
        if self._suspend_writes:
            return
        if self._write_pending is not None:
            self.root.after_cancel(self._write_pending)
        self._write_pending = self.root.after(35, self._write_now)

    def _write_now(self):
        self._write_pending = None
        try:
            write_parameters(self.control_path, self._values())
            self.status.config(text='Live parameters applied to the native renderer.')
        except (OSError, ValueError, tk.TclError):
            self.status.config(text='Enter a valid value within the displayed range.')

    def _apply(self, values):
        self._suspend_writes = True
        try:
            for name, value in values.items():
                self.variables[name].set(value)
        finally:
            self._suspend_writes = False
        self._write_now()

    def reset(self):
        self._canonical_hold = None
        self._apply(CANONICAL_PARAMETERS)
        self.status.config(text='Canonical renderer parameters restored.')

    def _hold_canonical(self, _event=None):
        if self._canonical_hold is None:
            try:
                self._canonical_hold = self._values()
                self._apply(CANONICAL_PARAMETERS)
                self.status.config(text='Showing Canonical while held; release to restore tuning.')
            except tk.TclError:
                self._canonical_hold = None

    def _release_canonical(self, _event=None):
        if self._canonical_hold is not None:
            values, self._canonical_hold = self._canonical_hold, None
            self._apply(values)
            self.status.config(text='Tuned parameters restored after canonical comparison.')

    def save(self):
        path = filedialog.asksaveasfilename(title='Save OES Eyeball preset',
                                            defaultextension='.json',
                                            filetypes=(('OES renderer preset', '*.json'),))
        if not path:
            return
        try:
            save_preset(path, self._values())
            self.status.config(text='Preset saved. Canonical artwork was not modified.')
        except (OSError, ValueError, tk.TclError):
            messagebox.showerror('OES Eyeball', 'The preset could not be saved.')

    def load(self):
        path = filedialog.askopenfilename(title='Load OES Eyeball preset',
                                          filetypes=(('OES renderer preset', '*.json'),))
        if not path:
            return
        try:
            self._apply(load_preset(path))
            self.status.config(text='Preset loaded into the native renderer.')
        except (OSError, ValueError):
            messagebox.showerror('OES Eyeball', 'The preset is invalid or unavailable.')

    def _attach_preview(self):
        if self.preview.attached:
            return
        try:
            attached = self.preview.attach(self.preview_surface.winfo_id())
        except OSError:
            attached = False
        if attached:
            self.preview_message.destroy()
            self.preview_message = None
            self.status.config(text='Native D3D11 renderer attached to the visual workspace.')
            self._place_preview()
        else:
            self.root.after(1000, self._attach_preview)

    def _preview_resized(self, _event=None):
        self._place_preview()

    def _place_preview(self, width=None, height=None):
        if not self.preview.attached:
            return
        try:
            parameters = self._values()
            self.preview.place(self.preview_surface.winfo_width(),
                               self.preview_surface.winfo_height(),
                               width or parameters['width'], height or parameters['height'])
        except (OSError, tk.TclError):
            self.status.config(text='Native preview positioning is temporarily unavailable.')

    def _refresh_diagnostics(self):
        value = read_diagnostics(self.diagnostics_path)
        if value:
            device = value.get('device_type', 'unavailable')
            device_text = 'D3D11 HW' if device == 'hardware' else ('WARP' if device == 'warp' else 'Unavailable')
            fps = value.get('fps')
            fps_text = f'{fps:.1f} FPS' if isinstance(fps, (int, float)) else 'FPS unavailable'
            width, height = value.get('width'), value.get('height')
            dimensions = f'{width}×{height}' if isinstance(width, int) and isinstance(height, int) else 'size unavailable'
            self.diagnostic_text.config(text='  |  '.join((
                str(value.get('adapter_name', 'GPU unavailable')), device_text,
                f"FL {value.get('feature_level', 'unavailable')}", fps_text,
                dimensions, str(value.get('status', 'unknown')).title())))
            self._place_preview(width, height)
        self.root.after(1000, self._refresh_diagnostics)

    def close(self):
        try:
            self.preview.detach()
        except OSError:
            pass
        self.root.destroy()


def main(argv=None):
    control_default, diagnostics_default = default_paths()
    parser = argparse.ArgumentParser(description='OES Eyeball native visual tuner')
    parser.add_argument('--control', type=Path, default=control_default)
    parser.add_argument('--diagnostics', type=Path, default=diagnostics_default)
    args = parser.parse_args(argv)
    root = tk.Tk()
    TuningPanel(root, args.control, args.diagnostics)
    root.mainloop()


if __name__ == '__main__':
    main()
