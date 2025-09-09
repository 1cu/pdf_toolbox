from __future__ import annotations
"""
Setup:
py -m pip install pymupdf pillow python-docx pywin32 tkinterdnd2
# Start:
py pdf_toolbox_gui.py
"""


import json
import os
import threading
import subprocess
from pathlib import Path
from typing import Callable, Optional

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

from common_utils import ensure_libs
import page_extract
import optimize
import repair
import unlock
import to_jpegs
import to_tiff
import to_word
import pptx_export

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
            self.entry.drop_target_register(DND_FILES)
            self.entry.dnd_bind("<<Drop>>", self._drop)

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
    def __init__(self, master: ttk.Notebook, cfg: dict):
        self.cfg = cfg
        frame = ttk.Frame(master)
        master.add(frame, text=self.TITLE)
        text = tk.Text(frame, height=8, state="disabled")
        text.pack(side="bottom", fill="both", expand=True)
        LogMixin.__init__(self, text)
        ttk.Frame.__init__(self, frame)
        self.body = ttk.Frame(frame)
        self.body.pack(side="top", fill="both", expand=True)
        self.build(self.body)

    def build(self, body: ttk.Frame) -> None:  # pragma: no cover - to override
        pass

    def run_thread(self, func: Callable, *args):
        def _target():
            try:
                self.log("Running...")
                func(*args)
                self.log("Done")
            except Exception as e:
                self.log(f"Error: {e}")
        threading.Thread(target=_target, daemon=True).start()


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
        ttk.Button(ex_frame, text="Extract", command=self.do_extract).grid(row=0, column=4, padx=5)
        ex_frame.pack(pady=5)

        split_frame = ttk.Frame(body)
        ttk.Label(split_frame, text="Pages per file").grid(row=0, column=0)
        self.pages = ttk.Entry(split_frame, width=5)
        self.pages.insert(0, str(self.cfg.get("split_pages", 1)))
        self.pages.grid(row=0, column=1)
        ttk.Button(split_frame, text="Split", command=self.do_split).grid(row=0, column=2, padx=5)
        split_frame.pack(pady=5)

    def do_extract(self):  # pragma: no cover - GUI only
        try:
            s = int(self.start.get())
            e = int(self.end.get())
        except ValueError:
            messagebox.showerror("Error", "Invalid page numbers")
            return
        self.run_thread(page_extract.extract_range, self.input.get(), s, e, self.outdir.get())

    def do_split(self):  # pragma: no cover - GUI only
        try:
            pages = int(self.pages.get())
            self.cfg["split_pages"] = pages
        except ValueError:
            messagebox.showerror("Error", "Invalid pages per file")
            return
        self.run_thread(page_extract.split_pdf, self.input.get(), pages, self.outdir.get())


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
        self.quality = ttk.Combobox(opt_frame, values=list(optimize.QUALITY_SETTINGS.keys()))
        self.quality.set(self.cfg.get("opt_quality", "default"))
        self.quality.grid(row=0, column=1)
        self.compress = tk.BooleanVar(value=self.cfg.get("opt_compress_images", False))
        ttk.Checkbutton(opt_frame, text="Compress images", variable=self.compress).grid(row=0, column=2)
        ttk.Button(opt_frame, text="Optimize", command=self.do_opt).grid(row=0, column=3, padx=5)
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
        ttk.Button(btn_frame, text="Repair", command=self.do_repair).grid(row=0, column=0, padx=5)
        self.pw = ttk.Entry(btn_frame, show="*")
        self.pw.grid(row=0, column=1)
        ttk.Button(btn_frame, text="Unlock", command=self.do_unlock).grid(row=0, column=2, padx=5)
        btn_frame.pack(pady=5)

    def do_repair(self):  # pragma: no cover - GUI only
        self.run_thread(repair.repair_pdf, self.input.get(), self.outdir.get())

    def do_unlock(self):  # pragma: no cover - GUI only
        self.run_thread(unlock.unlock_pdf, self.input.get(), self.pw.get() or None, self.outdir.get())


class JPEGTab(BaseTab):
    TITLE = "PDF → JPEG"

    def build(self, body: ttk.Frame) -> None:
        self.input = FileEntry(body, self.cfg, "last_open_dir")
        self.input.pack(fill="x")
        self.outdir = DirEntry(body, self.cfg, "last_save_dir")
        ttk.Label(body, text="Output Dir (optional)").pack(anchor="w")
        self.outdir.pack(fill="x")

        frame = ttk.Frame(body)
        ttk.Label(frame, text="Start").grid(row=0, column=0)
        ttk.Label(frame, text="End").grid(row=0, column=2)
        self.start = ttk.Entry(frame, width=5)
        self.end = ttk.Entry(frame, width=5)
        self.start.grid(row=0, column=1)
        self.end.grid(row=0, column=3)
        ttk.Label(frame, text="Quality").grid(row=1, column=0)
        self.quality = ttk.Entry(frame, width=5)
        self.quality.insert(0, str(self.cfg.get("jpeg_quality", 95)))
        self.quality.grid(row=1, column=1)
        ttk.Button(frame, text="Convert", command=self.do_conv).grid(row=1, column=3, padx=5)
        frame.pack(pady=5)

    def do_conv(self):  # pragma: no cover - GUI only
        start = int(self.start.get()) if self.start.get() else None
        end = int(self.end.get()) if self.end.get() else None
        q = int(self.quality.get())
        self.cfg["jpeg_quality"] = q
        self.run_thread(to_jpegs.pdf_to_jpegs, self.input.get(), start, end, q, self.outdir.get())


class TIFFTab(BaseTab):
    TITLE = "PDF → TIFF"

    def build(self, body: ttk.Frame) -> None:
        self.input = FileEntry(body, self.cfg, "last_open_dir")
        self.input.pack(fill="x")
        self.outdir = DirEntry(body, self.cfg, "last_save_dir")
        ttk.Label(body, text="Output Dir (optional)").pack(anchor="w")
        self.outdir.pack(fill="x")
        ttk.Button(body, text="Convert", command=self.do_conv).pack(pady=5)

    def do_conv(self):  # pragma: no cover - GUI only
        self.run_thread(to_tiff.pdf_to_tiff, self.input.get(), self.outdir.get())


class WordTab(BaseTab):
    TITLE = "PDF → Word"

    def build(self, body: ttk.Frame) -> None:
        self.input = FileEntry(body, self.cfg, "last_open_dir")
        self.input.pack(fill="x")
        self.outdir = DirEntry(body, self.cfg, "last_save_dir")
        ttk.Label(body, text="Output Dir (optional)").pack(anchor="w")
        self.outdir.pack(fill="x")
        ttk.Button(body, text="Convert", command=self.do_conv).pack(pady=5)

    def do_conv(self):  # pragma: no cover - GUI only
        self.run_thread(to_word.pdf_to_docx, self.input.get(), self.outdir.get())


class PPTXTab(BaseTab):
    TITLE = "PPTX → JPEG"

    def build(self, body: ttk.Frame) -> None:
        self.input = FileEntry(body, self.cfg, "last_open_dir")
        self.input.pack(fill="x")
        self.outdir = DirEntry(body, self.cfg, "last_save_dir")
        ttk.Label(body, text="Output Dir (optional)").pack(anchor="w")
        self.outdir.pack(fill="x")

        frame = ttk.Frame(body)
        ttk.Label(frame, text="Width").grid(row=0, column=0)
        ttk.Label(frame, text="Height").grid(row=0, column=2)
        self.width = ttk.Entry(frame, width=6)
        self.height = ttk.Entry(frame, width=6)
        self.width.insert(0, str(self.cfg.get("pptx_width", 1920)))
        self.height.insert(0, str(self.cfg.get("pptx_height", 1080)))
        self.width.grid(row=0, column=1)
        self.height.grid(row=0, column=3)
        ttk.Button(frame, text="Convert", command=self.do_conv).grid(row=0, column=4, padx=5)
        frame.pack(pady=5)

    def do_conv(self):  # pragma: no cover - GUI only
        w = int(self.width.get())
        h = int(self.height.get())
        self.cfg["pptx_width"] = w
        self.cfg["pptx_height"] = h
        self.run_thread(pptx_export.pptx_to_jpegs_via_powerpoint, self.input.get(), w, h, self.outdir.get())


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
                proc = subprocess.run([python, script, *argv], capture_output=True, text=True)
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

    tabs = [ExtractTab, OptimizeTab, RepairTab, JPEGTab, TIFFTab, WordTab, PPTXTab, BatchTab]
    instances = [tab(nb, cfg) for tab in tabs]

    def on_close():
        save_config(cfg)
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_close)
    root.mainloop()


if __name__ == "__main__":
    main()
