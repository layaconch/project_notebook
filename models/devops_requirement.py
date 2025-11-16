from odoo import fields, models


class DevOpsRequirement(models.Model):
    _name = "devops.requirement"
    _description = "DevOps Requirement"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "priority desc, deadline"

    name = fields.Char(required=True, tracking=True)
    description = fields.Text()
    requester_id = fields.Many2one("res.users", string="Requester", tracking=True)
    owner_id = fields.Many2one(
        "res.users", string="Owner", default=lambda self: self.env.user, tracking=True
    )
    priority = fields.Selection(
        [
            ("0", "Low"),
            ("1", "Normal"),
            ("2", "High"),
            ("3", "Critical"),
        ],
        default="1",
        tracking=True,
    )
    deadline = fields.Date(tracking=True)
    tag_ids = fields.Many2many("res.partner.category", string="Tags")
    requirement_type = fields.Selection(
        [
            ("feature", "Feature"),
            ("improvement", "Improvement"),
            ("bugfix", "Bug Fix"),
            ("research", "Research"),
        ],
        default="feature",
        tracking=True,
    )
    state = fields.Selection(
        [
            ("draft", "Draft"),
            ("approved", "Approved"),
            ("in_progress", "In Progress"),
            ("done", "Delivered"),
        ],
        default="draft",
        tracking=True,
    )
    issue_ids = fields.One2many(
        "devops.issue", "requirement_id", string="Related Issues"
    )

    def action_start(self):
        self.write({"state": "in_progress"})

    def action_done(self):
        self.write({"state": "done"})

    def action_approve(self):
        self.write({"state": "approved"})
