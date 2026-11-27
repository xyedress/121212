"""Інтеграційні перевірки реальних віджетів Tk (потрібен дисплей).

Запуск: python -m unittest discover -s tests -p gui_acceptance.py -v
Діалогові відповіді підмінено, щоб тест не вимагав дій користувача.
"""
import tempfile
import tkinter as tk
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch
from tkinter import ttk

from studyflow.core import TaskService
from studyflow.data import SQLiteRepository
from studyflow.gui import StudyFlowWindow
from studyflow.gui_controller import PlannerController
from studyflow.persistence import JsonSnapshotStore


class WindowAcceptance(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name)
        self.db = self.path / "data.db"
        self.repo = SQLiteRepository(str(self.db))
        self.addCleanup(self.repo.close)
        self.service = TaskService(self.repo, clock=lambda: datetime(2026, 12, 1, 12))
        self.root = tk.Tk()
        self.addCleanup(self.root.destroy)
        self.error = patch("studyflow.gui.messagebox.showerror")
        self.errors = self.error.start()
        self.addCleanup(self.error.stop)
        self.window = StudyFlowWindow(
            self.root, PlannerController(self.service, JsonSnapshotStore(self.repo)))
        self.root.update_idletasks()
        self.addCleanup(self.assert_no_errors)

    def assert_no_errors(self):
        self.errors.assert_not_called()

    def widgets(self, root):
        for child in root.winfo_children():
            yield child
            yield from self.widgets(child)

    def click(self, label):
        button = next(w for w in self.widgets(self.window)
                      if isinstance(w, ttk.Button) and w.cget("text") == label)
        button.invoke()
        self.root.update_idletasks()

    def add_task(self):
        with patch("studyflow.gui.TaskDialog") as dialog:
            dialog.return_value.result = ("Інформатика", "Фінальна робота",
                                          "2026-12-02 12:00")
            self.click("Додати")
        item, = self.window.tree.get_children()
        self.window.tree.selection_set(item)
        return item

    def test_create_search_edit_complete(self):
        item = self.add_task()
        self.assertIn("Фінальна робота", self.window.tree.item(item, "values"))
        self.window.search.set("неіснуюче")
        self.assertEqual(self.window.tree.get_children(), ())
        self.window.search.set("")
        self.window.tree.selection_set(item)
        with patch("studyflow.gui.simpledialog.askstring",
                   return_value="2026-12-04 12:00"):
            self.click("Змінити дедлайн")
        self.assertIn("2026-12-04 12:00", self.window.tree.item(item, "values"))
        self.click("Виконано")
        self.assertIn("Виконано", self.window.tree.item(item, "values"))
        self.assertEqual(float(self.window.progress["value"]), 100.0)
        self.window.mode.set("Активні")
        self.click("Оновити")
        self.assertEqual(self.window.tree.get_children(), ())
        self.window.mode.set("Виконані")
        self.click("Оновити")
        self.assertEqual(self.window.tree.get_children(), (item,))

    def test_backup_delete_restore_and_reopen(self):
        item = self.add_task()
        snapshot = str(self.path / "резерв.json")
        with patch("studyflow.gui.filedialog.asksaveasfilename", return_value=snapshot):
            self.click("Зберегти копію JSON")
        self.assertTrue(Path(snapshot).is_file())
        with patch("studyflow.gui.messagebox.askyesno", return_value=False):
            self.click("Видалити")
        self.assertEqual(self.window.tree.get_children(), (item,))
        with patch("studyflow.gui.messagebox.askyesno", return_value=True):
            self.click("Видалити")
        self.assertEqual(self.window.tree.get_children(), ())
        with patch("studyflow.gui.filedialog.askopenfilename", return_value=snapshot), \
             patch("studyflow.gui.messagebox.askyesno", return_value=True):
            self.click("Відновити з JSON")
        self.assertEqual(self.window.tree.get_children(), (item,))
        second = SQLiteRepository(str(self.db))
        try:
            self.assertEqual(second.all()[0].title, "Фінальна робота")
        finally:
            second.close()


if __name__ == "__main__":
    unittest.main()
