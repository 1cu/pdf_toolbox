from __future__ import annotations

"""
Setup:
py -m pip install pymupdf pillow python-docx pywin32 tkinterdnd2
# Start:
py gui.py
"""


import json
import os
import threading
import subprocess
import inspect
import pkgutil
import importlib
import pdf_toolbox
from pathlib import Path
from typing import Callable, Optional, Any

try:
    from tkinterdnd2 import DND_FILES, TkinterDnD  # type: ignore

    BaseTk = TkinterDnD.Tk
    DND_AVAILABLE = True
except Exception:  # pragma: no cover - optional
    import tkinter as tk  # type: ignore

    BaseTk = tk.Tk
    DND_FILES = None
    DND_AVAILABLE = False

import tkinter as tk  # type: ignore
from tkinter import ttk, filedialog, messagebox

from .utils import ensure_libs
from . import (
    extract,
    optimize,
    repair,
    unlock,
)

APPDATA = Path(os.getenv("APPDATA", Path.home() / "AppData" / "Roaming"))
CONFIG_PATH = APPDATA / "JensTools" / "pdf_toolbox" / "config.json"
CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
DEFAULT_CONFIG = {
    "last_open_dir": str(Path.home()),
    "last_save_dir": str(Path.home()),
    "jpeg_quality": 95,
    "pptx_width": 1920,
    "pptx_height": 1080,
    "opt_quality": "default",
    "opt_compress_images": False,
    "split_pages": 1,
}


def load_config() -> dict:
    if CONFIG_PATH.exists():
        try:
            return json.loads(CONFIG_PATH.read_text())
        except Exception:
            pass
    return DEFAULT_CONFIG.copy()


def save_config(cfg: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(cfg, indent=2))


class LogMixin:
    def __init__(self, text: tk.Text):
        self.text = text

    def log(self, msg: str) -> None:
        self.text["state"] = "normal"
        self.text.insert("end", msg + "\n")
        self.text.see("end")
        self.text["state"] = "disabled"


class FileEntry(ttk.Frame):
    def __init__(self, master: tk.Widget, cfg: dict, key: str, **kwargs):
        super().__init__(master, **kwargs)
        self.cfg = cfg
        self.key = key
        self.entry = ttk.Entry(self, width=50)
        self.entry.grid(row=0, column=0, sticky="ew")
        btn = ttk.Button(self, text="...", command=self.browse)
        btn.grid(row=0, column=1)
        self.columnconfigure(0, weight=1)
        if DND_AVAILABLE:
            self.entry.drop_target_register(DND_FILES)  # type: ignore[attr-defined]
            self.entry.dnd_bind("<<Drop>>", self._drop)  # type: ignore[attr-defined]

    def _drop(self, event):  # pragma: no cover - GUI only
        self.entry.delete(0, "end")
        self.entry.insert(0, event.data.strip("{}"))

    def browse(self):  # pragma: no cover - GUI only
        initial = self.cfg.get("last_open_dir", str(Path.home()))
        path = filedialog.askopenfilename(initialdir=initial)
        if path:
            self.entry.delete(0, "end")
            self.entry.insert(0, path)
            self.cfg["last_open_dir"] = str(Path(path).parent)

    def get(self) -> str:
        return self.entry.get()


class DirEntry(ttk.Frame):
    def __init__(self, master: tk.Widget, cfg: dict, key: str, **kwargs):
        super().__init__(master, **kwargs)
        self.cfg = cfg
        self.key = key
        self.entry = ttk.Entry(self, width=50)
        self.entry.grid(row=0, column=0, sticky="ew")
        btn = ttk.Button(self, text="...", command=self.browse)
        btn.grid(row=0, column=1)
        self.columnconfigure(0, weight=1)

    def browse(self):  # pragma: no cover - GUI only
        initial = self.cfg.get("last_save_dir", str(Path.home()))
        path = filedialog.askdirectory(initialdir=initial)
        if path:
            self.entry.delete(0, "end")
            self.entry.insert(0, path)
            self.cfg["last_save_dir"] = path

    def get(self) -> Optional[str]:
        val = self.entry.get().strip()
        return val or None


class BaseTab(ttk.Frame, LogMixin):
    TITLE: str = ""

    def __init__(self, master: ttk.Notebook, cfg: dict, title: str | None = None):
        self.cfg = cfg
        frame = ttk.Frame(master)
        master.add(frame, text=title or self.TITLE)
        text = tk.Text(frame, height=8, state="disabled")
        text.pack(side="bottom", fill="both", expand=True)
        LogMixin.__init__(self, text)
        ttk.Frame.__init__(self, frame)
        self.body = ttk.Frame(frame)
        self.body.pack(side="top", fill="both", expand=True)
        self.build(self.body)

    def build(self, body: ttk.Frame) -> None:  # pragma: no cover - to override
        pass

    def run_thread(self, func: Callable[..., Any], *args, **kwargs) -> None:
        def _target():
            try:
                self.log("Running...")
                func(*args, **kwargs)
                self.log("Done")
            except Exception as e:
                self.log(f"Error: {e}")

        threading.Thread(target=_target, daemon=True).start()


def _human_title(func_name: str) -> str:
    if "_to_" in func_name:
        left, right = func_name.split("_to_", 1)
        return f"{left.upper()} → {right.replace('_', ' ').upper()}"
    return func_name.replace("_", " ").title()


class FunctionTab(BaseTab):
    def __init__(self, master: ttk.Notebook, cfg: dict, func: Callable[..., Any]):
        self.func = func
        title = _human_title(func.__name__)
        super().__init__(master, cfg, title)

    def build(self, body: ttk.Frame) -> None:  # pragma: no cover - GUI only
        sig = inspect.signature(self.func)
        self._inputs: dict[str, tuple[Callable[[], Any], bool]] = {}
        row = 0
        for name, param in sig.parameters.items():
            ttk.Label(body, text=name).grid(row=row, column=0, sticky="w")
            getter, persist = self._add_input(body, row, name, param)
            self._inputs[name] = (getter, persist)
            row += 1
        ttk.Button(body, text="Run", command=self.do_run).grid(
            row=row, column=0, columnspan=2, pady=5
        )
        body.columnconfigure(1, weight=1)

    def _add_input(
        self, body: ttk.Frame, row: int, name: str, param: inspect.Parameter
    ) -> tuple[Callable[[], Any], bool]:
        ann = param.annotation
        default = None if param.default is inspect._empty else param.default

        if "dir" in name:
            dir_entry = DirEntry(body, self.cfg, "last_save_dir")
            dir_entry.grid(row=row, column=1, sticky="ew")
            return dir_entry.get, False

        if any(key in name for key in ("path", "file", "pdf", "pptx", "docx")):
            file_entry = FileEntry(body, self.cfg, "last_open_dir")
            file_entry.grid(row=row, column=1, sticky="ew")
            return file_entry.get, False

        if ann is bool:
            var = tk.BooleanVar(value=bool(default))
            chk = ttk.Checkbutton(body, variable=var)
            chk.grid(row=row, column=1, sticky="w")
            return var.get, True

        entry = ttk.Entry(body, width=10)
        if name in self.cfg:
            entry.insert(0, str(self.cfg[name]))
        elif default is not None:
            entry.insert(0, str(default))
        entry.grid(row=row, column=1, sticky="ew")

        def _get() -> Any:
            val = entry.get().strip()
            if val == "":
                return default
            if ann is int:
                return int(val)
            if ann is float:
                return float(val)
            return val

        return _get, True

    def do_run(self) -> None:  # pragma: no cover - GUI only
        kwargs = {}
        for name, (getter, persist) in self._inputs.items():
            val = getter()
            kwargs[name] = val
            if persist:
                self.cfg[name] = val
        self.run_thread(self.func, **kwargs)


def discover_converters() -> list[Callable[..., Any]]:
    converters: list[Callable[..., Any]] = []
    for mod_info in pkgutil.iter_modules(pdf_toolbox.__path__):
        if mod_info.name in {"gui", "rasterize", "utils"}:
            continue
        module = importlib.import_module(f"{__package__}.{mod_info.name}")
        for name, func in inspect.getmembers(module, inspect.isfunction):
            if "_to_" in name and func.__module__.startswith("pdf_toolbox"):
                converters.append(func)
    return converters


class ExtractTab(BaseTab):
    TITLE = "Extract / Split"

    def build(self, body: ttk.Frame) -> None:
        self.input = FileEntry(body, self.cfg, "last_open_dir")
        self.input.pack(fill="x")

        self.outdir = DirEntry(body, self.cfg, "last_save_dir")
        ttk.Label(body, text="Output Dir (optional)").pack(anchor="w")
        self.outdir.pack(fill="x")

        ex_frame = ttk.Frame(body)
        ttk.Label(ex_frame, text="Start").grid(row=0, column=0)
        ttk.Label(ex_frame, text="End").grid(row=0, column=2)
        self.start = ttk.Entry(ex_frame, width=5)
        self.end = ttk.Entry(ex_frame, width=5)
        self.start.grid(row=0, column=1)
        self.end.grid(row=0, column=3)
        ttk.Button(ex_frame, text="Extract", command=self.do_extract).grid(
            row=0, column=4, padx=5
        )
        ex_frame.pack(pady=5)

        split_frame = ttk.Frame(body)
        ttk.Label(split_frame, text="Pages per file").grid(row=0, column=0)
        self.pages = ttk.Entry(split_frame, width=5)
        self.pages.insert(0, str(self.cfg.get("split_pages", 1)))
        self.pages.grid(row=0, column=1)
        ttk.Button(split_frame, text="Split", command=self.do_split).grid(
            row=0, column=2, padx=5
        )
        split_frame.pack(pady=5)

    def do_extract(self):  # pragma: no cover - GUI only
        try:
            s = int(self.start.get())
            e = int(self.end.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid page numbers")
            return
        self.run_thread(
            extract.extract_range, self.input.get(), s, e, self.outdir.get()
        )

    def do_split(self):  # pragma: no cover - GUI only
        try:
            pages = int(self.pages.get())
            self.cfg["split_pages"] = pages
        except ValueError:
            messagebox.showerror("Error", "Invalid pages per file")
            return
        self.run_thread(extract.split_pdf, self.input.get(), pages, self.outdir.get())


class OptimizeTab(BaseTab):
    TITLE = "Optimize"

    def build(self, body: ttk.Frame) -> None:
        self.input = FileEntry(body, self.cfg, "last_open_dir")
        self.input.pack(fill="x")
        self.outdir = DirEntry(body, self.cfg, "last_save_dir")
        ttk.Label(body, text="Output Dir (optional)").pack(anchor="w")
        self.outdir.pack(fill="x")

        opt_frame = ttk.Frame(body)
        ttk.Label(opt_frame, text="Quality").grid(row=0, column=0)
        self.quality = ttk.Combobox(
            opt_frame, values=list(optimize.QUALITY_SETTINGS.keys())
        )
        self.quality.set(self.cfg.get("opt_quality", "default"))
        self.quality.grid(row=0, column=1)
        self.compress = tk.BooleanVar(value=self.cfg.get("opt_compress_images", False))
        ttk.Checkbutton(opt_frame, text="Compress images", variable=self.compress).grid(
            row=0, column=2
        )
        ttk.Button(opt_frame, text="Optimize", command=self.do_opt).grid(
            row=0, column=3, padx=5
        )
        opt_frame.pack(pady=5)

    def do_opt(self):  # pragma: no cover - GUI only
        self.cfg["opt_quality"] = self.quality.get()
        self.cfg["opt_compress_images"] = self.compress.get()
        self.run_thread(
            optimize.optimize_pdf,
            self.input.get(),
            self.quality.get(),
            self.compress.get(),
            True,
            self.outdir.get(),
        )


class RepairTab(BaseTab):
    TITLE = "Repair / Unlock"

    def build(self, body: ttk.Frame) -> None:
        self.input = FileEntry(body, self.cfg, "last_open_dir")
        self.input.pack(fill="x")
        self.outdir = DirEntry(body, self.cfg, "last_save_dir")
        ttk.Label(body, text="Output Dir (optional)").pack(anchor="w")
        self.outdir.pack(fill="x")
        btn_frame = ttk.Frame(body)
        ttk.Button(btn_frame, text="Repair", command=self.do_repair).grid(
            row=0, column=0, padx=5
        )
        self.pw = ttk.Entry(btn_frame, show="*")
        self.pw.grid(row=0, column=1)
        ttk.Button(btn_frame, text="Unlock", command=self.do_unlock).grid(
            row=0, column=2, padx=5
        )
        btn_frame.pack(pady=5)

    def do_repair(self):  # pragma: no cover - GUI only
        self.run_thread(repair.repair_pdf, self.input.get(), self.outdir.get())

    def do_unlock(self):  # pragma: no cover - GUI only
        self.run_thread(
            unlock.unlock_pdf,
            self.input.get(),
            self.pw.get() or None,
            self.outdir.get(),
        )


class BatchTab(BaseTab):
    TITLE = "Batch-Runner"

    def build(self, body: ttk.Frame) -> None:
        self.script = FileEntry(body, self.cfg, "last_open_dir")
        self.script.pack(fill="x")
        ttk.Label(body, text="Arguments").pack(anchor="w")
        self.args = ttk.Entry(body)
        self.args.pack(fill="x")
        ttk.Label(body, text="Python executable (optional)").pack(anchor="w")
        self.python = FileEntry(body, self.cfg, "last_open_dir")
        self.python.pack(fill="x")
        ttk.Button(body, text="Run", command=self.do_run).pack(pady=5)

    def do_run(self):  # pragma: no cover - GUI only
        script = self.script.get()
        argv = self.args.get().split()
        python = self.python.get() or "python"

        def _run():
            try:
                proc = subprocess.run(
                    [python, script, *argv], capture_output=True, text=True
                )
                self.log(proc.stdout)
                if proc.stderr:
                    self.log(proc.stderr)
            except Exception as e:
                self.log(str(e))

        threading.Thread(target=_run, daemon=True).start()


def main() -> None:  # pragma: no cover - GUI only
    ensure_libs()
    cfg = load_config()
    root = BaseTk()
    root.title("PDF Toolbox")
    nb = ttk.Notebook(root)
    nb.pack(fill="both", expand=True)

    static_tabs = [ExtractTab, OptimizeTab, RepairTab, BatchTab]
    _instances = [tab(nb, cfg) for tab in static_tabs]
    for func in discover_converters():
        FunctionTab(nb, cfg, func)

    def on_close():
        save_config(cfg)
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
