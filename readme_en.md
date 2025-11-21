# DevOps Operations Platform

DevOps Operations Platform is an Odoo 18 application that combines interactive notebooks, requirement/issue tracking, and user training content in a single workspace. It is designed for DevOps/SRE teams that need to run SQL/Python snippets against multiple data sources, store the outputs, and share procedures with different user groups.

## Key Features
- **Interactive notebooks** – Each notebook contains ordered cells with SQL or documentation content. Outputs are rendered with the custom `o_devops_table` layout for better readability.
- **Flexible data sources** – PostgreSQL, Oracle, SQL Server, and CSV sources are supported. PostgreSQL connections accept a per-source schema (`search_path`) so results stay in the intended namespace.
- **Execution modes & scheduling** – Notebooks can run immediately or via a dedicated schedule model. Only one active schedule is allowed per notebook, with minute-or-longer intervals enforced by cron `devops_notebook_cron`.
- **Team-oriented permissions** – Categories expose "Allowed User Groups" to control access, while public categories remain visible to everyone.
- **Training area** – Upload training courses, manuals, or links for end users under the "用户培训" (User Training) menu. Permissions separate managers and learners.
- **UI improvements** – Notebook meta information (data source, owner, stats, outline) lives in a left rail, cells occupy the right 80% area, and inputs use a light-blue theme to distinguish editable regions.
- **Developer comforts** – Notebook layout, execution widget, and training menus are tuned for DevOps workflows out of the box.

## Requirements
- Odoo 18.0 (tested with official `odoo:18.0-20251106` image)
- PostgreSQL 16.x for the main Odoo database
- Python dependencies resolved through the official image

## Installation
1. Clone this repository into your custom addons path (e.g. `/mnt/extra-addons/project_notebook`).
2. Ensure the module directory name is `project_notebook`.
3. Add the path to `odoo.conf` or set the `ODOO_ADDONS_PATH` environment variable.
4. Restart your Odoo service.
5. Update the app list and install **DevOps Operations Platform** from Apps (developer mode recommended).

## Upgrading
After updating the module code in your addons path, restart Odoo (if needed) and run:
```bash
odoo-bin -d <database_name> -u project_notebook --stop-after-init
```
This reloads models, views, cron definitions, and translations shipped with the addon.

## Usage Tips
- Configure data sources via DevOps → Settings → Data Sources; remember to set schema for PostgreSQL if you need non-public relations.
- Create notebooks from DevOps → 笔记本管理 → 笔记本. The header shows the data source so you always know where queries run.
- Use "配置执行计划" to open the schedule form; cron runs due notebooks and records execution history.
- Manage notebook categories and allowed user groups under DevOps → Settings.
- Maintain training courses/manuals under the 用户培训 menu; learners can browse content without edit rights.

## Roadmap Ideas
- Tighter integration with `document_knowledge` for richer article storage
- Optional queue_job backend for heavy notebook runs
- More translations and UX polish as new features land

Contributions and feedback are welcome!
