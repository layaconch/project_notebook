import csv
import os
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class DevOpsDataSource(models.Model):
    _name = "devops.data.source"
    _description = "DevOps Data Source"
    _PORT_DEFAULTS = {
        "postgresql": "5432",
        "oracle": "1521",
        "mssql": "1433",
        "mysql": "3306",
    }

    name = fields.Char(required=True)
    source_type = fields.Selection(
        [
            ("none", "No Data Source"),
            ("postgresql", "PostgreSQL"),
            ("oracle", "Oracle"),
            ("csv", "CSV File"),
            ("mssql", "Microsoft SQL Server"),
        ],
        required=True,
        default="postgresql",
    )
    connection_string = fields.Char(help="Legacy connection string.")
    host = fields.Char(string="Host")
    port = fields.Char(string="Port", default=lambda self: self._get_default_port())
    database = fields.Char(string="Database")
    schema = fields.Char(string="Schema")
    username = fields.Char(string="Username")
    password = fields.Char(string="Password")
    csv_path = fields.Char(help="Absolute path to CSV file when type is CSV.")
    description = fields.Text()

    def _get_default_port(self, source_type=None):
        stype = source_type or self.source_type or "postgresql"
        return self._PORT_DEFAULTS.get(stype)

    @api.onchange("source_type")
    def _onchange_source_type(self):
        default_port = self._get_default_port(self.source_type)
        if default_port:
            if not self.port or self.port in self._PORT_DEFAULTS.values():
                self.port = default_port

    def action_test_connection(self):
        messages = []
        for source in self:
            if source.source_type == "postgresql":
                try:
                    import psycopg2

                    conn_str = source._build_postgres_dsn()
                    with psycopg2.connect(conn_str) as conn:
                        with conn.cursor() as cur:
                            cur.execute("SELECT version();")
                            version = cur.fetchone()[0]
                        messages.append(_("PostgreSQL connection OK: %s") % version)
                except Exception as exc:  # pragma: no cover
                    raise UserError(_("PostgreSQL connection failed: %s") % exc)
            elif source.source_type == "oracle":
                try:
                    oracledb = source._load_oracle_driver()
                except ImportError as exc:
                    raise UserError(
                        _("Oracle test not available: %s. Install python-oracledb.")
                        % exc
                    )
                try:
                    dsn = source._build_oracle_dsn()
                    with oracledb.connect(
                        user=source.username or "",
                        password=source.password or "",
                        dsn=dsn,
                    ) as conn:
                        messages.append(
                            _("Oracle connection OK: %s")
                            % (conn.version or "driver ready")
                        )
                except Exception as exc:
                    raise UserError(_("Oracle connection failed: %s") % exc)
            elif source.source_type == "csv":
                if not source.csv_path or not os.path.exists(source.csv_path):
                    raise UserError(_("CSV path does not exist."))
                try:
                    with open(source.csv_path, newline="", encoding="utf-8") as csvfile:
                        csv.reader(csvfile).__next__()
                except Exception as exc:
                    raise UserError(_("CSV file read failed: %s") % exc)
                messages.append(_("CSV file reachable: %s") % source.csv_path)
            elif source.source_type == "mssql":
                try:
                    import pyodbc

                    dsn = source._build_mssql_dsn()
                    with pyodbc.connect(dsn, timeout=5) as conn:
                        cursor = conn.cursor()
                        cursor.execute("SELECT @@VERSION")
                        version = cursor.fetchone()[0]
                        messages.append(_("MSSQL connection OK: %s") % version)
                except Exception as exc:
                    raise UserError(_("MSSQL connection failed: %s") % exc)
        if messages:
            return {
                "type": "ir.actions.client",
                "tag": "display_notification",
                "params": {
                    "title": _("Connection Test"),
                    "message": "\n".join(messages),
                    "type": "success",
                    "sticky": False,
                },
            }
        return True

    def _convert_jdbc_to_psycopg(self, url):
        # jdbc:postgresql://host:port/db?user=X&password=Y
        import urllib.parse as urlparse

        rest = url.replace("jdbc:postgresql://", "")
        if "/" in rest:
            host_port, database = rest.split("/", 1)
        else:
            host_port, database = rest, ""
        if "?" in database:
            database, query = database.split("?", 1)
        else:
            query = ""
        if ":" in host_port:
            host, port = host_port.split(":", 1)
        else:
            host, port = host_port, "5432"
        params = dict(urlparse.parse_qsl(query))
        user = params.get("user", "")
        password = params.get("password", "")
        return f"host={host} port={port} dbname={database} user={user} password={password}"

    def _build_postgres_dsn(self):
        if self.host and self.database:
            parts = [f"host={self.host}"]
            if self.port:
                parts.append(f"port={self.port}")
            parts.append(f"dbname={self.database}")
            if self.username:
                parts.append(f"user={self.username}")
            if self.password:
                parts.append(f"password={self.password}")
            if self.schema:
                # wrap options value to avoid splitting on spaces
                parts.append(f"options='-c search_path={self.schema}'")
            return " ".join(parts)
        conn_str = self.connection_string or ""
        if conn_str.startswith("jdbc:postgresql://"):
            conn_str = self._convert_jdbc_to_psycopg(conn_str)
        if self.username and self.password and "user=" not in conn_str:
            conn_str += f" user={self.username} password={self.password}"
        if self.schema and "search_path" not in conn_str:
            conn_str += f" options='-c search_path={self.schema}'"
        return conn_str

    def _build_mssql_dsn(self):
        host = self.host or "localhost"
        port = self.port or "1433"
        database = self.database or "master"
        driver = "ODBC Driver 17 for SQL Server"
        parts = [f"DRIVER={{{driver}}}", f"SERVER={host},{port}", f"DATABASE={database}"]
        if self.username:
            parts.append(f"UID={self.username}")
        if self.password:
            parts.append(f"PWD={self.password}")
        return ";".join(parts)

    def _build_oracle_dsn(self):
        self.ensure_one()
        oracledb = self._load_oracle_driver()
        return oracledb.makedsn(
            self.host or "localhost",
            int(self.port or 1521),
            service_name=self.database or None,
        )

    def _load_oracle_driver(self):
        import oracledb
        try:
            from oracledb import driver_mode

            thin_mode = driver_mode.is_thin_mode()
        except Exception:
            thin_mode = True
        if thin_mode:
            lib_dir = os.environ.get("ORACLE_CLIENT", "/opt/oracle/instantclient")
            if lib_dir and os.path.isdir(lib_dir):
                init_client = getattr(oracledb, "init_oracle_client", None)
                if init_client:
                    try:
                        init_client(lib_dir=lib_dir)
                    except oracledb.ProgrammingError:
                        pass
        return oracledb

    def action_duplicate(self):
        self.ensure_one()
        copy_vals = {
            "name": _("%s (copy)") % self.name,
        }
        new_ds = self.copy(copy_vals)
        return {
            "type": "ir.actions.act_window",
            "res_model": "devops.data.source",
            "view_mode": "form",
            "res_id": new_ds.id,
        }
