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

    devops_mail_from_address = fields.Char(
        string="DevOps Mail From",
        config_parameter="devops.mail_from_address",
        help="通过 /mail/api/send_mail 发送邮件时默认使用的发件地址，应与外发服务器登录账号一致。",
    )

    devops_mail_smtp_host = fields.Char(
        string="SMTP 服务器",
        config_parameter="devops.mail_smtp_host",
        help="DevOps 邮件发送专用的 SMTP 主机名或 IP。",
    )
    devops_mail_smtp_port = fields.Integer(
        string="端口",
        config_parameter="devops.mail_smtp_port",
        help="SMTP 端口，留空将使用默认 25/465/587。",
    )
    devops_mail_smtp_user = fields.Char(
        string="SMTP 用户",
        config_parameter="devops.mail_smtp_user",
        help="SMTP 登录用户名（通常与发件邮箱相同）。",
    )
    devops_mail_smtp_password = fields.Char(
        string="SMTP 密码",
        config_parameter="devops.mail_smtp_password",
        help="SMTP 登录密码/授权码，仅保存在系统参数中。",
    )
    devops_mail_smtp_use_ssl = fields.Boolean(
        string="SSL",
        config_parameter="devops.mail_smtp_use_ssl",
        help="使用 SMTPS/SSL（一般端口 465）。",
    )
    devops_mail_smtp_use_tls = fields.Boolean(
        string="STARTTLS",
        config_parameter="devops.mail_smtp_use_tls",
        help="使用 STARTTLS（一般端口 587）。",
    )
    devops_mail_smtp_require_auth = fields.Boolean(
        string="启用认证",
        config_parameter="devops.mail_smtp_require_auth",
        help="勾选后才使用用户名/密码登录 SMTP；未勾选时匿名或 IP 受信任的场景。",
    )
