import base64

from odoo import fields, models


class DevOpsTrainingResource(models.Model):
    _name = "devops.training.resource"
    _description = "Training Resource"
    _order = "name"

    name = fields.Char(required=True)
    resource_type = fields.Selection(
        [("ppt", "PPT"), ("doc", "Word/Doc"), ("video", "Video"), ("other", "Other")],
        string="Type",
        default="ppt",
        required=True,
    )
    course_id = fields.Many2one("devops.training.course", string="Course", ondelete="cascade")
    attachment = fields.Binary("File")
    attachment_filename = fields.Char("Filename")
    url = fields.Char("External Link")
    description = fields.Text()
    knowledge_link = fields.Char("Knowledge Link")


class DevOpsTrainingManual(models.Model):
    _name = "devops.training.manual"
    _description = "User Manual"
    _order = "name"

    name = fields.Char(required=True)
    manual_type = fields.Selection(
        [("file", "File"), ("markdown", "Markdown")], string="Type", default="file", required=True
    )
    description = fields.Text()
    attachment = fields.Binary("File")
    attachment_filename = fields.Char("Filename")
    url = fields.Char("External Link")
    body_markdown = fields.Text("Markdown Content")
    tag_ids = fields.Many2many("res.partner.category", string="Tags")


class DevOpsTrainingCourse(models.Model):
    _name = "devops.training.course"
    _description = "Training Course"
    _order = "name"

    name = fields.Char(required=True)
    tag_ids = fields.Many2many("res.partner.category", string="Tags")
    description = fields.Text()
    resource_ids = fields.One2many("devops.training.resource", "course_id", string="Resources")


class DevOpsTrainingFAQ(models.Model):
    _name = "devops.training.faq"
    _description = "Training FAQ"
    _order = "sequence, id"

    name = fields.Char("Question", required=True)
    answer = fields.Html("Answer", sanitize=True)
    tag_ids = fields.Many2many("res.partner.category", string="Tags")
    sequence = fields.Integer(default=10)
    active = fields.Boolean(default=True)
