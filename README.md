# StudyFlow — практичні заняття № 13–17

**Виконав: Трасковський Богдан.**

Консольний і графічний планувальник навчальних завдань (тема 3). Python 3.10+, SQLite, без сторонніх залежностей.

## Готова версія для Windows (практична № 17)

Розгортання: переносний пакет (portable), без інсталятора. Після успішної збірки архів StudyFlow-Windows-x64.zip доступний у [Releases](https://github.com/xyedress/121212/releases). Розпакуйте архів і відкрийте StudyFlow.exe (GUI) або StudyFlow-CLI.exe (CLI). Для цих файлів окремий Python не потрібен. Підтримувана цільова платформа: Windows 10/11 x64. EXE не підписані; Windows може показати попередження.

### Збірка з вихідного коду

На Windows x64 встановіть Python 3.11 x64 із pip та Tcl/Tk. Відкрийте PowerShell у корені репозиторію. Виконайте:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\build.ps1
```

Сценарій встановлює PyInstaller 6.11.1, запускає модульні тести, збирає два EXE в dist, виконує перевірки запуску з тимчасовою SQLite-базою й створює release/StudyFlow-Windows-x64.zip та SHA256SUMS.txt. Потрібне інтернет-з'єднання для завантаження залежностей збірки. Встановлення PyInstaller краще проводити в окремому віртуальному середовищі. Для запуску вихідного коду PyInstaller не потрібен.

Автоматична збірка налаштована у GitHub Actions: [Windows Release](https://github.com/xyedress/121212/actions/workflows/release.yml). У разі потреби оберіть Run workflow. Реліз публікується тільки після успішного завершення збірки та перевірок. Перевірити контрольну суму ZIP можна командою Get-FileHash -Algorithm SHA256.

## Запуск

```sh
python main.py
python main.py --mode active
python main.py --gui
python -m unittest discover -s tests -v
```

На Windows замість `python` можна використати `py`. Дані автоматично зберігаються в SQLite між запусками. У Windows нова база розміщується в `%LOCALAPPDATA%/StudyFlow/studyflow.db`, у Linux — у `$XDG_DATA_HOME/studyflow/studyflow.db` або `~/.local/share/studyflow/studyflow.db`. Якщо у поточній директорії вже існує `studyflow.db`, програма використовує її. Опція `--db` дозволяє вибрати інший файл бази.

## Графічний інтерфейс

Запуск: `python main.py --gui` або `START GUI.bat` у Windows. Tkinter має бути встановлений (перевірка: `python -m tkinter`). У Linux за потреби встановіть системний пакет Tkinter для своєї версії Python.

У вікні доступні прокручувана таблиця, пошук, фільтри, загальний прогрес, створення завдання, зміна дедлайну, завершення, видалення та JSON-копії. Для відновлення і видалення потрібне підтвердження. GUI і CLI використовують ту саму базу; для демонстрації можна запустити `python main.py --gui --db demo.db`.

## Команди

```text
help
add "Математика" "Практична 5" "2026-12-05 18:00"
list
today
week
done 1
edit 1 "2026-12-06 18:00"
mode all
stats
plan
overdue
progress
save "backups/demo.snapshot.json"
load "backups/demo.snapshot.json" --replace
delete 1
exit
```

Команда `add` без аргументів відкриває діалог. Доступні режими `all`, `active`, `completed`. Дати та час — локальні.

Команда `plan` показує активні завдання за пріоритетом, `overdue` — прострочені, `progress` — статистику терміновості й відсоток виконання. Поріг терміновості — 24 години.

## Постійність інформації

`save` створює або замінює резервний JSON-знімок усіх завдань. `load` відновлює записи зі знімка, замінюючи поточний список; для цього обов'язково потрібно вказати `--replace`. Перед відновленням перевіряється весь файл; за некоректного JSON або помилки транзакції старі записи залишаються. Щоденна робота не потребує ручної команди save: всі зміни автоматично фіксуються в SQLite.

Архітектура, консольний та графічний інтерфейси, бізнес-логіка і постійність інформації: [DESIGN.md](DESIGN.md).
