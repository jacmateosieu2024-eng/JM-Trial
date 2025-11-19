# Tableau de bord hebdomadaire — guide ultra détaillé

Ce dépôt ne contient qu'un script (`task_dashboard.py`) qui affiche un tableau de bord de tâches directement dans le terminal. Voici chaque étape à suivre, même si tu n'as jamais utilisé d'outil de développement auparavant.

## 1. Ouvrir le dossier dans ton interface
1. Connecte-toi à la plateforme où se trouve ce dépôt (GitHub Codespaces, Replit, machine locale, etc.).
2. Dans le panneau de gauche (explorateur de fichiers), clique sur le dossier **JM-Trial** pour voir son contenu.
3. Clique sur `task_dashboard.py` pour l'ouvrir et parcourir le code.

## 2. Lancer le script d'exemple
1. Ouvre un terminal intégré (souvent un onglet nommé *Terminal* ou *Console* en bas).
2. Assure-toi que tu es bien dans le dossier `JM-Trial`. La ligne de commande doit se terminer par quelque chose comme `JM-Trial$` ou `JM-Trial#`. Sinon, tape `cd JM-Trial` et appuie sur **Entrée**.
3. Tape la commande suivante puis appuie sur **Entrée** :
   ```bash
   python task_dashboard.py
   ```
4. Le terminal affiche aussitôt le tableau de bord de démonstration : un en-tête, un résumé de la semaine et une table par jour.

## 3. Ajouter tes propres tâches
1. Reste dans l'éditeur ouvert sur `task_dashboard.py` et descends tout en bas du fichier.
2. Repère la liste `example_tasks = [...]`.
3. Remplace ou ajoute des entrées en utilisant la même structure, par exemple :
   ```python
   Task("Lundi", "08:30-09:00", "Lecture e-mails", "Routine", 0.5, "À faire")
   ```
4. Enregistre le fichier (`Ctrl+S` ou `Cmd+S`).
5. Retourne dans le terminal et relance `python task_dashboard.py` pour voir la mise à jour.

## 4. Comprendre rapidement le résultat
- Chaque section porte le nom d'un jour où au moins une tâche est planifiée.
- Les colonnes t'indiquent le créneau horaire, le titre de la tâche, sa catégorie, la durée estimée et le statut (avec un emoji pour t'aider à identifier l'état en un coup d'œil).
- Le bloc "Total de tâches / Heures estimées / Progression" au début te donne une vue d'ensemble immédiate.

## 5. (Optionnel) Réutiliser le tableau depuis un autre script
1. Dans un nouveau fichier Python, importe les classes :
   ```python
   from task_dashboard import Task, WeeklyDashboard
   ```
2. Crée ton tableau :
   ```python
   dashboard = WeeklyDashboard("Semaine 42")
   dashboard.add_task(Task("Lundi", "09:00-10:00", "Réunion", "Projet", 1, "En cours"))
   print(dashboard.render())
   ```
3. Exécute ce nouveau fichier comme n'importe quel script Python.

En cas de doute, reprends les étapes dans l'ordre : ouvrir le fichier, éditer, enregistrer, puis relancer `python task_dashboard.py`. Répète autant de fois que nécessaire jusqu'à obtenir la semaine parfaite.
