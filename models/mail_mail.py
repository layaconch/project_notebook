from odoo import fields, models


class MailMail(models.Model):
    _inherit = "mail.mail"

    devops_run_ids = fields.Many2many(
        "devops.notebook.run",
        "devops_run_mail_rel",
        "mail_id",
        "run_id",
        string="DevOps Runs",
        help="Notebook runs that sent this mail.",
        readonly=True,
    )
