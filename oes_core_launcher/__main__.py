def main():
    try:
        from .ui import LauncherUI
        LauncherUI().run()
    except ImportError:
        import ctypes
        ctypes.windll.user32.MessageBoxW(
            0, 'Install launcher dependencies from launcher-requirements.txt.',
            'OES Core — Needs Attention', 0x10)


if __name__ == '__main__':
    main()
