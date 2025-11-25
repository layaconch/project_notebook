import base64
import json

from odoo import http, SUPERUSER_ID, registry as registry_get, api
from odoo.http import request
from odoo.tools import html_escape


class DevOpsMailApiController(http.Controller):
    @http.route("/mail/api/ping", type="http", auth="none", csrf=False)
    def ping(self, **kwargs):
        return http.Response(
            json.dumps({"status": "ok"}),
            status=200,
            content_type="application/json",
        )

    @http.route(
        ["/mail/api/send_mail", "/odoo/mail/api/send_mail"],
        type="http",  # allow plain HTTP/POST for pg_http, curl, etc.
        auth="none",  # nodb route; we'll select db manually
        methods=["POST"],
        csrf=False,
    )
    def send_mail(self, **kwargs):
        """Minimal mail API for pg_http或curl。

        支持 application/json 请求；返回 JSON。
        Body 示例：
        {
            "token": "...必填...",
            "subject": "Hello",
            "email_to": "a@x.com,b@y.com",
            "email_cc": "...",
            "email_bcc": "...",
            "body_html": "<p>hi</p>",
            "body": "hi text",
            "attachments": [{"name": "file.txt", "data": "base64"}]
        }
        """
        # 解析 JSON 或表单参数
        payload = None
        try:
            if hasattr(request, "get_json_data"):
                payload = request.get_json_data()
        except Exception:
            payload = None
        if not payload and request.httprequest.data:
            try:
                payload = json.loads(request.httprequest.data.decode("utf-8"))
            except Exception:
                payload = None
        if not payload:
            payload = kwargs or {}

        db = request.params.get("db")
        if not db:
            return http.Response(
                json.dumps({"error": "missing db"}),
                status=400,
                content_type="application/json",
            )

        registry = registry_get(db)
        if registry is None:
            return http.Response(
                json.dumps({"error": "invalid db"}),
                status=400,
                content_type="application/json",
            )

        token = payload.get("token")
        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            expected = env["ir.config_parameter"].get_param("devops.mail_api_token") or "devops-mail-token"
            sender_user_id = env["ir.config_parameter"].get_param("devops.mail_sender_user_id")
            mail_server_param = env["ir.config_parameter"].get_param("devops.mail_server_id")
        if not expected or token != expected:
            return http.Response(
                json.dumps({"error": "unauthorized"}),
                status=403,
                content_type="application/json",
            )

        subject = payload.get("subject")
        email_to = payload.get("email_to")
        if not subject or not email_to:
            return http.Response(
                json.dumps({"error": "subject and email_to are required"}),
                status=400,
                content_type="application/json",
            )

        def normalize(value):
            if not value:
                return False
            if isinstance(value, (list, tuple, set)):
                return ",".join([str(v).strip() for v in value if v])
            return str(value).replace(";", ",")

        def to_int(val):
            try:
                return int(val)
            except Exception:
                return None

        attachments_vals = []
        for att in payload.get("attachments") or []:
            name = att.get("name")
            data = att.get("data")
            if not name or not data:
                continue
            try:
                base64.b64decode(data)
            except Exception:
                continue
            attachments_vals.append((0, 0, {"name": name, "datas": data}))

        vals = {
            "subject": subject,
            "email_to": normalize(email_to),
            "email_cc": normalize(payload.get("email_cc")),
            "body_html": payload.get("body_html")
            or (payload.get("body") and html_escape(payload.get("body")))
            or "",
            "body": payload.get("body") or "",
        }
        email_from = payload.get("email_from")
        sender_user_email = False
        if sender_user_id:
            try:
                sender_user = env["res.users"].browse(int(sender_user_id)).exists()
                if sender_user:
                    sender_user_email = sender_user.email_formatted or sender_user.email
            except Exception:
                sender_user_email = False
        email_from = email_from or sender_user_email
        if email_from:
            vals["email_from"] = email_from
        if attachments_vals:
            vals["attachment_ids"] = attachments_vals
        notebook_id = to_int(payload.get("notebook_id"))
        run_id = to_int(payload.get("run_id"))
        if notebook_id:
            vals["model"] = "devops.notebook"
            vals["res_id"] = notebook_id

        with registry.cursor() as cr:
            env = api.Environment(cr, SUPERUSER_ID, {})
            server_id = False
            if mail_server_param:
                try:
                    server_id = int(mail_server_param)
                except Exception:
                    server_id = False
                if server_id:
                    server = env["ir.mail_server"].browse(server_id).exists()
                    if not server:
                        server_id = False
            if server_id:
                vals["mail_server_id"] = server_id
            mail = env["mail.mail"].create(vals)
            # 关联运行/笔记本并记录到 chatter
            if run_id:
                run = env["devops.notebook.run"].browse(run_id)
                if run:
                    mail.devops_run_ids = [(4, run.id)]
                    notebook_id = notebook_id or run.notebook_id.id
            if notebook_id:
                notebook = env["devops.notebook"].browse(notebook_id)
                if notebook:
                    recipients = vals.get("email_to") or ""
                    if vals.get("email_cc"):
                        recipients = ",".join([recipients, vals["email_cc"]]) if recipients else vals["email_cc"]
                    notebook.message_post(
                        body=(
                            "<p><b>邮件已发送</b></p>"
                            f"<p>主题：{html_escape(subject)}</p>"
                            f"<p>收件人：{html_escape(recipients or '')}</p>"
                        ),
                        attachment_ids=mail.attachment_ids.ids,
                        message_type="comment",
                        subtype_xmlid="mail.mt_note",
                    )
            mail.send()
        return http.Response(
            json.dumps({"status": "sent", "mail_id": mail.id}),
            status=200,
            content_type="application/json",
        )
