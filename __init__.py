from . import models
from . import wizard
from . import controllers
from odoo import api, SUPERUSER_ID


def post_init_hook(env):
    if not isinstance(env, api.Environment):
        env = api.Environment(env.cr, SUPERUSER_ID, {})
    env["devops.notebook.schedule"].sudo()._migrate_seconds_to_minutes()
    # Convert deprecated markdown cells to richtext
    env["devops.notebook.cell"].sudo().search([("cell_type", "=", "markdown")]).write(
        {"cell_type": "richtext"}
    )
