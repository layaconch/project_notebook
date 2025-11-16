from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    devops_default_data_source_id = fields.Many2one(
        "devops.data.source",
        string="Default DevOps Data Source",
        store=False,
        config_parameter="devops.default_data_source_id",
    )
