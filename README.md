# Mail Triage App

`mail_triage_app` est une application Streamlit qui se connecte à Gmail via OAuth pour analyser les 14 derniers jours de votre boîte de réception, prioriser les messages et générer des brouillons de réponse. Le dépôt contient également l'ancien script `task_dashboard.py` présenté dans la documentation précédente.

## Fonctionnalités principales

- Authentification OAuth (lecture + création de brouillons) via `credentials.json` / `token.json`.
- Récupération des messages de l'INBOX sur les 14 derniers jours avec sujet, expéditeur, date, extrait, libellés, statut non lu, taille du fil.
- Score de priorité (0–100) transparent :
  - +25 non lu ; +15 expéditeur humain ; +10 question/action ; +10 fil Re: > 2 ; +15 important/étoilé ; +10 <48 h ; −10 seulement en copie ; −20 newsletter.
- Interface Streamlit avec filtres (dates, non lus, score mini, recherche, tri), cartes interactives, marquage « must reply » local, mode bulk pour générer les réponses des N meilleurs courriels.
- Génération de réponse : via OpenAI (si `OPENAI_API_KEY`) ou modèle de règles ; édition directe dans un champ texte.
- Bouton « Enregistrer en brouillon Gmail » (si la portée `gmail.compose` est active) — jamais d'envoi automatique.
- Gestion robuste des erreurs (absence d'Internet, token expiré, boîte vide) et journalisation dans `logs/mail_triage.log`.

## Installation

1. **Cloner et préparer l'environnement**
   ```bash
   git clone <ce dépôt>
   cd JM-Trial
   python -m venv .venv
   source .venv/bin/activate  # ou Scripts\\activate sous Windows
   pip install -r requirements.txt
   ```

2. **Configurer le projet Google Cloud**
   - Créez un projet sur [console.cloud.google.com](https://console.cloud.google.com/).
   - Activez l'API Gmail.
   - Créez des identifiants **OAuth client ID** (type « Application de bureau ») et téléchargez le fichier `credentials.json` placé à la racine du dépôt.
   - Lors du premier lancement, l'application ouvrira un navigateur pour autoriser les scopes :
     - `https://www.googleapis.com/auth/gmail.readonly`
     - `https://www.googleapis.com/auth/gmail.compose`
   - Le token actualisé sera stocké dans `token.json` (ne pas committer).

3. **(Optionnel) Activer OpenAI**
   - Exportez votre clé : `export OPENAI_API_KEY="sk-..."` (ou équivalent Windows).
   - Sans clé, l'application utilisera le modèle de réponse basé sur des règles.

## Utilisation

1. Lancez l'app Streamlit :
   ```bash
   streamlit run app.py
   ```
2. Dans la barre latérale :
   - Rafraîchissez les messages.
   - Ajustez la plage de dates, les filtres non lus / score / recherche et l'ordre de tri.
3. Sur chaque carte :
   - Ouvrez l'e-mail complet, marquez-le comme « must reply ».
   - Générez un brouillon de réponse (OpenAI ou règles) puis éditez le texte.
   - Enregistrez en brouillon Gmail si la portée `gmail.compose` est active.
4. Utilisez le **mode bulk** pour créer rapidement des suggestions sur les N e-mails les mieux notés.

Les journaux détaillés se trouvent dans `logs/mail_triage.log` pour faciliter le diagnostic.

## Autres scripts

- `task_dashboard.py` : tableau de bord terminal décrit dans la précédente version du README. Il reste disponible et inchangé.

## Dépannage

- **`credentials.json` manquant** : recréez les identifiants OAuth comme décrit ci-dessus.
- **Erreur de scopes lors de l'enregistrement d'un brouillon** : assurez-vous que `gmail.compose` est présent dans la liste des scopes et relancez l'authentification (supprimez `token.json`).
- **Pas d'e-mails** : vérifiez que des messages sont présents dans l'INBOX sur les 14 derniers jours ou ajustez les filtres de date.
