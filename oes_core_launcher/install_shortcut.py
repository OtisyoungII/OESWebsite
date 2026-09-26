"""Install per-user desktop and sign-in shortcuts. No credentials enter them."""
import subprocess
from pathlib import Path
from .controller import python_path, repository_root


def ps_quote(value):
    return "'" + str(value).replace("'", "''") + "'"


def shortcut_metadata(root=None):
    root = repository_root() if root is None else Path(root)
    pythonw = python_path(root).with_name('pythonw.exe')
    icon = root / 'oes_core_launcher' / 'assets' / 'oes-eyeball.ico'
    if not pythonw.is_file() or not icon.is_file():
        raise ValueError('Launcher Python or icon is missing')
    return {
        'target': str(pythonw),
        'arguments': '-m oes_core_launcher',
        'working_directory': str(root),
        'icon': str(icon) + ',0',
        'description': 'OES Core / Eyeball',
    }


def shortcut_script(root=None):
    metadata = shortcut_metadata(root)
    return (
        "$desktop=[Environment]::GetFolderPath('Desktop');"
        "$startup=[Environment]::GetFolderPath('Startup');"
        "$shell=New-Object -ComObject WScript.Shell;"
        "function Install-OesCoreShortcut($path){"
        "$link=$shell.CreateShortcut($path);"
        f"$link.TargetPath={ps_quote(metadata['target'])};"
        f"$link.Arguments={ps_quote(metadata['arguments'])};"
        f"$link.WorkingDirectory={ps_quote(metadata['working_directory'])};"
        f"$link.IconLocation={ps_quote(metadata['icon'])};"
        f"$link.Description={ps_quote(metadata['description'])};$link.Save()"
        "};"
        "Install-OesCoreShortcut (Join-Path $desktop 'OES Core.lnk');"
        "Install-OesCoreShortcut (Join-Path $startup 'OES Core.lnk')"
    )


def main():
    subprocess.run(['powershell.exe', '-NoProfile', '-NonInteractive', '-Command',
                    shortcut_script()], check=True)
    print('OES Core desktop and sign-in shortcuts installed for the current user.')


if __name__ == '__main__':
    main()
