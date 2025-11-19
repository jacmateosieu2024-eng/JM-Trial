"""Tableau de bord hebdomadaire pour suivre des tâches en console.

Le script peut être exécuté tel quel pour afficher une semaine d'exemple,
ou bien importé pour construire un tableau de bord personnalisé avec la
classe ``WeeklyDashboard``.
"""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass, field
from typing import Dict, Iterable, List


DAYS_ORDER = [
    "Lundi",
    "Mardi",
    "Mercredi",
    "Jeudi",
    "Vendredi",
    "Samedi",
    "Dimanche",
]


@dataclass
class Task:
    """Représente une tâche de la semaine."""

    day: str
    time_slot: str
    title: str
    category: str
    estimate_hours: float
    status: str = "À faire"
    notes: str = ""

    STATUS_EMOJIS: Dict[str, str] = field(
        default_factory=lambda: {
            "À faire": "📝",
            "En cours": "⏳",
            "Terminé": "✅",
            "Bloqué": "⛔",
        }
    )

    def status_badge(self) -> str:
        """Retourne une version compacte du statut avec emoji."""

        emoji = self.STATUS_EMOJIS.get(self.status, "⬜")
        return f"{emoji}  {self.status}"


class WeeklyDashboard:
    """Petit utilitaire pour suivre des tâches hebdomadaires."""

    def __init__(self, week_label: str) -> None:
        self.week_label = week_label
        self._tasks: List[Task] = []

    # --- Gestion des tâches -------------------------------------------------
    def add_task(self, task: Task) -> None:
        self._tasks.append(task)

    def add_tasks(self, tasks: Iterable[Task]) -> None:
        for task in tasks:
            self.add_task(task)

    # --- Calculs -------------------------------------------------------------
    def by_day(self) -> Dict[str, List[Task]]:
        grouped: Dict[str, List[Task]] = defaultdict(list)
        for task in self._tasks:
            grouped[task.day].append(task)
        for day in grouped:
            grouped[day].sort(key=lambda t: t.time_slot)
        return grouped

    def status_summary(self) -> Dict[str, int]:
        summary: Dict[str, int] = defaultdict(int)
        for task in self._tasks:
            summary[task.status] += 1
        return dict(summary)

    def total_hours(self) -> float:
        return sum(task.estimate_hours for task in self._tasks)

    def completion_ratio(self) -> float:
        completed = sum(1 for task in self._tasks if task.status == "Terminé")
        return completed / len(self._tasks) if self._tasks else 0.0

    # --- Rendu ---------------------------------------------------------------
    def render(self) -> str:
        sections = [self._render_header()]
        sections.append(self._render_status_overview())
        sections.append(self._render_day_tables())
        return "\n".join(sections)

    def _render_header(self) -> str:
        title = f"Tableau de bord — {self.week_label}"
        line = "=" * len(title)
        return f"{title}\n{line}\n"

    def _render_status_overview(self) -> str:
        summary = self.status_summary()
        parts = [
            f"Total de tâches : {len(self._tasks)}",
            f"Heures estimées : {self.total_hours():.1f} h",
            f"Progression : {self.completion_ratio() * 100:5.1f}%",
        ]
        for status in ("Terminé", "En cours", "À faire", "Bloqué"):
            if status in summary:
                parts.append(f"{status} : {summary[status]}")
        return "\n".join(parts) + "\n"

    def _render_day_tables(self) -> str:
        grouped = self.by_day()
        sections: List[str] = []
        for day in DAYS_ORDER:
            tasks = grouped.get(day)
            if not tasks:
                continue
            sections.append(self._render_day(day, tasks))
        return "\n".join(sections)

    def _render_day(self, day: str, tasks: List[Task]) -> str:
        headers = ["Créneau", "Tâche", "Catégorie", "Durée", "Statut"]
        rows = [
            [
                task.time_slot,
                task.title,
                task.category,
                f"{task.estimate_hours:g} h",
                task.status_badge(),
            ]
            for task in tasks
        ]
        table = format_table(headers, rows)
        return f"\n{day}\n{ '-' * len(day)}\n{table}"


def format_table(headers: List[str], rows: List[List[str]]) -> str:
    """Affiche une table alignée sans dépendance externe."""

    widths = [len(h) for h in headers]
    for row in rows:
        for idx, cell in enumerate(row):
            widths[idx] = max(widths[idx], len(cell))

    def format_row(row: List[str]) -> str:
        return " | ".join(cell.ljust(widths[idx]) for idx, cell in enumerate(row))

    sep = "-+-".join("-" * width for width in widths)
    table_lines = [format_row(headers), sep]
    table_lines.extend(format_row(row) for row in rows)
    return "\n".join(table_lines)


if __name__ == "__main__":
    example_tasks = [
        Task("Lundi", "09:00-10:30", "Planification de la semaine", "Organisation", 1.5, "Terminé"),
        Task("Lundi", "11:00-13:00", "Prototype tableau de bord", "Projet", 2, "En cours"),
        Task("Mardi", "10:00-12:00", "Atelier équipe", "Collaboration", 2, "À faire"),
        Task("Mercredi", "14:00-15:00", "Suivi client", "Relations", 1, "En cours"),
        Task("Jeudi", "09:00-11:00", "Analyse des métriques", "Projet", 2, "À faire"),
        Task("Jeudi", "15:00-16:00", "Coaching individuel", "Mentorat", 1, "Terminé"),
        Task("Vendredi", "10:00-12:00", "Bouclage sprint", "Projet", 2, "À faire"),
        Task("Vendredi", "13:00-14:00", "Rétrospective", "Organisation", 1, "À faire"),
    ]

    dashboard = WeeklyDashboard("Semaine 36")
    dashboard.add_tasks(example_tasks)
    print(dashboard.render())
