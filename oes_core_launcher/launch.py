"""Platform-neutral launch-state policy for the Eyeball desktop application."""
import sys


def reduced_motion_enabled(platform=None, animation_query=None):
    platform = sys.platform if platform is None else platform
    if platform != 'win32':
        return False
    if animation_query is not None:
        return not animation_query()
    try:
        import ctypes
        enabled = ctypes.c_int()
        # SPI_GETCLIENTAREAANIMATION follows the Windows "Show animations" setting.
        if ctypes.windll.user32.SystemParametersInfoW(
                0x1042, 0, ctypes.byref(enabled), 0):
            return not bool(enabled.value)
    except Exception:
        pass
    return False


def launch_is_ready(status):
    return status.core in ('Online', 'Needs Attention')
