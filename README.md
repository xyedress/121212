# StudyFlow — практичне заняття № 13

**Виконав: Трасковський Богдан.**

Консольний планувальник навчальних завдань (тема 3). Python 3.10+, SQLite, без сторонніх залежностей.

## Запуск

```sh
python main.py
python main.py --mode active
python -m unittest discover -s tests -v
```

На Windows замість `python` можна використати `py`. Дані зберігаються локально у `studyflow.db`. Опція `--db` дозволяє вибрати інший файл бази.

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
delete 1
exit
```

Команда `add` без аргументів відкриває діалог. Доступні режими `all`, `active`, `completed`. Дати та час — локальні.

Архітектура та реалізація консольного інтерфейсу: [DESIGN.md](DESIGN.md).
