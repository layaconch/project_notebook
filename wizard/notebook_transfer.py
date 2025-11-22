import base64
import json
import time

from odoo import _, api, fields, models
from odoo.exceptions import UserError


EXPORT_VERSION = "1.0"


class NotebookExportWizard(models.TransientModel):
    _name = "devops.notebook.export.wizard"
    _description = "Export Notebook"

    data = fields.Binary(string="Export File", readonly=True)
    filename = fields.Char(readonly=True)

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)
        active_id = self.env.context.get("active_id")
        if not active_id:
            return res
        notebook = self.env["devops.notebook"].browse(active_id).exists()
        if not notebook:
            return res
        payload = {
            "version": EXPORT_VERSION,
            "exported_at": time.time(),
            "notebook": {
                "name": notebook.name,
                "description": notebook.description,
                "execution_mode": notebook.execution_mode,
            },
            "cells": [
                {
                    "sequence": cell.sequence,
                    "cell_type": cell.cell_type,
                    "input_source": cell.input_source,
                }
                for cell in notebook.cell_ids.sorted("sequence")
            ],
        }
        dump = json.dumps(payload, ensure_ascii=False, indent=2)
        res["data"] = base64.b64encode(dump.encode("utf-8"))
        res["filename"] = f"{notebook.name or 'notebook'}.hwnb"
        return res


class NotebookImportWizard(models.TransientModel):
    _name = "devops.notebook.import.wizard"
    _description = "Import Notebook"

    data_file = fields.Binary(string="Notebook File", required=True)
    filename = fields.Char()
    project_id = fields.Many2one("project.project", string="Project")
    data_source_id = fields.Many2one("devops.data.source", string="Data Source")

    def action_import(self):
        self.ensure_one()
        if not self.data_file:
            raise UserError(_("Please upload a .hwnb file."))
        try:
            content = base64.b64decode(self.data_file)
            payload = json.loads(content.decode("utf-8"))
        except Exception:
            raise UserError(_("Invalid file format. Please upload a valid .hwnb file."))

        notebook_vals = payload.get("notebook") or {}
        name = notebook_vals.get("name") or _("Imported Notebook")
        description = notebook_vals.get("description")
        execution_mode = notebook_vals.get("execution_mode", "immediate")

        default_ds = self.data_source_id
        if not default_ds and self.project_id and self.project_id.notebook_data_source_id:
            default_ds = self.project_id.notebook_data_source_id

        notebook = self.env["devops.notebook"].create(
            {
                "name": name,
                "description": description,
                "execution_mode": execution_mode,
                "project_id": self.project_id.id if self.project_id else False,
                "data_source_id": default_ds.id if default_ds else False,
            }
        )

        for cell in payload.get("cells", []):
            self.env["devops.notebook.cell"].create(
                {
                    "notebook_id": notebook.id,
                    "sequence": cell.get("sequence") or 10,
                    "cell_type": cell.get("cell_type") or "markdown",
                    "input_source": cell.get("input_source") or "",
                }
            )

        action = self.env.ref("project_notebook.action_devops_notebook").read()[0]
        action.update(
            {
                "res_id": notebook.id,
                "view_mode": "form",
                "views": [(False, "form")],
                "target": "current",
                "res_model": "devops.notebook",
            }
        )
        return action
