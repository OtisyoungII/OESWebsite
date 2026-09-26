"""Native Windows credential provisioning for OES Core."""
import re
import tkinter as tk
from pathlib import Path
from tkinter import messagebox

from .config import LauncherConfig
from .credentials import WindowsCredentialStore


SUCCESS = 'OES Core credential saved.'
MISMATCH = 'The shared keys do not match. Nothing was saved.'
INVALID = 'Enter a 64-character lowercase hexadecimal shared key.'
SAVE_FAILED = 'The credential could not be saved.'


class ProvisioningSession:
    """Validate and store one credential without retaining the submitted value."""
    def __init__(self, config, store):
        self.config = config
        self.store = store

    def save(self, secret, confirmation):
        try:
            if secret != confirmation:
                return False, MISMATCH
            if not re.fullmatch(r'[0-9a-f]{64}', secret or ''):
                return False, INVALID
            try:
                self.store.write(secret, self.config.worker_id)
            except Exception:
                return False, SAVE_FAILED
            return True, SUCCESS
        finally:
            secret = None
            confirmation = None

    def cancel(self):
        return False


class ProvisioningDialog:
    def __init__(self, root, session):
        self.root = root
        self.session = session
        self.secret = tk.StringVar(root)
        self.confirmation = tk.StringVar(root)

        root.title('OES Core Provisioning')
        root.resizable(False, False)
        root.protocol('WM_DELETE_WINDOW', self.cancel)
        icon = Path(__file__).resolve().parent / 'assets' / 'oes-eyeball.ico'
        if icon.is_file():
            try:
                root.iconbitmap(default=str(icon))
            except tk.TclError:
                pass

        frame = tk.Frame(root, padx=18, pady=16)
        frame.grid(row=0, column=0)
        tk.Label(frame, text='Worker Shared Key', anchor='w').grid(
            row=0, column=0, columnspan=2, sticky='ew')
        first = tk.Entry(frame, textvariable=self.secret, show='*', width=52)
        first.grid(row=1, column=0, columnspan=2, pady=(3, 12), sticky='ew')
        tk.Label(frame, text='Confirm Worker Shared Key', anchor='w').grid(
            row=2, column=0, columnspan=2, sticky='ew')
        tk.Entry(frame, textvariable=self.confirmation, show='*', width=52).grid(
            row=3, column=0, columnspan=2, pady=(3, 16), sticky='ew')
        tk.Button(frame, text='Save', width=12, command=self.save).grid(
            row=4, column=0, padx=(0, 6), sticky='e')
        tk.Button(frame, text='Cancel', width=12, command=self.cancel).grid(
            row=4, column=1, padx=(6, 0), sticky='w')
        first.focus_set()

    def _clear(self):
        self.secret.set('')
        self.confirmation.set('')

    def save(self):
        secret = self.secret.get()
        confirmation = self.confirmation.get()
        try:
            saved, message = self.session.save(secret, confirmation)
        finally:
            secret = None
            confirmation = None
            self._clear()
        if saved:
            messagebox.showinfo('OES Core', message, parent=self.root)
            self.root.destroy()
        else:
            messagebox.showerror('OES Core', message, parent=self.root)

    def cancel(self):
        self.session.cancel()
        self._clear()
        self.root.destroy()


def main():
    root = tk.Tk()
    try:
        config = LauncherConfig.load()
        session = ProvisioningSession(config, WindowsCredentialStore())
    except Exception:
        messagebox.showerror('OES Core', 'OES Core provisioning is unavailable.', parent=root)
        root.destroy()
        return
    ProvisioningDialog(root, session)
    root.mainloop()


if __name__ == '__main__':
    main()
