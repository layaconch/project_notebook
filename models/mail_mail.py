from odoo import api, fields, models


class MailMail(models.Model):
    _inherit = "mail.mail"

    notebook_id = fields.Many2one(
        "devops.notebook",
        string="Notebook",
        compute="_compute_notebook",
        store=False,
    )

    @api.depends("res_model", "res_id")
    def _compute_notebook(self):
        notebooks = self.env["devops.notebook"].browse()
        for mail in self:
            notebook = notebooks.browse()
            if mail.res_model == "devops.notebook" and mail.res_id:
                nb = notebooks.browse(mail.res_id).exists()
                notebook = nb if nb else notebooks.browse()
            mail.notebook_id = notebook
