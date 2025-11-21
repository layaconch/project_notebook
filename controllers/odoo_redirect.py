from urllib.parse import urlencode

from odoo import http
from odoo.http import request


class DevOpsActionRedirect(http.Controller):
    @http.route('/odoo/action-<int:action_id>', auth='user')
    def devops_redirect_action(self, action_id, **params):
        Action = request.env['ir.actions.act_window'].sudo().browse(action_id)
        if not Action.exists():
            return request.redirect('/web')

        requested_view_type = params.get('view_type')
        preferred = Action.view_mode.split(',') if Action.view_mode else []
        target_type = requested_view_type or (preferred[0] if preferred else 'list')
        if requested_view_type == 'tree' and 'list' in preferred:
            target_type = 'list'

        hash_params = {
            'action': action_id,
            'model': Action.res_model,
            'view_type': target_type,
        }
        return request.redirect('/web#%s' % urlencode(hash_params))

    @http.route('/odoo/action_devops_settings', auth='user')
    def devops_settings_shortcut(self, **params):
        """Gracefully redirect legacy link to the DevOps settings action."""
        try:
            action = request.env.ref('project_notebook.action_devops_settings').id
        except Exception:
            return request.redirect('/web')
        hash_params = {'action': action, 'menu_id': params.get('menu_id')}
        return request.redirect('/web#%s' % urlencode({k: v for k, v in hash_params.items() if v}))
