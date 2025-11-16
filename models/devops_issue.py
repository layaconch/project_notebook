from odoo import fields, models


class DevOpsIssue(models.Model):
    _name = "devops.issue"
    _description = "DevOps Issue"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "priority desc, create_date desc"

    name = fields.Char(required=True, tracking=True)
    requirement_id = fields.Many2one(
        "devops.requirement", string="Requirement", ondelete="set null"
    )
    owner_id = fields.Many2one(
        "res.users", string="Owner", default=lambda self: self.env.user, tracking=True
    )
    reporter_id = fields.Many2one("res.users", string="Reporter")
    priority = fields.Selection(
        [
            ("0", "Low"),
            ("1", "Medium"),
            ("2", "High"),
            ("3", "Blocker"),
        ],
        default="1",
        tracking=True,
    )
    severity = fields.Selection(
        [
            ("minor", "Minor"),
            ("major", "Major"),
            ("critical", "Critical"),
        ],
        default="major",
    )
    status = fields.Selection(
        [
            ("open", "Open"),
            ("in_progress", "In Progress"),
            ("resolved", "Resolved"),
            ("closed", "Closed"),
        ],
        default="open",
        tracking=True,
    )
    reproduction_steps = fields.Html()
    resolution = fields.Html()
    deadline = fields.Date()

    def action_progress(self):
        self.write({"status": "in_progress"})

    def action_resolve(self):
        self.write({"status": "resolved"})

    def action_close(self):
        self.write({"status": "closed"})
