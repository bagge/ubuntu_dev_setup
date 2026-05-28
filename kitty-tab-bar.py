# pyright: reportMissingImports=false
"""Custom kitty tab bar styled to match the Neovim lualine/tabby setup."""

import os
import subprocess
import sys
import time

from kitty.fast_data_types import Color, Screen, add_timer, get_boss
from kitty.tab_bar import DrawData, ExtraData, TabBarData, as_rgb, draw_title
from kitty.utils import color_as_int


LEFT_SEPARATOR = ""
RIGHT_SEPARATOR = ""
REFRESH_SECONDS = 2.0


def color(red: int, green: int, blue: int) -> int:
    return as_rgb(color_as_int(Color(red, green, blue)))


DRACULA_BLACK = color(0x19, 0x1A, 0x21)
DRACULA_MENU = color(0x21, 0x22, 0x2C)
DRACULA_COMMENT = color(0x62, 0x72, 0xA4)
DRACULA_PURPLE = color(0xBD, 0x93, 0xF9)
DRACULA_FOREGROUND = color(0xF8, 0xF8, 0xF2)

timer_id = None
last_network_sample = None


def draw_segment(screen: Screen, text: str, fg: int, bg: int, bold: bool = False) -> None:
    screen.cursor.fg = fg
    screen.cursor.bg = bg
    screen.cursor.bold = bold
    screen.cursor.italic = False
    screen.draw(text)


def draw_tab_title(
    draw_data: DrawData,
    screen: Screen,
    tab: TabBarData,
    before: int,
    max_title_length: int,
    index: int,
) -> None:
    if max_title_length <= 1:
        screen.draw("…")
        return

    if draw_data.leading_spaces:
        screen.draw(" " * draw_data.leading_spaces)

    draw_title(draw_data, screen, tab, index)
    trailing_spaces = min(max_title_length - 1, draw_data.trailing_spaces)
    max_title_length -= trailing_spaces
    extra = screen.cursor.x - before - max_title_length
    if extra > 0:
        screen.cursor.x -= extra + 1
        screen.draw("…")
    if trailing_spaces:
        screen.draw(" " * trailing_spaces)


def redraw_tab_bar(_) -> None:
    boss = get_boss()
    tab_managers = getattr(boss, "all_tab_managers", ())
    active_tab_manager = getattr(boss, "active_tab_manager", None)
    if not tab_managers and active_tab_manager is not None:
        tab_managers = (active_tab_manager,)

    for tab_manager in tab_managers:
        tab_manager.mark_tab_bar_dirty()


def ensure_timer() -> None:
    global timer_id

    if timer_id is None:
        timer_id = add_timer(redraw_tab_bar, REFRESH_SECONDS, True)


def cpu_load() -> str:
    try:
        return f"{os.getloadavg()[0]:.2f}"
    except OSError:
        return "--"


def linux_memory_usage() -> str | None:
    try:
        values = {}
        with open("/proc/meminfo", encoding="utf-8") as meminfo:
            for line in meminfo:
                key, raw_value = line.split(":", 1)
                values[key] = int(raw_value.strip().split()[0])
    except (FileNotFoundError, ValueError):
        return None

    total = values.get("MemTotal")
    available = values.get("MemAvailable")
    if not total or available is None:
        return None
    used_percent = (total - available) / total * 100
    return f"{used_percent:.0f}%"


def macos_memory_usage() -> str | None:
    try:
        total = int(subprocess.check_output(["sysctl", "-n", "hw.memsize"], text=True).strip())
        vm_stat = subprocess.check_output(["vm_stat"], text=True)
    except (OSError, subprocess.SubprocessError, ValueError):
        return None

    page_size = 4096
    free_pages = 0
    for line in vm_stat.splitlines():
        if "page size of" in line:
            page_size = int(line.split("page size of", 1)[1].split("bytes", 1)[0].strip())
        elif line.startswith(("Pages free:", "Pages inactive:", "Pages speculative:")):
            free_pages += int(line.rsplit(":", 1)[1].strip().rstrip("."))

    available = free_pages * page_size
    used_percent = max(0, min(100, (total - available) / total * 100))
    return f"{used_percent:.0f}%"


def memory_usage() -> str:
    return linux_memory_usage() or (macos_memory_usage() if sys.platform == "darwin" else None) or "--"


def linux_network_totals() -> tuple[int, int] | None:
    try:
        with open("/proc/net/dev", encoding="utf-8") as interfaces:
            lines = interfaces.readlines()[2:]
    except FileNotFoundError:
        return None

    rx_bytes = 0
    tx_bytes = 0
    for line in lines:
        name, raw_values = line.split(":", 1)
        if name.strip() == "lo":
            continue
        values = raw_values.split()
        rx_bytes += int(values[0])
        tx_bytes += int(values[8])
    return rx_bytes, tx_bytes


def macos_network_totals() -> tuple[int, int] | None:
    try:
        netstat = subprocess.check_output(["netstat", "-ibn"], text=True)
    except (OSError, subprocess.SubprocessError):
        return None

    rows = netstat.splitlines()
    if not rows:
        return None

    headers = rows[0].split()
    try:
        name_index = headers.index("Name")
        ibytes_index = headers.index("Ibytes")
        obytes_index = headers.index("Obytes")
    except ValueError:
        return None

    interfaces: dict[str, tuple[int, int]] = {}
    for row in rows[1:]:
        columns = row.split()
        if len(columns) <= max(name_index, ibytes_index, obytes_index):
            continue
        name = columns[name_index]
        if name.startswith("lo"):
            continue
        try:
            ibytes = int(columns[ibytes_index])
            obytes = int(columns[obytes_index])
        except ValueError:
            continue
        previous = interfaces.get(name, (0, 0))
        interfaces[name] = (max(previous[0], ibytes), max(previous[1], obytes))

    if not interfaces:
        return None
    return tuple(sum(values[index] for values in interfaces.values()) for index in (0, 1))


def network_totals() -> tuple[int, int] | None:
    return linux_network_totals() or (macos_network_totals() if sys.platform == "darwin" else None)


def network_rates() -> tuple[float | None, float | None]:
    global last_network_sample

    totals = network_totals()
    now = time.monotonic()
    if totals is None:
        last_network_sample = None
        return None, None

    rx_bytes, tx_bytes = totals
    if last_network_sample is None:
        last_network_sample = (now, rx_bytes, tx_bytes)
        return None, None

    last_time, last_rx_bytes, last_tx_bytes = last_network_sample
    last_network_sample = (now, rx_bytes, tx_bytes)
    elapsed = max(now - last_time, 0.001)
    return (
        max(0, rx_bytes - last_rx_bytes) / elapsed,
        max(0, tx_bytes - last_tx_bytes) / elapsed,
    )


def format_rate(rate: float | None) -> str:
    if rate is None:
        return "--/s"

    units = ("B/s", "K/s", "M/s", "G/s")
    value = rate
    for unit in units:
        if value < 1024 or unit == units[-1]:
            if unit == "B/s":
                return f"{value:.0f}{unit}"
            return f"{value:.1f}{unit}" if value < 10 else f"{value:.0f}{unit}"
        value /= 1024

    return "--/s"


def fixed_width_value(value: str, width: int) -> str:
    if len(value) > width:
        return value[: width - 1] + "…"
    return value.rjust(width)


def metric_cell(label: str, value: str, value_width: int) -> str:
    return f" {label} {fixed_width_value(value, value_width)} "


def status_cells() -> list[tuple[int, str]]:
    rx_rate, tx_rate = network_rates()
    return [
        (DRACULA_PURPLE, metric_cell("LOAD", cpu_load(), 6)),
        (DRACULA_FOREGROUND, metric_cell("MEM", memory_usage(), 4)),
        (DRACULA_COMMENT, metric_cell("↓", format_rate(rx_rate), 7)),
        (DRACULA_COMMENT, metric_cell("↑", format_rate(tx_rate), 7)),
    ]


def status_width(cells: list[tuple[int, str]]) -> int:
    return 2 + sum(len(text) for _, text in cells)


def fit_status_cells(cells: list[tuple[int, str]], width: int) -> list[tuple[int, str]]:
    cells = list(cells)
    while cells and status_width(cells) > width:
        cells.pop(0)
    return cells


def draw_right_status(screen: Screen, is_last: bool) -> None:
    if not is_last:
        return

    cells = fit_status_cells(status_cells(), screen.columns - screen.cursor.x)
    if not cells:
        return

    width = status_width(cells)
    padding = screen.columns - screen.cursor.x - width
    if padding <= 0:
        return

    draw_segment(screen, " " * padding, DRACULA_BLACK, DRACULA_BLACK)
    draw_segment(screen, LEFT_SEPARATOR, DRACULA_MENU, DRACULA_BLACK)
    for fg, text in cells:
        draw_segment(screen, text, fg, DRACULA_MENU)
    draw_segment(screen, RIGHT_SEPARATOR, DRACULA_MENU, DRACULA_BLACK)


def draw_tab(
    draw_data: DrawData,
    screen: Screen,
    tab: TabBarData,
    before: int,
    max_title_length: int,
    index: int,
    is_last: bool,
    extra_data: ExtraData,
) -> int:
    if not extra_data.for_layout:
        ensure_timer()

    tab_bg = DRACULA_PURPLE if tab.is_active else DRACULA_MENU
    tab_fg = DRACULA_BLACK if tab.is_active else DRACULA_COMMENT

    draw_segment(screen, LEFT_SEPARATOR, tab_bg, DRACULA_BLACK)
    title_start = screen.cursor.x
    screen.cursor.fg = tab_fg
    screen.cursor.bg = tab_bg
    screen.cursor.bold = tab.is_active
    screen.cursor.italic = False
    draw_tab_title(draw_data, screen, tab, title_start, max(1, max_title_length - 3), index)
    draw_segment(screen, RIGHT_SEPARATOR, tab_bg, DRACULA_BLACK)
    draw_segment(screen, " ", DRACULA_BLACK, DRACULA_BLACK)

    screen.cursor.bold = False
    screen.cursor.italic = False
    end = screen.cursor.x
    if not extra_data.for_layout:
        draw_right_status(screen, is_last)
    return end
