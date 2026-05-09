# Velocity
Velocity is a streamlined project management tool designed to strip away the "bloat" of traditional enterprise software. Built with speed and clarity in mind, it provides a Kanban-style interface for teams to move from "To-Do" to "Done" without the friction.

## 💡Why Velocity?
Most project management tools today are either too simple (spreadsheets) or too complex (enterprise software with 1,000 buttons). Velocity came to mind during a late-night coding session when I realized that most teams just need three things:

- To know who is doing what.

- To know when it's due.

- To see the progress at a glance.

The goal was to create a "Jira-lite" experience, retaining the powerful organizational structure of projects and tasks, but making it fast enough to keep up with a high-velocity startup environment.

## 🧠 Methodology
Velocity is built on the Agile Kanban Methodology. It focuses on:

    1. Visual Transparency: A dedicated project board that separates tasks by status.

    2. Ownership: Every task has a creator and an assignee, ensuring no ticket is "homeless."

    3. Time-Awareness: Built-in support for timezones so that "Due by 5 PM" means the same thing to a developer in London as it does to one in New York.

    4. Collaboration: A membership-based system where project owners can invite specific users to contribute to their workspace.

## 🛠️ The Tech Stack
I chose a stack that prioritizes rapid development and stable data integrity:

- Python & Flask: The engine. Flask was chosen for its "micro" philosophy-keeping the backend lightweight and fast.

- SQLAlchemy: The brain. This manages the complex relationships between users, projects, and tasks using a structured relational database.

- SQLite: The storage. A reliable, file-based database perfect for a portable MVP.

- Pytz: The clock. Essential for handling the messy world of global timezones.

- Jinja2: The face. Dynamic HTML templates that render project data in real-time.

## Project File Structure
- instance/ # Local database storage
- templates/ # The UI (HTML/Dashboard/Project views)
- .env # Secure configuration
- app.py # The core application logic
- requirements.txt # Necessary Python libraries
## Environment Variables

To run this project, you will need to add the following environment variables to your .env file

`SECRET_KEY`