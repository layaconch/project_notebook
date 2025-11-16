import builtins
import contextlib
import csv
import io
import re
import time
from io import StringIO

from odoo import api, fields, models
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
    category_id = fields.Many2one(
        "devops.notebook.category", string="Category", tracking=True
    )
    cell_total = fields.Integer(compute="_compute_stats", store=True)
    execution_count = fields.Integer(compute="_compute_stats", store=True)
    failed_cells = fields.Integer(compute="_compute_stats", store=True)

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
        for notebook in self:
            for cell in notebook.cell_ids.sorted("sequence"):
                cell.action_run()
            notebook.last_run = fields.Datetime.now()

    @api.model
    def _default_data_source(self):
        param = (
            self.env["ir.config_parameter"]
            .sudo()
            .get_param("devops.default_data_source_id")
        )
        return int(param) if param else False


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
        ],
        required=True,
    )
    input_source = fields.Text(string="Input", required=True)
    output_text = fields.Text(string="Output (raw)")
    output_html = fields.Html(string="Rendered Output")
    output_file = fields.Binary(string="Export File", readonly=True)
    output_filename = fields.Char(string="Export Filename", readonly=True)
    cell_label = fields.Char(compute="_compute_label", store=True)
    last_run = fields.Datetime()
    status = fields.Selection(
        [("pending", "Pending"), ("success", "Success"), ("error", "Error")],
        default="pending",
    )
    elapsed_ms = fields.Float(string="Elapsed (ms)")

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

    @api.depends("sequence")
    def _compute_label(self):
        for cell in self:
            cell.cell_label = f"In [{cell.sequence}]" if cell.cell_type != "markdown" else ""

    def _run_cell(self):
        start = time.time()
        output_text = ""
        output_html = ""
        status = "success"
        export_file = False
        export_filename = False
        try:
            if self.cell_type == "markdown":
                output_html = self._render_markdown(self.input_source or "")
                output_text = self.input_source or ""
            elif self.cell_type == "python":
                output_text = self._exec_python()
                output_html = "<pre>%s</pre>" % html_escape(output_text or "")
            elif self.cell_type == "sql":
                sql_result = self._exec_sql()
                if isinstance(sql_result, tuple):
                    # tuple can be (text, html[, file_bytes, filename])
                    output_text = sql_result[0]
                    output_html = sql_result[1]
                    if len(sql_result) >= 4:
                        export_file = sql_result[2]
                        export_filename = sql_result[3]
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
        }
        if status == "success" and self.cell_type == "markdown":
            payload["output_text"] = self.input_source or ""
        self.write(payload)

    def _exec_python(self):
        localdict = {
            "env": self.env,
            "notebook": self.notebook_id,
            "cell": self,
            "recordset": self.env[self._name].browse(self.id),
        }
        localdict.setdefault("print", builtins.print)
        buffer = StringIO()
        code = self.input_source or ""
        globals_env = {"__builtins__": builtins}
        with contextlib.redirect_stdout(buffer):
            exec(compile(code, "<notebook>", "exec"), globals_env, localdict)
        stdout = buffer.getvalue()
        return stdout.strip()

    def _exec_sql(self):
        query = (self.input_source or "").strip()
        if not query:
            return ""
        source = self.notebook_id.data_source_id
        if not source:
            raise ValueError("No data source configured for this notebook.")
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
        text_lines += [", ".join([str(col) for col in row]) for row in rows]
        html_header = "".join(f"<th>{html_escape(h)}</th>" for h in headers)
        html_body = "".join(
            "<tr>" + "".join(f"<td>{html_escape(col)}</td>" for col in row) + "</tr>"
            for row in rows
        )
        html = (
            "<table class='o_devops_table'>"
            f"<thead><tr>{html_header}</tr></thead>"
            f"<tbody>{html_body}</tbody></table>"
        )
        return "\n".join(text_lines), html

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
