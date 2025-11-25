from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    devops_default_data_source_id = fields.Many2one(
        "devops.data.source",
        string="Default DevOps Data Source",
        store=False,
        config_parameter="devops.default_data_source_id",
    )

    devops_mail_api_token = fields.Char(
        string="DevOps Mail API Token",
        config_parameter="devops.mail_api_token",
        default="devops-mail-token",
        help="用于 /mail/api/send_mail 接口的校验，不填则使用默认值。",
    )

    devops_mail_sender_user_id = fields.Many2one(
        "res.users",
        string="API Mail Sender (User)",
        config_parameter="devops.mail_sender_user_id",
        help="选择一个 Odoo 用户，使用其邮箱作为 API 发件人（email_from）。",
    )

    devops_mail_server_id = fields.Many2one(
        "ir.mail_server",
        string="API Mail Server",
        config_parameter="devops.mail_server_id",
        help="可选：指定已有的外发服务器；未指定则回退到系统默认。",
    )
