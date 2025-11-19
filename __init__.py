from . import models
from odoo import api, SUPERUSER_ID


def post_init_hook(cr, registry):
    env = api.Environment(cr, SUPERUSER_ID, {})
    env["devops.notebook.schedule"].sudo()._migrate_seconds_to_minutes()
