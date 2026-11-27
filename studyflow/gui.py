"""Віконний інтерфейс StudyFlow на Tkinter/ttk."""
import sqlite3
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, simpledialog, ttk

from .core import DATE_FORMAT
from .gui_controller import PlannerController


class TaskDialog(simpledialog.Dialog):
    """Модальна форма створення навчального завдання."""

    def body(self, master):
        self.fields = []
        for row, label in enumerate(("Предмет", "Назва завдання", "Дедлайн (YYYY-MM-DD HH:MM)")):
            ttk.Label(master, text=label).grid(row=row, column=0, sticky="w", padx=8, pady=6)
            entry = ttk.Entry(master, width=38)
            entry.grid(row=row, column=1, sticky="ew", padx=8, pady=6)
            self.fields.append(entry)
        self.fields[2].insert(0, datetime.now().strftime(DATE_FORMAT))
        return self.fields[0]

    def validate(self):
        from .core import TaskService
        values = [field.get().strip() for field in self.fields]
        try:
            if not values[0] or not values[1]:
                raise ValueError("Заповніть предмет і назву")
            TaskService.validate_deadline(values[2])
        except ValueError as exc:
            messagebox.showerror("Некоректні дані", str(exc), parent=self)
            return False
        return True

    def apply(self):
        self.result = tuple(field.get().strip() for field in self.fields)


class StudyFlowWindow(ttk.Frame):
    """View: компоненти вікна та обробники подій."""
    MODES = {"Усі": "all", "Активні": "active", "Виконані": "completed"}
    PERIODS = {"Усі дати": "all", "Сьогодні": "today", "7 днів": "week"}

    def __init__(self, root: tk.Tk, controller: PlannerController,
                 mode: str = "all"):
        super().__init__(root, padding=20)
        self.root = root
        self.controller = controller
        self.rows = {}
        root.title("StudyFlow — планувальник навчальних завдань")
        root.geometry("1050x680")
        root.minsize(820, 530)
        self.pack(fill="both", expand=True)

        style = ttk.Style(root)
        style.configure("Heading.TLabel", font=("Segoe UI", 20, "bold"))
        style.configure("Summary.TLabel", font=("Segoe UI", 11))
        style.configure("Treeview", rowheight=29)
        self.mode = tk.StringVar(value=next(
            key for key, value in self.MODES.items() if value == mode))
        self.period = tk.StringVar(value="Усі дати")
        self.search = tk.StringVar()
        self.summary = tk.StringVar()
        self.status = tk.StringVar(value="Готово до роботи")
        self._build()
        self.refresh()

    def _build(self):
        ttk.Label(self, text="StudyFlow", style="Heading.TLabel").pack(anchor="w")
        ttk.Label(self, text="Навчальний планувальник  •  Трасковський Богдан").pack(anchor="w", pady=(0, 16))

        dashboard = ttk.LabelFrame(self, text="Загальний прогрес", padding=10)
        dashboard.pack(fill="x", pady=(0, 12))
        ttk.Label(dashboard, textvariable=self.summary, style="Summary.TLabel").pack(anchor="w")
        self.progress = ttk.Progressbar(dashboard, maximum=100, mode="determinate")
        self.progress.pack(fill="x", pady=(7, 0))

        filters = ttk.Frame(self)
        filters.pack(fill="x", pady=(0, 10))
        ttk.Label(filters, text="Статус:").pack(side="left")
        modes = ttk.Combobox(filters, textvariable=self.mode, values=list(self.MODES),
                             state="readonly", width=13)
        modes.pack(side="left", padx=(5, 12))
        ttk.Label(filters, text="Період:").pack(side="left")
        periods = ttk.Combobox(filters, textvariable=self.period, values=list(self.PERIODS),
                               state="readonly", width=13)
        periods.pack(side="left", padx=(5, 12))
        ttk.Label(filters, text="Пошук:").pack(side="left")
        ttk.Entry(filters, textvariable=self.search).pack(side="left", fill="x", expand=True, padx=5)
        ttk.Button(filters, text="Оновити", command=self.refresh).pack(side="left", padx=(7, 0))
        modes.bind("<<ComboboxSelected>>", lambda event: self.refresh())
        periods.bind("<<ComboboxSelected>>", lambda event: self.refresh())
        self.search.trace_add("write", lambda *_: self.refresh())

        table = ttk.Frame(self)
        table.pack(fill="both", expand=True)
        table.columnconfigure(0, weight=1)
        table.rowconfigure(0, weight=1)
        columns = ("id", "subject", "title", "deadline", "status")
        self.tree = ttk.Treeview(table, columns=columns, show="headings", selectmode="browse")
        for key, title, width, stretch in (
            ("id", "ID", 55, False), ("subject", "Предмет", 160, True),
            ("title", "Завдання", 300, True), ("deadline", "Дедлайн", 155, False),
            ("status", "Статус", 125, False),
        ):
            self.tree.heading(key, text=title)
            self.tree.column(key, width=width, minwidth=45, stretch=stretch,
                             anchor="center" if key == "id" else "w")
        self.tree.grid(row=0, column=0, sticky="nsew")
        scrollbar = ttk.Scrollbar(table, orient="vertical", command=self.tree.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar.set)
        self.tree.tag_configure("Прострочено", foreground="#b42318")
        self.tree.tag_configure("Терміново", foreground="#9a6700")
        self.tree.tag_configure("Виконано", foreground="#18794e")
        self.tree.bind("<Double-1>", lambda event: self.edit())

        actions = ttk.Frame(self)
        actions.pack(fill="x", pady=(12, 6))
        for label, callback in (("Додати", self.add), ("Виконано", self.complete),
                                ("Змінити дедлайн", self.edit), ("Видалити", self.delete)):
            ttk.Button(actions, text=label, command=callback).pack(side="left", padx=(0, 6))

        files = ttk.Frame(self)
        files.pack(fill="x", pady=(0, 10))
        ttk.Button(files, text="Зберегти копію JSON", command=self.save).pack(side="left", padx=(0, 6))
        ttk.Button(files, text="Відновити з JSON", command=self.load).pack(side="left")
        ttk.Button(files, text="Вихід", command=self.root.destroy).pack(side="right")
        ttk.Separator(self).pack(fill="x", pady=(0, 8))
        ttk.Label(self, textvariable=self.status).pack(anchor="w")

    def refresh(self):
        try:
            dashboard = self.controller.dashboard(
                self.MODES[self.mode.get()], self.PERIODS[self.period.get()],
                self.search.get())
        except (ValueError, sqlite3.Error) as exc:
            messagebox.showerror("Помилка", str(exc), parent=self.root)
            return
        selection = self.tree.selection()
        previous = selection[0] if selection else None
        for item in self.tree.get_children():
            self.tree.delete(item)
        self.rows = {str(row.id): row for row in dashboard.rows}
        for row in dashboard.rows:
            self.tree.insert("", "end", iid=str(row.id), values=(
                row.id, row.subject, row.title, row.deadline, row.status),
                tags=(row.status,))
        if previous in self.rows:
            self.tree.selection_set(previous)
            self.tree.focus(previous)
        report = dashboard.progress
        self.summary.set(f"Усього: {report.total}   |   Виконано: {report.completed}   |   "
                         f"Прострочено: {report.overdue}   |   Терміново: {report.urgent}   |   "
                         f"Прогрес: {report.completion_percent:g}%")
        self.progress["value"] = report.completion_percent
        self.status.set(f"Показано завдань: {len(dashboard.rows)}")

    def selected(self):
        selection = self.tree.selection()
        if not selection:
            messagebox.showinfo("StudyFlow", "Оберіть завдання у списку", parent=self.root)
            return None
        return self.rows[selection[0]]

    def perform(self, action, success):
        try:
            action()
        except (ValueError, OSError, sqlite3.Error) as exc:
            messagebox.showerror("Помилка", str(exc), parent=self.root)
            return
        self.refresh()
        self.status.set(success)

    def add(self):
        dialog = TaskDialog(self.root, title="Нове завдання")
        if dialog.result is not None:
            self.perform(lambda: self.controller.add(*dialog.result), "Завдання додано")

    def complete(self):
        row = self.selected()
        if row:
            self.perform(lambda: self.controller.complete(row.id), "Завдання виконано")

    def edit(self):
        row = self.selected()
        if row:
            value = simpledialog.askstring("Змінити дедлайн", "YYYY-MM-DD HH:MM",
                                           initialvalue=row.deadline, parent=self.root)
            if value is not None:
                self.perform(lambda: self.controller.edit_deadline(row.id, value),
                             "Дедлайн оновлено")

    def delete(self):
        row = self.selected()
        if row and messagebox.askyesno("Видалення", f"Видалити завдання №{row.id}?",
                                      parent=self.root):
            self.perform(lambda: self.controller.delete(row.id), "Завдання видалено")

    def save(self):
        path = filedialog.asksaveasfilename(parent=self.root, defaultextension=".json",
                                           filetypes=[("JSON", "*.json")],
                                           initialfile="studyflow.snapshot.json")
        if path:
            self.perform(lambda: self.controller.save(path), "Резервну копію збережено")

    def load(self):
        path = filedialog.askopenfilename(parent=self.root, filetypes=[("JSON", "*.json")])
        if path and messagebox.askyesno(
                "Відновлення", "Замінити всі поточні завдання даними з копії?",
                parent=self.root):
            self.perform(lambda: self.controller.load(path, confirmed=True),
                         "Дані відновлено")


def run_gui(controller: PlannerController, mode="all"):
    root = tk.Tk()
    StudyFlowWindow(root, controller, mode)
    root.mainloop()
