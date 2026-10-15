#!/usr/bin/env python3
"""ISG Desktop · interfaz local para Debian y derivados mediante Tkinter."""
from __future__ import annotations

import math
import os
from pathlib import Path
import queue
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

from isg_core import ISGError, decode, encode, estimate_encode
from isg_batch import (prepare_jobs, execute_jobs, prepare_decode_jobs, execute_decode_jobs)
from isg_privacy import cleanup_legacy_state, DEFAULTS

VERSION = "1.0.0"
BG, INK, MUTED, ACCENT = "#f3f6fb", "#17263a", "#596a7c", "#245eaa"
INITIAL_DIR = Path.home()


def readable_size(size: int) -> str:
    value = float(size)
    for unit in ("B", "KiB", "MiB", "GiB", "TiB"):
        if value < 1024 or unit == "TiB":
            return f"{value:.0f} {unit}" if unit == "B" else f"{value:.1f} {unit}"
        value /= 1024
    return f"{value:.1f} TiB"


def readable_time(seconds: float) -> str:
    seconds = max(0, round(seconds))
    if seconds < 60:
        return f"{seconds} s"
    minutes, seconds = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes} min {seconds:02d} s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours} h {minutes:02d} min"


class App(tk.Tk):
    def __init__(self):
        super().__init__(className="ISGDesktop")
        self.title("ISG Desktop")
        self._set_app_icon()
        self.geometry("960x740")
        self.minsize(710, 500)
        self.configure(bg=BG)
        self.events: queue.Queue = queue.Queue()
        self.cancel_event = threading.Event()
        self.running = False
        self.current_task = ""
        self.started = 0.0
        self.last_progress = 0.0
        self.raw_status = "Preparado."
        self.close_on_completion = False
        self.legacy_remaining = cleanup_legacy_state()
        self.dnd_ready = False
        self._drop_targets = []
        self._autofilled_video_dest = ""
        self._autofilled_restore_folder = ""
        self.task_item_name = ""
        self._setup_theme()
        self._create_ui()
        self._init_dnd()
        self.after(100, self._read_events)
        if self.legacy_remaining:
            self.after(300, lambda: messagebox.showwarning(
                "Datos de versiones anteriores",
                "No se pudieron eliminar algunos datos antiguos de ISG Desktop por permisos. "
                "Comprueba las carpetas XDG de la aplicación y elimina los ficheros manualmente."))
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.bind_all("<Control-q>", lambda _event: self._on_close())

    def _set_app_icon(self):
        """Aplica el logo propio a la ventana y al dock, sin dependencias gráficas extra.

        En el paquete Debian, los iconos se instalan junto al programa; al
        ejecutarlo desde el ZIP se utilizan los mismos recursos locales.
        """
        assets = Path(__file__).resolve().parent / "assets"
        icons = []
        for size in (128, 64, 32):
            path = assets / f"isg-desktop-{size}.png"
            if path.is_file():
                icons.append(tk.PhotoImage(master=self, file=str(path)))
        if icons:
            self.iconphoto(True, *icons)
            self._icon_images = icons  # Evitar recolección por Python.

    def _setup_theme(self):
        style = ttk.Style(self)
        if "clam" in style.theme_names():
            style.theme_use("clam")
        style.configure("TFrame", background=BG)
        style.configure("TLabel", background=BG, foreground=INK, font=("Sans", 10))
        style.configure("Subtitle.TLabel", font=("Sans", 10), background=BG, foreground=MUTED)
        style.configure("Section.TLabel", font=("Sans", 11, "bold"), background=BG)
        style.configure("TButton", font=("Sans", 10), padding=(11, 7))
        style.configure("Accent.TButton", foreground="#ffffff", background=ACCENT)
        style.map("Accent.TButton", background=[("active", "#17497f"), ("disabled", "#9db1c9")])
        style.configure("TEntry", padding=(7, 7))
        style.configure("TNotebook", background=BG, borderwidth=0)
        style.configure("TNotebook.Tab", padding=(10, 7), font=("Sans", 10))
        style.configure("Horizontal.TProgressbar", thickness=15)
        style.configure("Drop.TLabel", background="#e4ebf7", foreground=ACCENT, font=("Sans", 10), relief="solid", borderwidth=1)

    def _make_scrolled_tab(self, label: str):
        """Desplazamiento solo cuando el contenido supera el espacio disponible."""
        wrapper = ttk.Frame(self.tabs)
        self.tabs.add(wrapper, text=label)
        canvas = tk.Canvas(wrapper, bg=BG, highlightthickness=0, borderwidth=0)
        scrollbar = ttk.Scrollbar(wrapper, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=scrollbar.set)
        canvas.pack(side="left", fill="both", expand=True)
        inner = ttk.Frame(canvas, padding=(14, 12))
        window_id = canvas.create_window((0, 0), window=inner, anchor="nw")
        if not hasattr(self, "_scrolled_tabs"):
            self._scrolled_tabs = {}
        self._scrolled_tabs[label] = (wrapper, canvas, scrollbar, inner)
        pending = {"job": None}

        def refresh():
            pending["job"] = None
            if not canvas.winfo_exists() or not wrapper.winfo_ismapped():
                return
            visible_height = canvas.winfo_height()
            if visible_height <= 1:
                return  # Antes de que el gestor geométrico haya dimensionado la pestaña.
            content_height = inner.winfo_reqheight()
            needs_scroll = content_height > visible_height + 1
            has_scroll = bool(scrollbar.winfo_manager())
            if needs_scroll and not has_scroll:
                scrollbar.pack(side="right", fill="y", before=canvas)
            elif not needs_scroll and has_scroll:
                scrollbar.pack_forget()
                canvas.yview_moveto(0)

        def schedule_refresh():
            if pending["job"] is None:
                pending["job"] = self.after_idle(refresh)

        def inner_changed(_event):
            canvas.configure(scrollregion=canvas.bbox("all"))
            schedule_refresh()

        def canvas_changed(event):
            canvas.itemconfigure(window_id, width=event.width)
            schedule_refresh()

        inner.bind("<Configure>", inner_changed)
        canvas.bind("<Configure>", canvas_changed)
        wrapper.bind("<Map>", lambda _event: schedule_refresh())

        # Ratón/touchpad: no capturar el desplazamiento si ya cabe todo.
        def wheel(event):
            if not scrollbar.winfo_manager():
                return
            delta = getattr(event, "delta", 0)
            if delta:
                canvas.yview_scroll(-int(delta / 120) or (-1 if delta > 0 else 1), "units")
            elif getattr(event, "num", None) in (4, 5):
                canvas.yview_scroll(-1 if event.num == 4 else 1, "units")
            return "break"

        def on_enter(_event):
            canvas.bind_all("<MouseWheel>", wheel)
            canvas.bind_all("<Button-4>", wheel)
            canvas.bind_all("<Button-5>", wheel)

        def on_leave(_event):
            for sequence in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
                canvas.unbind_all(sequence)

        canvas.bind("<Enter>", on_enter)
        canvas.bind("<Leave>", on_leave)
        return inner

    def _auto_list_scroll(self, listbox, scrollbar):
        """Oculta la barra de una lista mientras sus elementos caben en pantalla."""
        state = {"job": None, "bounds": (0.0, 1.0)}

        def refresh():
            state["job"] = None
            if not scrollbar.winfo_exists():
                return
            first, last = state["bounds"]
            needs_scroll = first > 0.00001 or last < 0.99999
            if needs_scroll and not scrollbar.winfo_manager():
                scrollbar.pack(side="right", fill="y")
            elif not needs_scroll and scrollbar.winfo_manager():
                scrollbar.pack_forget()

        def on_scroll(first, last):
            scrollbar.set(first, last)
            state["bounds"] = (float(first), float(last))
            if state["job"] is None:
                state["job"] = self.after_idle(refresh)

        listbox.configure(yscrollcommand=on_scroll)

    def _create_ui(self):
        root = ttk.Frame(self, padding=(16, 12))
        root.pack(fill="both", expand=True)

        self.tabs = ttk.Notebook(root, height=185)
        self.tabs.pack(fill="both", expand=True)
        enc = self._make_scrolled_tab("Crear")
        dec = self._make_scrolled_tab("Recuperar")
        batch = self._make_scrolled_tab("Lotes")
        info = self._make_scrolled_tab("Información")

        self.source_file = tk.StringVar()
        self.video_dest = tk.StringVar()
        self.resolution = tk.StringVar(value=DEFAULTS["resolution"])
        self.block_size = tk.StringVar(value=DEFAULTS["block_size"])
        self.redundancy = tk.StringVar(value=DEFAULTS["redundancy"])
        self.restore_video = tk.StringVar()
        self.restore_folder = tk.StringVar(value=DEFAULTS["restore_folder"])
        self.batch_folder = tk.StringVar(value=DEFAULTS["batch_folder"])
        self.decode_batch_folder = tk.StringVar(value=DEFAULTS["decode_batch_folder"])
        self.batch_files: list[str] = []
        self.decode_batch_files: list[str] = []

        ttk.Label(enc, text="Generar un vídeo", style="Section.TLabel").pack(anchor="w", pady=(0, 12))
        self._field(enc, "Archivo de origen", self.source_file, file_select=True)
        self.drop_create = self._drop_area(enc, "Arrastra aquí un archivo para crear un vídeo")
        self._field(enc, "Guardar vídeo como", self.video_dest, file_save=True)
        options = ttk.Frame(enc)
        options.pack(fill="x", pady=(0, 10))
        for col, (title, var, choices) in enumerate((
            ("Resolución", self.resolution, ("1280x720", "1920x1080")),
            ("Bloque de píxeles", self.block_size, ("8", "12", "16")),
            ("Copias", self.redundancy, ("1", "2", "3")),
        )):
            part = ttk.Frame(options)
            part.grid(row=0, column=col, sticky="ew", padx=(0, 9))
            ttk.Label(part, text=title).pack(anchor="w", pady=(0, 4))
            ttk.Combobox(part, textvariable=var, values=choices, state="readonly", width=10).pack(fill="x")
            options.columnconfigure(col, weight=1)
        self.estimate = tk.StringVar(value="Selecciona un archivo para estimar la duración del vídeo.")
        ttk.Label(enc, textvariable=self.estimate, style="Subtitle.TLabel", wraplength=610).pack(
            anchor="w", pady=(1, 10))
        self.start_enc = ttk.Button(enc, text="Crear vídeo", style="Accent.TButton", command=self._start_encode)
        self.start_enc.pack(anchor="w", pady=(0, 7))
        for var in (self.source_file, self.resolution, self.block_size, self.redundancy):
            var.trace_add("write", lambda *_: self._update_estimate())

        ttk.Label(dec, text="Recuperar archivo original", style="Section.TLabel").pack(anchor="w", pady=(0, 12))
        self._field(dec, "Vídeo de origen", self.restore_video, file_select=True)
        self.drop_restore = self._drop_area(dec, "Arrastra aquí un vídeo para recuperar su archivo")
        self._field(dec, "Carpeta donde recuperar el archivo (por defecto, junto al vídeo)", self.restore_folder, folder_select=True)
        self.start_dec = ttk.Button(dec, text="Recuperar archivo", style="Accent.TButton",
                                    command=self._start_decode)
        self.start_dec.pack(anchor="w", pady=(5, 12))

        ttk.Label(batch, text="Convertir varios archivos", style="Section.TLabel").pack(anchor="w", pady=(0, 6))
        ttk.Label(batch, text="Genera un vídeo independiente por cada archivo",
                  style="Subtitle.TLabel", wraplength=610).pack(anchor="w", pady=(0, 9))
        batch_controls = ttk.Frame(batch)
        batch_controls.pack(fill="x", pady=(0, 6))
        self.batch_add = ttk.Button(batch_controls, text="Añadir archivos…", command=self._batch_add)
        self.batch_add.pack(side="left", padx=(0, 5))
        self.batch_remove = ttk.Button(batch_controls, text="Quitar selección", command=self._batch_remove)
        self.batch_remove.pack(side="left", padx=(0, 5))
        self.batch_clear = ttk.Button(batch_controls, text="Vaciar lista", command=self._batch_clear)
        self.batch_clear.pack(side="left")
        batch_list_frame = ttk.Frame(batch)
        batch_list_frame.pack(fill="x", pady=(0, 8))
        self.batch_list = tk.Listbox(batch_list_frame, height=5, selectmode=tk.EXTENDED, exportselection=False,
                                     font=("Sans", 10), bg="#fff", fg=INK, activestyle="dotbox")
        list_scroll = ttk.Scrollbar(batch_list_frame, orient="vertical", command=self.batch_list.yview)
        self._auto_list_scroll(self.batch_list, list_scroll)
        self.batch_list.pack(side="left", fill="x", expand=True)
        self.drop_batch = self._drop_area(batch, "Arrastra aquí varios archivos para convertirlos")
        self._field(batch, "Carpeta para los vídeos del lote (vacío = junto al original)", self.batch_folder, folder_select=True)
        self.batch_count = tk.StringVar(value="0 archivos seleccionados")
        ttk.Label(batch, textvariable=self.batch_count, style="Subtitle.TLabel").pack(anchor="w", pady=(0, 5))
        self.start_batch = ttk.Button(batch, text="Convertir lote", style="Accent.TButton", command=self._start_batch)
        self.start_batch.pack(anchor="w", pady=(0, 12))

        ttk.Separator(batch, orient="horizontal").pack(fill="x", pady=(8, 14))
        ttk.Label(batch, text="Recuperar varios vídeos", style="Section.TLabel").pack(anchor="w", pady=(0, 6))
        ttk.Label(batch, text="Cada vídeo recupera su archivo",
                  style="Subtitle.TLabel", wraplength=610).pack(anchor="w", pady=(0, 9))
        decode_controls = ttk.Frame(batch)
        decode_controls.pack(fill="x", pady=(0, 6))
        self.batch_decode_add = ttk.Button(decode_controls, text="Añadir vídeos…",
                                           command=self._decode_batch_add)
        self.batch_decode_add.pack(side="left", padx=(0, 5))
        self.batch_decode_remove = ttk.Button(decode_controls, text="Quitar selección",
                                              command=self._decode_batch_remove)
        self.batch_decode_remove.pack(side="left", padx=(0, 5))
        self.batch_decode_clear = ttk.Button(decode_controls, text="Vaciar vídeos",
                                             command=self._decode_batch_clear)
        self.batch_decode_clear.pack(side="left")
        frame = ttk.Frame(batch)
        frame.pack(fill="x", pady=(0, 8))
        self.decode_batch_list = tk.Listbox(frame, height=5, selectmode=tk.EXTENDED,
                                            exportselection=False, font=("Sans", 10),
                                            bg="#fff", fg=INK, activestyle="dotbox")
        decode_scroll = ttk.Scrollbar(frame, orient="vertical", command=self.decode_batch_list.yview)
        self._auto_list_scroll(self.decode_batch_list, decode_scroll)
        self.decode_batch_list.pack(side="left", fill="x", expand=True)
        self.drop_decode_batch = self._drop_area(batch, "Arrastra aquí varios vídeos para recuperarlos")
        self._field(batch, "Carpeta de recuperación del lote (vacío = junto al vídeo)",
                    self.decode_batch_folder, folder_select=True)
        self.decode_batch_count = tk.StringVar(value="0 vídeos seleccionados")
        ttk.Label(batch, textvariable=self.decode_batch_count,
                  style="Subtitle.TLabel").pack(anchor="w", pady=(0, 5))
        self.start_decode_batch = ttk.Button(batch, text="Recuperar lote",
                                             style="Accent.TButton", command=self._start_decode_batch)
        self.start_decode_batch.pack(anchor="w", pady=(0, 10))

        # Información de los parámetros: consulta local, sin cargar enlaces.
        self._build_info(info)

        self.activity_panel = ttk.Frame(root)
        self.activity_panel.pack(fill="x", pady=(10, 0))
        ttk.Label(self.activity_panel, text="Progreso de la operación actual", style="Section.TLabel").pack(anchor="w", pady=(0, 5))
        self.progress_value = tk.DoubleVar(value=0)
        ttk.Progressbar(self.activity_panel, variable=self.progress_value, maximum=100).pack(fill="x")
        self.percent = tk.StringVar(value="0 %")
        self.status = tk.StringVar(value="Preparado.")
        activity_line = ttk.Frame(self.activity_panel)
        activity_line.pack(fill="x", pady=(4, 5))
        ttk.Label(activity_line, textvariable=self.status, style="Subtitle.TLabel", wraplength=620).pack(side="left")
        ttk.Label(activity_line, textvariable=self.percent, style="Subtitle.TLabel").pack(side="right")

        self.footer = ttk.Frame(root)
        self.footer.pack(fill="x", pady=(8, 0))
        self.stop_button = ttk.Button(self.footer, text="Cancelar operación", command=self._cancel,
                                      state="disabled")
        self.stop_button.pack(side="right")
        # Barra de botones y progreso visibles; formulario desplazable encima.
        self.tabs.pack_forget()
        self.activity_panel.pack_forget()
        self.footer.pack_forget()
        self.footer.pack(side="bottom", fill="x", pady=(8, 0))
        self.activity_panel.pack(side="bottom", fill="x", pady=(10, 0))
        self.tabs.pack(fill="both", expand=True)
        self.source_file.trace_add("write", lambda *_: self._source_changed())
        self.restore_video.trace_add("write", lambda *_: self._restore_changed())

    def _source_changed(self):
        value = self.source_file.get().strip()
        if value and (not self.video_dest.get() or self.video_dest.get() == self._autofilled_video_dest):
            source = Path(value).expanduser()
            self._autofilled_video_dest = str(source.with_name(source.name + ".mp4"))
            self.video_dest.set(self._autofilled_video_dest)

    def _restore_changed(self):
        value = self.restore_video.get().strip()
        if value:
            path = Path(value).expanduser()
            if not self.restore_folder.get() or self.restore_folder.get() == self._autofilled_restore_folder:
                self._autofilled_restore_folder = str(path.parent)
                self.restore_folder.set(self._autofilled_restore_folder)

    def _clear_session(self):
        """Vacía entradas, listas y parámetros al terminar cualquier operación.

        Tras completar el lote entero, no tras cada archivo del lote. Se ejecuta
        igualmente al fallar o cancelar la operación para minimizar datos en RAM.
        """
        self.source_file.set("")
        self.video_dest.set("")
        self.restore_video.set("")
        self.restore_folder.set("")
        self._autofilled_video_dest = ""
        self._autofilled_restore_folder = ""
        self.batch_folder.set("")
        self.decode_batch_folder.set("")
        self.batch_files.clear()
        self.decode_batch_files.clear()
        self._batch_refresh()
        self._decode_batch_refresh()
        self.resolution.set(DEFAULTS["resolution"])
        self.block_size.set(DEFAULTS["block_size"])
        self.redundancy.set(DEFAULTS["redundancy"])
        self.task_item_name = ""
        self.raw_status = "Preparado."
        self.current_task = ""
        self.progress_value.set(0)
        self.percent.set("0 %")
        self.status.set("Preparado.")

    def _drop_area(self, parent, message):
        area = ttk.Label(parent, text=message, style="Drop.TLabel", anchor="center", padding=(12, 8))
        area.pack(fill="x", pady=(0, 11))
        return area

    def _init_dnd(self):
        """TkDND nativo empaquetado por Debian/Ubuntu; nunca descarga componentes."""
        try:
            self.tk.call("package", "require", "tkdnd")
        except tk.TclError:
            for widget in (self.drop_create, self.drop_restore, self.drop_batch, self.drop_decode_batch):
                widget.configure(text="Para arrastrar archivos, instala el paquete del sistema «tkdnd». "
                                 "Mientras tanto puedes usar «Examinar».")
            return
        for widget, mode in ((self.drop_create, "create"), (self.drop_restore, "restore"),
                             (self.drop_batch, "batch"), (self.drop_decode_batch, "batch_decode"),
                             (self.batch_list, "batch"), (self.decode_batch_list, "batch_decode")):
            try:
                self._register_drop(widget, mode)
            except tk.TclError:
                widget.configure(text="Arrastrar no disponible aquí; utiliza «Examinar».")
                continue
            self.dnd_ready = True

    def _register_drop(self, widget, mode):
        callback = widget.register(lambda raw, target=mode: self._handle_drop(target, raw))
        self._drop_targets.append(callback)
        self.tk.call("tkdnd::drop_target", "register", widget._w, "DND_Files")
        self.tk.call("bind", widget._w, "<<Drop:DND_Files>>", f"{callback} %D")

    def _handle_drop(self, mode, raw):
        if self.running:
            return "refuse_drop"
        # TkDND entrega una lista Tcl, no una cadena separada por espacios.
        try:
            names = self.tk.splitlist(raw)
        except tk.TclError:
            return "refuse_drop"
        files = [str(Path(name)) for name in names if Path(name).is_file()]
        if not files:
            return "refuse_drop"
        if mode == "create":
            if len(files) != 1:
                messagebox.showwarning("Arrastrar", "Arrastra solo un archivo aquí; para varios usa Lotes.")
                return "refuse_drop"
            self.source_file.set(files[0])
        elif mode == "restore":
            if len(files) != 1:
                messagebox.showwarning("Arrastrar", "Arrastra solo un vídeo aquí; para varios usa Lotes.")
                return "refuse_drop"
            self.restore_video.set(files[0])
        elif mode == "batch":
            self.batch_files.extend(name for name in files if name not in self.batch_files)
            self._batch_refresh()
        else:
            self.decode_batch_files.extend(name for name in files if name not in self.decode_batch_files)
            self._decode_batch_refresh()
        return "copy"

    def _build_info(self, parent):
        """Explicación breve de los tres parámetros configurables."""
        content = (
            ("Resolución", "1280×720: menor carga de procesamiento. "
             "1920×1080: más datos por fotograma y vídeos potencialmente más cortos."),
            ("Bloque de píxeles", "8: vídeo más corto. 12: opción intermedia. "
             "16: más duración, pero puede tolerar mejor alteraciones del vídeo."),
            ("Copias", "1: menor duración. 2 o 3: mayor duración y más posibilidades "
             "de recuperación si se pierden fotogramas."),
        )
        for header, explanation in content:
            ttk.Label(parent, text=header, style="Section.TLabel").pack(anchor="w", pady=(0, 4))
            ttk.Label(parent, text=explanation, wraplength=650, justify="left").pack(
                anchor="w", fill="x", pady=(0, 14))

    def _batch_add(self):
        values = filedialog.askopenfilenames(title="Selecciona los archivos para convertir")
        for path in values:
            if path not in self.batch_files:
                self.batch_files.append(path)
        self._batch_refresh()

    def _batch_remove(self):
        remove = set(self.batch_list.curselection())
        self.batch_files = [item for index, item in enumerate(self.batch_files) if index not in remove]
        self._batch_refresh()

    def _batch_clear(self):
        self.batch_files.clear()
        self._batch_refresh()

    def _batch_refresh(self):
        self.batch_list.delete(0, "end")
        for filename in self.batch_files:
            self.batch_list.insert("end", Path(filename).name)
        self.batch_count.set(f"{len(self.batch_files)} archivos seleccionados")

    def _start_batch(self):
        try:
            jobs = prepare_jobs(list(self.batch_files), self.batch_folder.get())
            width, height = map(int, self.resolution.get().split("x"))
            block, copies = int(self.block_size.get()), int(self.redundancy.get())
        except (ISGError, ValueError) as exc:
            messagebox.showwarning("Lotes", str(exc))
            return
        def action(callback):
            return execute_jobs(jobs, width=width, height=height, block=block, copies=copies,
                                cancel=self.cancel_event, progress=callback,
                                item_done=lambda src, dest, success, msg:
                                self.events.put(("batch_item", str(src), str(dest), success, msg)))
        self._start_task(f"Convirtiendo lote de {len(jobs)} archivos…", action, "batch",
                         item_name=f"{len(jobs)} archivos")

    def _decode_batch_add(self):
        values = filedialog.askopenfilenames(title="Selecciona los vídeos para recuperar")
        for path in values:
            if path not in self.decode_batch_files:
                self.decode_batch_files.append(path)
        self._decode_batch_refresh()

    def _decode_batch_remove(self):
        remove = set(self.decode_batch_list.curselection())
        self.decode_batch_files = [item for index, item in enumerate(self.decode_batch_files)
                                   if index not in remove]
        self._decode_batch_refresh()

    def _decode_batch_clear(self):
        self.decode_batch_files.clear()
        self._decode_batch_refresh()

    def _decode_batch_refresh(self):
        self.decode_batch_list.delete(0, "end")
        for filename in self.decode_batch_files:
            self.decode_batch_list.insert("end", Path(filename).name)
        self.decode_batch_count.set(f"{len(self.decode_batch_files)} vídeos seleccionados")

    def _start_decode_batch(self):
        try:
            jobs = prepare_decode_jobs(list(self.decode_batch_files), self.decode_batch_folder.get())
        except ISGError as exc:
            messagebox.showwarning("Recuperación por lotes", str(exc))
            return
        def action(callback):
            return execute_decode_jobs(jobs, cancel=self.cancel_event, progress=callback,
                item_done=lambda src, dest, success, msg:
                self.events.put(("batch_item", str(src), str(dest), success, msg)))
        self._start_task(f"Recuperando lote de {len(jobs)} vídeos…", action,
                         "batch_decode", item_name=f"{len(jobs)} vídeos")

    def _field(self, parent, title, var, *, file_select=False, file_save=False,
               folder_select=False, file_types=None):
        ttk.Label(parent, text=title, style="Section.TLabel").pack(anchor="w", pady=(0, 4))
        field = ttk.Frame(parent)
        field.pack(fill="x", pady=(0, 12))
        ttk.Entry(field, textvariable=var).pack(side="left", fill="x", expand=True)

        def browse():
            current = Path(var.get()).expanduser() if var.get() else INITIAL_DIR
            initial = current if current.is_dir() else current.parent
            kwargs = {"initialdir": str(initial)}
            if file_select:
                value = filedialog.askopenfilename(filetypes=file_types or [("Todos", "*")], **kwargs)
            elif file_save:
                value = filedialog.asksaveasfilename(defaultextension=".mp4",
                                                     filetypes=[("Todos los archivos", "*")], **kwargs)
            else:
                value = filedialog.askdirectory(**kwargs)
            if value:
                var.set(value)

        ttk.Button(field, text="Examinar…", command=browse).pack(side="left", padx=(8, 0))

    def _update_estimate(self):
        source = Path(self.source_file.get()).expanduser()
        if not source.is_file():
            self.estimate.set("Selecciona un archivo para estimar la duración del vídeo.")
            return
        try:
            width, height = map(int, self.resolution.get().split("x"))
            info = estimate_encode(str(source), width, height, int(self.block_size.get()),
                                   int(self.redundancy.get()))
            self.estimate.set(
                "Duración estimada del vídeo: " + readable_time(info["video_seconds"]) + "\n"
                "Tiempo estimado de procesamiento: se calculará durante la creación"
            )
        except (ISGError, OSError, ValueError) as exc:
            self.estimate.set(f"No se puede calcular la duración: {exc}")

    def _show(self, message):
        """Solo estado de la operación en curso; no se almacena un registro."""
        self.status.set(message)

    def _start_task(self, name, target, task_type="unknown", item_name=""):
        if self.running:
            return
        self.running = True
        self.current_task = task_type
        self.task_item_name = item_name
        self.started = time.monotonic()
        self.last_progress = 0.0
        self.cancel_event.clear()
        self.progress_value.set(0)
        self.percent.set("0 %")
        self.status.set(name)
        self._show("▶ " + name)
        for control in (self.start_enc, self.start_dec,
                        self.start_batch, self.batch_add, self.batch_remove, self.batch_clear,
                        self.start_decode_batch, self.batch_decode_add,
                        self.batch_decode_remove, self.batch_decode_clear):
            control.configure(state="disabled")
        self.stop_button.configure(state="normal")

        def worker():
            try:
                # Limitar eventos al hilo gráfico para archivos de muchos bloques.
                last = [0.0]
                def report(value, message):
                    now = time.monotonic()
                    if now - last[0] >= 0.12 or value >= 1.0:
                        last[0] = now
                        self.events.put(("progress", value, message))
                result = target(report)
                self.events.put(("ok", result))
            except (ISGError, OSError, ValueError) as exc:
                self.events.put(("error", str(exc)))
            except Exception as exc:
                self.events.put(("error", f"Error inesperado ({type(exc).__name__}): {exc}"))

        threading.Thread(target=worker, name="isg-worker", daemon=True).start()

    def _start_encode(self):
        source, output = self.source_file.get().strip(), self.video_dest.get().strip()
        if not source or not output:
            messagebox.showwarning("Datos incompletos", "Selecciona un archivo de entrada y el vídeo de salida.")
            return
        width, height = map(int, self.resolution.get().split("x"))
        block, copies = int(self.block_size.get()), int(self.redundancy.get())
        self._start_task("Generando vídeo…", lambda cb: encode(
            source, output, width, height, block, copies, self.cancel_event, cb), "encode",
            item_name=Path(source).name)

    def _start_decode(self):
        source, target = self.restore_video.get().strip(), self.restore_folder.get().strip()
        if not source or not target:
            messagebox.showwarning("Datos incompletos", "Selecciona el vídeo y la carpeta de destino.")
            return
        self._start_task("Recuperando archivo…", lambda cb: decode(
            source, target, self.cancel_event, cb), "decode",
            item_name=Path(source).name)

    def _cancel(self):
        if self.running:
            self.cancel_event.set()
            self.stop_button.configure(state="disabled")
            self.status.set("Cancelación solicitada; terminando la operación…")
            self._show("Solicitada cancelación.")

    def _on_close(self):
        if not self.running:
            self.destroy()
            return
        if messagebox.askyesno("Operación en curso", "¿Cancelar la operación y cerrar cuando finalice?"):
            self.close_on_completion = True
            self._cancel()

    def _read_events(self):
        try:
            while True:
                event = self.events.get_nowait()
                kind = event[0]
                if kind == "progress":
                    progress = min(max(float(event[1]), 0.0), 1.0)
                    self.last_progress = progress
                    self.raw_status = event[2]
                    self.progress_value.set(progress * 100)
                    self.percent.set(f"{progress * 100:.1f} %")
                    elapsed = time.monotonic() - self.started
                    eta = (elapsed * (1 - progress) / progress) if 0.1 <= progress < 1 else 0
                    suffix = f" · aprox. {readable_time(eta)} restantes" if eta >= 3 else ""
                    self.status.set(self.raw_status + suffix)
                    # Estimación calculada con el progreso real, solo en RAM y
                    # únicamente mientras se crea el vídeo individual.
                    if self.current_task == "encode" and 0.10 <= progress < 1:
                        video_line = self.estimate.get().split("\n", 1)[0]
                        self.estimate.set(video_line + "\nTiempo estimado de procesamiento: "
                                          + readable_time(elapsed / progress) + " en total")
                elif kind == "log":
                    self._show(event[1])
                elif kind == "batch_item":
                    _, source, destination, success, detail = event
                    self._show(("✔ " if success else "✖ ") + Path(source).name + ": " + detail)
                elif kind in ("ok", "error"):
                    success = kind == "ok"
                    result = event[1]
                    if isinstance(result, dict) and self.current_task in {"batch", "batch_decode"}:
                        summary = (f"Lote terminado: {result['succeeded']} correctos y "
                                   f"{result['failed']} fallidos de {result['total']} archivos.")
                    else:
                        summary = str(result)
                    self._show(("✔ " if success else "✖ ") + summary)
                    partial = (success and self.current_task in {"batch", "batch_decode"} and
                               isinstance(result, dict) and result.get("failed", 0) > 0)
                    self.status.set("Lote finalizado con incidencias." if partial else
                                    ("Operación completada." if success else "Error: " + summary))
                    self.running = False
                    self.stop_button.configure(state="disabled")
                    for control in (self.start_enc, self.start_dec,
                                    self.start_batch, self.batch_add, self.batch_remove, self.batch_clear,
                                    self.start_decode_batch, self.batch_decode_add,
                                    self.batch_decode_remove, self.batch_decode_clear):
                        control.configure(state="normal")
                    if success:
                        self.progress_value.set(100)
                        self.percent.set("100 %")
                    if self.close_on_completion:
                        self._clear_session()
                        self.destroy()
                        return
                    if partial:
                        messagebox.showwarning("ISG Desktop", summary)
                    elif success:
                        messagebox.showinfo("ISG Desktop", summary)
                    elif "cancelada" not in summary.lower():
                        messagebox.showerror("ISG Desktop", summary)
                    self._clear_session()
        except queue.Empty:
            pass
        self.after(100, self._read_events)


if __name__ == "__main__":
    try:
        App().mainloop()
    except tk.TclError as exc:
        print("No se puede abrir el entorno gráfico:", exc)
        raise SystemExit(1)
