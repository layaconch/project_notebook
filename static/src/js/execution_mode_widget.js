/** @odoo-module **/

import { registry } from "@web/core/registry";
import { SelectionField } from "@web/views/fields/selection/selection_field";
import { useService } from "@web/core/utils/hooks";

export class DevopsExecutionModeField extends SelectionField {
    setup() {
        super.setup();
        this.orm = useService("orm");
        this.action = useService("action");
    }

    async onSelectionChange(value) {
        await super.onSelectionChange(value);
        if (this.props.name !== "execution_mode" || value !== "scheduled") {
            return;
        }
        const record = this.props.record;
        if (!record || !record.resId) {
            return;
        }
        try {
            const action = await this.orm.call(
                "devops.notebook",
                "action_configure_schedule",
                [[record.resId]],
                {}
            );
            if (action) {
                await this.action.doAction(action);
            }
        } catch (e) {
            // let the normal dialog display the error
            throw e;
        }
    }
}

registry.category("fields").add("devops_execution_mode", {
    component: DevopsExecutionModeField,
    supportedTypes: ["selection"],
});
