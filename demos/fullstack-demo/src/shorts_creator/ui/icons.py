"""Inline SVG icons used across the UI."""

from markupsafe import Markup


def icon_svg(path, view_box="0 0 24 24", size=5):
    cls = f"w-{size} h-{size}"
    return Markup(
        f'<svg class="{cls}" viewBox="{view_box}" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="{path}"/></svg>'
    )


def folder():
    return icon_svg("M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z")


def plus():
    return icon_svg("M12 5v14m-7-7h14")


def dashboard():
    return icon_svg("M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z")


def lightbulb():
    return icon_svg(
        "M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 1 1 7.072 0l-.548.547A3.374 3.374 0 0 0 14 18.469V19a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"
    )


def file_text():
    return icon_svg(
        "M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z M16 2v6h6 M8 13h8 M8 17h8 M8 9h1"
    )


def clock():
    return icon_svg("M12 8v4l3 3m6-3a9 9 0 1 1-18 0 9 9 0 0 1 18 0z")


def settings_icon():
    return icon_svg(
        "M12.22 2h-.44a2 2 0 0 0-2 2v.18a2 2 0 0 1-1 1.73l-.43.25a2 2 0 0 1-2 0l-.15-.08a2 2 0 0 0-2.73.73l-.22.38a2 2 0 0 0 .73 2.73l.15.1a2 2 0 0 1 1 1.72v.51a2 2 0 0 1-1 1.74l-.15.09a2 2 0 0 0-.73 2.73l.22.38a2 2 0 0 0 2.73.73l.15-.08a2 2 0 0 1 2 0l.43.25a2 2 0 0 1 1 1.73V20a2 2 0 0 0 2 2h.44a2 2 0 0 0 2-2v-.18a2 2 0 0 1 1-1.73l.43-.25a2 2 0 0 1 2 0l.15.08a2 2 0 0 0 2.73-.73l.22-.39a2 2 0 0 0-.73-2.73l-.15-.08a2 2 0 0 1-1-1.74v-.5a2 2 0 0 1 1-1.74l.15-.09a2 2 0 0 0 .73-2.73l-.22-.38a2 2 0 0 0-2.73-.73l-.15.08a2 2 0 0 1-2 0l-.43-.25a2 2 0 0 1-1-1.73V4a2 2 0 0 0-2-2z M12 15a3 3 0 1 0 0-6 3 3 0 0 0 0 6z"
    )


def zap():
    return icon_svg("M13 2L3 14h9l-1 8 10-12h-9l1-8z")


def sliders():
    return icon_svg("M4 21v-7m0-4V3m8 18v-9m0-4V3m8 18v-5m0-4V3M1 14h6m2-6h6m2 8h6")


def play():
    return icon_svg("M5 3l14 9-14 9V3z")


def check():
    return icon_svg("M20 6L9 17l-5-5")


def alert():
    return icon_svg("M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0zm-9 3.75h.008v.008H12v-.008z")


def spinner(size="sm", indicator=False):
    dim = {"sm": "w-3.5 h-3.5", "md": "w-4 h-4"}.get(size, "w-3.5 h-3.5")
    cls = f"animate-spin {dim} shrink-0" + (" htmx-indicator" if indicator else "")
    return Markup(
        f'<svg class="{cls}" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">\n    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>\n    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>\n</svg>'
    )


def loader():
    return spinner("md")


def copy_icon():
    return icon_svg(
        "M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z"
    )


def chevron_right():
    return icon_svg("M9 18l6-6-6-6")


def chevron_down():
    return icon_svg("M6 9l6 6 6-6")


def search():
    return icon_svg("M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z")


def activity():
    return icon_svg("M22 12h-4l-3 9L9 3l-3 9H2")


def video_icon():
    return icon_svg(
        "M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z"
    )


def film_icon():
    return icon_svg(
        "M7 4v16M17 4v16M3 8h4m10 0h4M3 12h18M3 16h4m10 0h4M4 20h16a1 1 0 001-1V5a1 1 0 00-1-1H4a1 1 0 00-1 1v14a1 1 0 001 1z"
    )


def download_icon():
    return icon_svg(
        '<path d="M4 14.899A7 7 0 1 1 15.71 8h1.79a4.5 4.5 0 0 1 2.5 8.242"/>'
        '<path d="M12 12v9"/>'
        '<path d="m8 17 4 4 4-4"/>'
    )


def bookmark():
    return icon_svg("M19 21l-7-5-7 5V5a2 2 0 012-2h10a2 2 0 012 2z")


def edit_icon():
    return icon_svg("M11 4H4a2 2 0 00-2 2v14a2 2 0 002 2h14a2 2 0 002-2v-7")


def refresh():
    return icon_svg(
        "M23 4v6h-6M1 20v-6h6M3.51 9a9 9 0 0114.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0020.49 15"
    )


def sun():
    return icon_svg(
        "M12 8a4 4 0 1 0 0 8 4 4 0 0 0 0-8zM12 2v2M12 20v2M4.93 4.93l1.41 1.41"
        "M19.07 4.93l-1.41 1.41M2 12h2M20 12h2M6.34 17.66l-1.41 1.41M17.66 17.66l1.41 1.41"
    )


def moon():
    return icon_svg("M12 3a6 6 0 0 0 9 9 9 9 0 1 1-9-9Z")


def trash_icon():
    return icon_svg(
        "M3 6h18m-2 0v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"
    )


def indicator_spinner():
    return spinner("sm", indicator=True)
