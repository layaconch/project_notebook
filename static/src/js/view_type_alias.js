/** @odoo-module **/

import { session } from "@web/session";

// Allow legacy "tree" references to reuse the new "list" definition so
// cached links such as /odoo/action-XXX still render without errors.
if (!session.view_info.tree && session.view_info.list) {
    session.view_info.tree = {
        ...session.view_info.list,
    };
}
