from pathlib import Path


def button_shadow(window):
    """Keep the Windows system color, using a portable shade elsewhere."""
    return ("SystemButtonShadow" if window.tk.call("tk", "windowingsystem") == "win32"
            else "#b8b8b8")


def set_window_icon(window, icon_path):
    """Apply Windows ICO icons only on the Tk backend that supports them."""
    if icon_path and window.tk.call("tk", "windowingsystem") == "win32":
        window.iconbitmap(str(Path(__file__).parent / icon_path))
