from odoo import fields, models
from odoo.tools.safe_eval import safe_eval


class ProjectProject(models.Model):
    _inherit = "project.project"

    notebook_count = fields.Integer(compute="_compute_notebook_count")

    def _compute_notebook_count(self):
        counts = {
            rec["project_id"][0]: rec["project_id_count"]
            for rec in self.env["devops.notebook"].read_group(
                [("project_id", "in", self.ids)],
                ["project_id"],
                ["project_id"],
            )
        }
        for project in self:
            project.notebook_count = counts.get(project.id, 0)

    def action_open_notebooks(self):
        self.ensure_one()
        action = self.env.ref("project_notebook.action_devops_notebook").read()[0]
        action["domain"] = [("project_id", "=", self.id)]
        raw_ctx = action.get("context") or {}
        ctx = {}
        if isinstance(raw_ctx, str):
            try:
                ctx = safe_eval(raw_ctx, {"uid": self.env.uid})
            except Exception:
                ctx = {}
        else:
            ctx = dict(raw_ctx)
        ctx.update(
            {
                "default_project_id": self.id,
                "search_default_project_id": self.id,
            }
        )
        action["context"] = ctx
        return action
