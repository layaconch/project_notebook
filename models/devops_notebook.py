import base64
import builtins
import contextlib
import csv
import io
import re
import time
import traceback
from io import StringIO

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools import html_escape
from odoo.tools.safe_eval import safe_eval


class DevOpsNotebookCategory(models.Model):
    _name = "devops.notebook.category"
    _description = "Notebook Category"
    _order = "name"

    name = fields.Char(required=True)
    is_public = fields.Boolean(string="Public", help="Visible and runnable by all users")
    group_ids = fields.Many2many(
        "res.groups", string="Allowed User Groups", help="Groups allowed to access."
    )


class DevOpsNotebook(models.Model):
    _name = "devops.notebook"
    _description = "DevOps Notebook"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "create_date desc"

    name = fields.Char(required=True, tracking=True)
    project_id = fields.Many2one(
        "project.project", string="Project", tracking=True, index=True
    )
    wiki_page_count = fields.Integer(
        string="Wiki Pages",
        related="project_id.document_page_count",
        readonly=True,
    )
    owner_id = fields.Many2one(
        "res.users", string="Owner", default=lambda self: self.env.user, tracking=True
    )
    description = fields.Text()
    cell_ids = fields.One2many("devops.notebook.cell", "notebook_id", string="Cells")
    last_run = fields.Datetime(tracking=True)
    data_source_id = fields.Many2one(
        "devops.data.source",
        string="Data Source",
        default=lambda self: self._default_data_source(),
    )
    execution_mode = fields.Selection(
        [
            ("immediate", "Run Immediately"),
            ("scheduled", "Scheduled"),
        ],
        string="Execution Mode",
        default="immediate",
    )
    schedule_ids = fields.One2many(
        "devops.notebook.schedule", "notebook_id", string="Schedules"
    )
    run_history_ids = fields.One2many(
        "devops.notebook.run", "notebook_id", string="Run History", readonly=True
    )
    cell_total = fields.Integer(compute="_compute_stats", store=True)
    execution_count = fields.Integer(compute="_compute_stats", store=True)
    failed_cells = fields.Integer(compute="_compute_stats", store=True)

    def copy(self, default=None):
        default = dict(default or {})
        base_name = default.get("name") or self.name or _("Notebook")
        suffix = ""
        if "copy" in base_name:
            match = re.search(r"copy(\d+)$", base_name)
            if match:
                num = int(match.group(1)) + 1
                base_name = re.sub(r"copy\d+$", "", base_name).rstrip()
                suffix = f"copy{num}"
            else:
                suffix = "copy1"
        else:
            suffix = "copy1"
        default["name"] = f"{base_name} {suffix}".strip()
        return super().copy(default)

    @api.depends("cell_ids.status", "cell_ids.last_run")
    def _compute_stats(self):
        for notebook in self:
            notebook.cell_total = len(notebook.cell_ids)
            notebook.execution_count = len(
                notebook.cell_ids.filtered(lambda c: c.status == "success")
            )
            notebook.failed_cells = len(
                notebook.cell_ids.filtered(lambda c: c.status == "error")
            )

    def action_run_all(self):
        run_model = self.env["devops.notebook.run"].sudo()
        for notebook in self:
            from_schedule = self.env.context.get("from_schedule")
            schedule_id = self.env.context.get("schedule_id")
            if notebook.execution_mode == "scheduled" and not from_schedule:
                active_sched = notebook.schedule_ids.filtered("active")
                if not active_sched:
                    raise UserError(
                        _("Please configure an active schedule before running.")
                    )
                return {
                    "type": "ir.actions.client",
                    "tag": "display_notification",
                    "params": {
                        "title": _("Scheduled run"),
                        "message": _(
                            "This notebook is set to scheduled mode. It will be executed according to its schedule."
                        ),
                        "type": "success",
                        "sticky": False,
                    },
                }
            start_dt = fields.Datetime.now()
            run_record = run_model.create(
                {
                    "name": f"{notebook.name} - {fields.Datetime.to_string(start_dt)}",
                    "notebook_id": notebook.id,
                    "schedule_id": schedule_id,
                    "trigger_type": "schedule" if from_schedule else "manual",
                    "user_id": self.env.user.id,
                    "start_datetime": start_dt,
                }
            )
            run_state = "success"
            error_message = False
            execution_context = {"results": [], "by_id": {}, "by_sequence": {}}
            try:
                for cell in notebook.cell_ids.sorted("sequence"):
                    cell._run_cell(execution_context=execution_context)
                end_dt = fields.Datetime.now()
                notebook.last_run = end_dt
            except Exception:
                run_state = "failed"
                error_message = traceback.format_exc()
                raise
            finally:
                end_dt = fields.Datetime.now()
                duration = 0.0
                if start_dt and end_dt:
                    duration = (end_dt - start_dt).total_seconds()
                sent_mail_ids = []
                for entry in execution_context.get("results", []):
                    if isinstance(entry, dict):
                        data = entry.get("data")
                        if isinstance(data, dict) and data.get("sent_mail_ids"):
                            sent_mail_ids.extend(data.get("sent_mail_ids") or [])
                if sent_mail_ids:
                    sent_mail_ids = list({int(i) for i in sent_mail_ids if i})
                run_record.write(
                    {
                        "end_datetime": end_dt,
                        "duration_seconds": duration,
                        "state": run_state,
                        "message": error_message,
                        "result_cell_total": notebook.cell_total,
                        "result_failed_cells": notebook.failed_cells,
                        "mail_ids": sent_mail_ids and [(6, 0, sent_mail_ids)] or False,
                    }
                )

    @api.model
    def _default_data_source(self):
        default_project_id = self.env.context.get("default_project_id")
        if default_project_id:
            project = self.env["project.project"].browse(default_project_id).exists()
            if project and project.notebook_data_source_id:
                return project.notebook_data_source_id.id
        param = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("devops.default_data_source_id")
        )
        return int(param) if param else False

    def action_run_now(self):
        self.ensure_one()
        self.action_run_all()
        return True

    def action_open_project_wiki(self):
        self.ensure_one()
        if not self.project_id:
            raise UserError(_("Please set a project to open its wiki pages."))
        action = self.env.ref(
            "document_page_project.action_document_page_projects",
            raise_if_not_found=False,
        )
        if not action:
            raise UserError(_("Project wiki action is unavailable. Please update modules."))
        result = action.read()[0]
        result["domain"] = [
            ("type", "=", "content"),
            ("project_id", "=", self.project_id.id),
        ]
        ctx = result.get("context")
        if isinstance(ctx, str):
            ctx = safe_eval(ctx)
        ctx = dict(ctx or {})
        ctx.update({"default_project_id": self.project_id.id})
        result["context"] = ctx
        return result

    def action_export_notebook(self):
        self.ensure_one()
        return {
            "type": "ir.actions.act_window",
            "res_model": "devops.notebook.export.wizard",
            "view_mode": "form",
            "target": "new",
            "context": {"active_id": self.id},
        }

    def action_clear_all_outputs(self):
        for notebook in self:
            notebook.cell_ids.action_clear_output()
        return True

    def action_open_run_history(self):
        self.ensure_one()
        action_ref = self.env.ref(
            "project_notebook.action_devops_notebook_run",
            raise_if_not_found=False,
        )
        if not action_ref:
            raise UserError(
                _("Run history action is unavailable. Please update the DevOps module.")
            )
        action = action_ref.read()[0]
        action_domain = [("notebook_id", "=", self.id)]
        action["domain"] = action_domain
        ctx = action.get("context")
        if isinstance(ctx, str):
            ctx = safe_eval(ctx)
        ctx = dict(ctx or {})
        ctx.update(
            {
                "default_notebook_id": self.id,
                "search_default_notebook_id": self.id,
            }
        )
        action["context"] = ctx
        return action

    def action_configure_schedule(self):
        self.ensure_one()
        view = self.env.ref("project_notebook.view_devops_notebook_schedule_form")
        schedule = self.schedule_ids[:1]
        ctx = {
            "default_notebook_id": self.id,
        }
        action = {
            "type": "ir.actions.act_window",
            "name": _("配置执行计划"),
            "res_model": "devops.notebook.schedule",
            "view_mode": "form",
            "view_id": view.id,
            "target": "new",
            "context": ctx,
        }
        if schedule:
            action["res_id"] = schedule.id
        return action


class DevOpsNotebookCell(models.Model):
    _name = "devops.notebook.cell"
    _description = "DevOps Notebook Cell"
    _order = "sequence, id"

    notebook_id = fields.Many2one(
        "devops.notebook", required=True, ondelete="cascade", index=True
    )
    sequence = fields.Integer(default=lambda self: self._default_sequence())
    cell_type = fields.Selection(
        [
            ("markdown", "Markdown"),
            ("python", "Python"),
            ("sql", "SQL"),
            ("mail", "Mail"),
            ("richtext", "Rich Text"),
        ],
        required=True,
    )
    input_source = fields.Text(string="Input", required=True)
    output_text = fields.Text(string="Output (raw)")
    output_html = fields.Html(string="Rendered Output")
    output_file = fields.Binary(string="Export File", readonly=True)
    output_filename = fields.Char(string="Export Filename", readonly=True)
    output_data = fields.Json(string="Structured Output", readonly=True)
    cell_label = fields.Char(compute="_compute_label", store=True)
    last_run = fields.Datetime()
    status = fields.Selection(
        [("pending", "Pending"), ("success", "Success"), ("error", "Error")],
        default="pending",
    )
    elapsed_ms = fields.Float(string="Elapsed (ms)")

    @api.constrains("cell_type", "notebook_id", "notebook_id.data_source_id")
    def _check_sql_requires_datasource(self):
        for cell in self:
            if cell.cell_type != "sql":
                continue
            ds = cell.notebook_id.data_source_id
            if not ds or ds.source_type == "none":
                raise UserError(_("SQL cells require a configured data source (not 'No Data Source')."))

    def _default_sequence(self):
        notebook_id = self.env.context.get("default_notebook_id")
        if notebook_id:
            notebook = self.env["devops.notebook"].browse(notebook_id)
            max_seq = max(notebook.cell_ids.mapped("sequence") or [0])
            return max_seq + 10
        return 10

    @api.model
    def create(self, vals):
        if not vals.get("sequence") and vals.get("notebook_id"):
            notebook = self.env["devops.notebook"].browse(vals["notebook_id"])
            max_seq = max(notebook.cell_ids.mapped("sequence") or [0])
            vals["sequence"] = max_seq + 10
        return super().create(vals)

    def action_run(self):
        for cell in self:
            cell._run_cell()

    def action_clear_output(self):
        """Clear outputs of selected cells."""
        self.write(
            {
                "output_text": False,
                "output_html": False,
                "output_file": False,
                "output_filename": False,
                "output_data": False,
                "status": "pending",
            }
        )

    def action_delete_cell(self):
        self.unlink()

    @api.depends("sequence")
    def _compute_label(self):
        for cell in self:
            cell.cell_label = f"In [{cell.sequence}]" if cell.cell_type != "markdown" else ""

    def _run_cell(self, execution_context=None):
        start = time.time()
        output_text = ""
        output_html = ""
        status = "success"
        export_file = False
        export_filename = False
        structured_data = None
        try:
            if self.cell_type == "markdown":
                output_html = self._render_markdown(self.input_source or "")
                output_text = self.input_source or ""
            elif self.cell_type == "python":
                output_text = self._exec_python(execution_context=execution_context)
                output_html = "<pre>%s</pre>" % html_escape(output_text or "")
            elif self.cell_type == "mail":
                output_text, structured_data = self._exec_mail(
                    execution_context=execution_context
                )
                output_html = "<pre>%s</pre>" % html_escape(output_text or "")
            elif self.cell_type == "richtext":
                # Treat input as HTML; render directly and keep raw text
                output_text = self.input_source or ""
                output_html = self.input_source or ""
            elif self.cell_type == "sql":
                sql_result = self._exec_sql()
                if isinstance(sql_result, dict):
                    output_text = sql_result.get("text", "")
                    output_html = sql_result.get("html", "")
                    structured_data = sql_result.get("data")
                    export_file = sql_result.get("file")
                    export_filename = sql_result.get("filename")
                else:
                    output_text = sql_result
                    output_html = "<pre>%s</pre>" % html_escape(output_text or "")
        except Exception as exc:  # pragma: no cover - best effort logging
            status = "error"
            output_text = str(exc)
            output_html = "<pre class='text-danger'>%s</pre>" % html_escape(
                output_text
            )
        elapsed = (time.time() - start) * 1000.0
        payload = {
            "status": status,
            "output_text": output_text,
            "output_html": output_html,
            "output_file": export_file,
            "output_filename": export_filename,
            "last_run": fields.Datetime.now(),
            "elapsed_ms": elapsed,
            "output_data": structured_data,
        }
        if status == "success" and self.cell_type == "markdown":
            payload["output_text"] = self.input_source or ""
        entry = self._make_result_entry(
            status=status,
            text=output_text,
            html=output_html,
            data=structured_data,
            file=export_file,
            filename=export_filename,
        )
        self.write(payload)
        if execution_context is not None:
            execution_context.setdefault("results", []).append(entry)
            execution_context.setdefault("by_id", {})[self.id] = entry
            execution_context.setdefault("by_sequence", {})[self.sequence] = entry
            execution_context.setdefault("by_label", {})
            if self.cell_label:
                execution_context["by_label"][self.cell_label] = entry
            execution_context["last_result"] = entry

    def _exec_python(self, execution_context=None):
        localdict = {
            "env": self.env,
            "notebook": self.notebook_id,
            "cell": self,
            "recordset": self.env[self._name].browse(self.id),
        }
        localdict.setdefault("print", builtins.print)
        buffer = StringIO()
        code = self.input_source or ""
        if execution_context is None:
            execution_context = {}
        localdict["cell_results"] = execution_context
        localdict["last_result"] = execution_context.get("last_result")

        localdict["get_cell_result"] = lambda identifier: self._get_cell_result_helper(
            identifier, execution_context
        )
        globals_env = {"__builtins__": builtins}
        with contextlib.redirect_stdout(buffer):
            exec(compile(code, "<notebook>", "exec"), globals_env, localdict)
        stdout = buffer.getvalue()
        return stdout.strip()

    def _exec_mail(self, execution_context=None):
        Mail = self.env["mail.mail"].sudo()
        sent_ids = []
        buffer = StringIO()
        localdict = {
            "env": self.env,
            "notebook": self.notebook_id,
            "cell": self,
            "recordset": self.env[self._name].browse(self.id),
            "cell_results": execution_context or {},
            "last_result": (execution_context or {}).get("last_result"),
        }
        localdict.setdefault("print", builtins.print)

        def normalize_addresses(value):
            if not value:
                return ""
            if isinstance(value, (list, tuple, set)):
                return ",".join([v.strip() for v in value if v])
            return str(value).replace(";", ",")

        def prepare_attachments(attachments):
            prepared = []
            for item in attachments or []:
                name = None
                content = None
                if isinstance(item, dict):
                    name = item.get("name")
                    content = item.get("content")
                elif isinstance(item, (list, tuple)) and len(item) >= 2:
                    name, content = item[0], item[1]
                if not name or content is None:
                    continue
                data = content
                if isinstance(content, bytes):
                    data = base64.b64encode(content).decode("ascii")
                elif isinstance(content, str):
                    data = content
                else:
                    data = base64.b64encode(str(content).encode("utf-8")).decode("ascii")
                prepared.append((name, data))
            return prepared

        def send_mail(
            *,
            subject,
            email_to,
            body_html=None,
            body_text=None,
            email_cc=None,
            email_bcc=None,
            attachments=None,
            auto_send=True,
        ):
            if not subject or not email_to:
                raise UserError(
                    _("Both subject and recipients (email_to) are required to send mail.")
                )
            vals = {
                "subject": subject,
                "body_html": body_html or (body_text and html_escape(body_text)) or "",
                "body": body_text or "",
                "email_to": normalize_addresses(email_to),
                "email_cc": normalize_addresses(email_cc),
                "email_bcc": normalize_addresses(email_bcc),
            }
            prepared_attachments = prepare_attachments(attachments)
            if prepared_attachments:
                vals["attachment_ids"] = [
                    (
                        0,
                        0,
                        {
                            "name": name,
                            "datas": data,
                        },
                    )
                    for name, data in prepared_attachments
                ]
            mail = Mail.create(vals)
            if auto_send:
                mail.send()
            sent_ids.append(mail.id)
            return mail

        localdict["send_mail"] = send_mail
        localdict["get_cell_result"] = lambda identifier: self._get_cell_result_helper(
            identifier, execution_context
        )
        code = self.input_source or ""
        globals_env = {"__builtins__": builtins}
        with contextlib.redirect_stdout(buffer):
            exec(compile(code, "<notebook mail>", "exec"), globals_env, localdict)
        stdout = buffer.getvalue().strip()
        summary = stdout or _("Sent %s mails") % len(sent_ids)
        data = {"sent_mail_ids": sent_ids}
        return summary, data

    def _get_cell_result_helper(self, identifier, execution_context):
        entry = None
        if execution_context:
            if isinstance(identifier, str):
                entry = execution_context.get("by_label", {}).get(identifier)
            else:
                by_seq = execution_context.get("by_sequence", {})
                by_id = execution_context.get("by_id", {})
                entry = by_seq.get(identifier) or by_id.get(identifier)
        if entry:
            return entry
        cell = self._find_cell_by_identifier(identifier)
        if cell:
            return cell._make_result_entry()
        return None

    def _make_result_entry(
        self,
        *,
        status=None,
        text=None,
        html=None,
        data=None,
        file=None,
        filename=None,
    ):
        return {
            "id": self.id,
            "sequence": self.sequence,
            "label": self.cell_label,
            "type": self.cell_type,
            "status": status if status is not None else self.status,
            "text": text if text is not None else self.output_text,
            "html": html if html is not None else self.output_html,
            "data": data if data is not None else self.output_data,
            "file": file if file is not None else self.output_file,
            "filename": filename if filename is not None else self.output_filename,
        }

    def _find_cell_by_identifier(self, identifier):
        notebook = self.notebook_id
        if not notebook:
            return self.env[self._name]
        candidates = notebook.cell_ids
        target = self.env[self._name]
        if isinstance(identifier, int):
            target = candidates.filtered(lambda c: c.sequence == identifier)[:1]
        elif isinstance(identifier, str):
            stripped = identifier.strip()
            match = re.match(r"In \[(\d+)\]", stripped)
            if match:
                seq = int(match.group(1))
                target = candidates.filtered(lambda c: c.sequence == seq)[:1]
            if not target:
                target = candidates.filtered(lambda c: c.cell_label == stripped)[:1]
        return target

    def _exec_sql(self):
        query = (self.input_source or "").strip()
        if not query:
            return ""
        source = self.notebook_id.data_source_id
        if not source:
            raise ValueError("No data source configured for this notebook.")
        if source.source_type == "none":
            raise ValueError("SQL cells require a real data source (not 'No Data Source').")
        if source.source_type == "postgresql":
            conn_str = source._build_postgres_dsn()
            if conn_str:
                import psycopg2

                with psycopg2.connect(conn_str) as conn:
                    with conn.cursor() as cur:
                        cur.execute(query)
                        if cur.description:
                            return self._format_query_result(cur)
                        return "%s row(s) affected" % cur.rowcount
            cr = self.env.cr
            cr.execute(query)
            if cr.description:
                return self._format_query_result(cr)
            return "%s row(s) affected" % cr.rowcount
        elif source.source_type == "mssql":
            try:
                import pyodbc
            except ImportError as exc:
                raise ValueError("pyodbc not installed: %s" % exc) from exc

            conn_str = source._build_mssql_dsn()
            with pyodbc.connect(conn_str, timeout=5) as conn:
                cur = conn.cursor()
                cur.execute(query)
                if cur.description:
                    return self._format_query_result(cur)
                return "%s row(s) affected" % cur.rowcount
        elif source.source_type == "oracle":
            try:
                oracledb = source._load_oracle_driver()
            except ImportError as exc:
                raise ValueError("python-oracledb not installed: %s" % exc) from exc

            dsn = source._build_oracle_dsn()
            with oracledb.connect(
                user=source.username or "",
                password=source.password or "",
                dsn=dsn,
            ) as conn:
                cur = conn.cursor()
                cur.execute(query)
                if cur.description:
                    return self._format_query_result(cur)
                return "%s row(s) affected" % cur.rowcount
        elif source.source_type == "csv":
            path = source.csv_path
            if not path:
                return "CSV path not configured."
            import csv

            with open(path, newline="", encoding="utf-8") as csvfile:
                reader = csv.reader(csvfile)
                rows = list(reader)
            text_rows = ["\t".join(row) for row in rows]
            html_rows = "".join(
                "<tr>" + "".join(f"<td>{html_escape(col)}</td>" for col in row) + "</tr>"
                for row in rows
            )
            html = f"<table class='o_devops_table'><tbody>{html_rows}</tbody></table>"
            return "\n".join(text_rows), html
        return "Data source type %s not supported yet." % source.source_type

    def _format_query_result(self, cursor):
        rows = cursor.fetchall()
        headers = [desc[0] for desc in cursor.description]
        text_lines = [", ".join(headers)]
        text_lines += [
            ", ".join([self._stringify_value(col) for col in row]) for row in rows
        ]
        html_header = "".join(f"<th>{html_escape(self._stringify_value(h))}</th>" for h in headers)
        html_body = "".join(
            "<tr>"
            + "".join(
                f"<td>{html_escape(self._stringify_value(col))}</td>"
                for col in row
            )
            + "</tr>"
            for row in rows
        )
        html = (
            "<table class='o_devops_table'>"
            f"<thead><tr>{html_header}</tr></thead>"
            f"<tbody>{html_body}</tbody></table>"
        )
        data_rows = []
        for row in rows:
            record = {}
            for header, value in zip(headers, row):
                record[header] = self._stringify_value(value)
            data_rows.append(record)
        return {
            "text": "\n".join(text_lines),
            "html": html,
            "data": data_rows,
        }

    def _stringify_value(self, value):
        if value is None:
            return ""
        if isinstance(value, (bytes, bytearray)):
            try:
                return value.decode("utf-8")
            except Exception:
                return value.hex()
        return str(value)

    def _build_xlsx(self, headers, rows):
        try:
            import xlsxwriter
        except Exception:
            return False
        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {"in_memory": True})
        worksheet = workbook.add_worksheet("Result")
        header_fmt = workbook.add_format({"bold": True, "bg_color": "#F3F4F6"})
        for col, h in enumerate(headers):
            worksheet.write(0, col, h, header_fmt)
        for r_index, row in enumerate(rows, start=1):
            for c_index, col in enumerate(row):
                worksheet.write(r_index, c_index, col)
        workbook.close()
        buffer.seek(0)
        try:
            import base64
            return base64.b64encode(buffer.getvalue()).decode("ascii")
        except Exception:
            return False

    def _render_markdown(self, source):
        text = source or ""
        try:
            import markdown

            return markdown.markdown(
                text,
                extensions=[
                    "fenced_code",
                    "tables",
                    "codehilite",
                    "nl2br",
                ],
                output_format="html5",
            )
        except Exception:
            return self._render_markdown_fallback(text)

    def _render_markdown_fallback(self, text):
        escaped = html_escape(text)
        lines = escaped.splitlines()
        rows = []
        html_lines = []
        table_mode = False
        for line in lines:
            stripped = line.strip()
            if stripped.startswith("|") and stripped.endswith("|"):
                table_mode = True
                parts = [col.strip() for col in stripped.strip("|").split("|")]
                rows.append(parts)
                continue
            if table_mode:
                html_lines.append(self._render_table(rows))
                rows = []
                table_mode = False
            if stripped.startswith("### "):
                html_lines.append(f"<h3>{stripped[4:]}</h3>")
            elif stripped.startswith("## "):
                html_lines.append(f"<h2>{stripped[3:]}</h2>")
            elif stripped.startswith("# "):
                html_lines.append(f"<h1>{stripped[2:]}</h1>")
            elif stripped:
                html_lines.append(f"<p>{stripped}</p>")
            else:
                html_lines.append("<br/>")
        if table_mode:
            html_lines.append(self._render_table(rows))
        import re

        body = "\n".join(html_lines)
        body = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", body)
        body = re.sub(r"`([^`]+)`", r"<code>\1</code>", body)
        return body

    def _render_table(self, rows):
        if not rows:
            return ""
        header = rows[0]
        body_rows = rows[2:] if len(rows) > 2 else rows[1:]
        header_html = "".join(f"<th>{col}</th>" for col in header)
        body_html = "".join(
            "<tr>" + "".join(f"<td>{col}</td>" for col in row) + "</tr>"
            for row in body_rows
        )
        return f"<table class='o_devops_table'><thead><tr>{header_html}</tr></thead><tbody>{body_html}</tbody></table>"


class ProjectProject(models.Model):
    _inherit = "project.project"

    notebook_data_source_id = fields.Many2one(
        "devops.data.source",
        string="Default Notebook Data Source",
        help="Default data source when creating notebooks under this project.",
    )


class DevOpsNotebookSchedule(models.Model):
    _name = "devops.notebook.schedule"
    _description = "Notebook Schedule"
    _order = "next_run asc"

    name = fields.Char(string="Description")
    notebook_id = fields.Many2one("devops.notebook", required=True, ondelete="cascade")
    project_id = fields.Many2one(
        "project.project",
        string="Project",
        related="notebook_id.project_id",
        store=True,
        readonly=True,
    )
    start_datetime = fields.Datetime(
        string="Start", required=True, default=lambda self: fields.Datetime.now()
    )
    end_datetime = fields.Datetime(string="End")
    interval_number = fields.Integer(string="Every", default=1, required=True)
    interval_type = fields.Selection(
        [
            ("months", "Months"),
            ("weeks", "Weeks"),
            ("days", "Days"),
            ("hours", "Hours"),
            ("minutes", "Minutes"),
        ],
        default="days",
        required=True,
    )
    next_run = fields.Datetime(string="Next Run", compute="_compute_next_run", store=True)
    active = fields.Boolean(default=True)
    last_run = fields.Datetime(readonly=True)
    run_count = fields.Integer(readonly=True)

    @api.depends("start_datetime", "interval_number", "interval_type", "last_run", "active")
    def _compute_next_run(self):
        for rec in self:
            if not rec.active:
                rec.next_run = False
                continue
            now = fields.Datetime.now()
            base = rec.last_run or rec.start_datetime
            # If first run and start is in the past/now, run immediately
            if not rec.last_run and base and base <= now:
                rec.next_run = now
            else:
                rec.next_run = rec._add_interval(base)

    def _add_interval(self, dt):
        if not dt:
            return False
        itype = self.interval_type
        inum = self.interval_number or 1
        if itype == "seconds":
            # Guard for legacy records; normalize to minutes
            itype = "minutes"
            inum = self._normalize_interval_to_minutes(inum)
        delta_args = {itype: inum}
        return fields.Datetime.add(dt, **delta_args)

    def action_run_now(self):
        for schedule in self:
            schedule._run_once()

    def _run_once(self):
        if not self.notebook_id:
            return
        ctx = dict(self.env.context, from_schedule=True, schedule_id=self.id)
        self.notebook_id.with_context(ctx).action_run_all()
        now = fields.Datetime.now()
        self.write(
            {
                "last_run": now,
                "run_count": (self.run_count or 0) + 1,
                "next_run": self._add_interval(now),
            }
        )

    @api.model
    def _cron_run_schedules(self):
        now = fields.Datetime.now()
        domain = [
            ("active", "=", True),
            ("next_run", "!=", False),
            ("next_run", "<=", now),
        ]
        for schedule in self.search(domain, limit=200):
            if schedule.end_datetime and schedule.end_datetime < now:
                schedule.active = False
                continue
            schedule._run_once()

    def _normalize_interval_to_minutes(self, interval_number=None):
        number = interval_number if interval_number is not None else self.interval_number
        return max(1, int(((number or 1) + 59) // 60))

    def _migrate_seconds_to_minutes(self):
        # Normalize legacy seconds interval to minutes (minimum 1 minute)
        sec_records = self.search([("interval_type", "=", "seconds")])
        for rec in sec_records:
            rec.write(
                {
                    "interval_type": "minutes",
                    "interval_number": rec._normalize_interval_to_minutes(),
                }
            )

    @api.constrains("notebook_id", "active")
    def _check_single_active_schedule(self):
        for rec in self:
            if not rec.active or not rec.notebook_id:
                continue
            others = self.search(
                [
                    ("id", "!=", rec.id),
                    ("notebook_id", "=", rec.notebook_id.id),
                    ("active", "=", True),
                ],
                limit=1,
            )
            if others:
                raise ValueError(_("A notebook can only have one active schedule."))


class DevOpsNotebookRun(models.Model):
    _name = "devops.notebook.run"
    _description = "Notebook Run History"
    _order = "start_datetime desc"

    name = fields.Char(required=True)
    notebook_id = fields.Many2one("devops.notebook", required=True, ondelete="cascade")
    schedule_id = fields.Many2one("devops.notebook.schedule", ondelete="set null")
    trigger_type = fields.Selection(
        [("manual", "Manual"), ("schedule", "Scheduled")],
        string="Trigger",
        default="manual",
    )
    project_id = fields.Many2one(
        "project.project",
        string="Project",
        related="notebook_id.project_id",
        store=True,
        readonly=True,
    )
    state = fields.Selection(
        [("success", "Success"), ("failed", "Failed")],
        string="Status",
        default="success",
    )
    start_datetime = fields.Datetime(required=True)
    end_datetime = fields.Datetime()
    duration_seconds = fields.Float(string="Duration (s)")
    user_id = fields.Many2one("res.users", string="Triggered By")
    message = fields.Text(string="Details")
    result_cell_total = fields.Integer(string="Cells")
    result_failed_cells = fields.Integer(string="Failed Cells")
    mail_ids = fields.Many2many(
        "mail.mail",
        "devops_run_mail_rel",
        "run_id",
        "mail_id",
        string="Mails",
        readonly=True,
    )

    def action_open_mails(self):
        self.ensure_one()
        action = self.env.ref("mail.action_view_mail_mail", raise_if_not_found=False)
        if not action:
            return False
        result = action.read()[0]
        result["domain"] = [("id", "in", self.mail_ids.ids)]
        ctx = result.get("context")
        if isinstance(ctx, str):
            ctx = safe_eval(ctx)
        ctx = dict(ctx or {})
        ctx.update(
            {
                "default_devops_run_ids": [self.id],
                "search_default_devops_run_ids": [self.id],
            }
        )
        result["context"] = ctx
        return result
