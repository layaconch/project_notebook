/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ErrorDialog } from "@web/core/errors/error_dialogs";
import { browser } from "@web/core/browser/browser";

function safeCopy(text) {
    try {
        const clip = browser.navigator?.clipboard;
        if (clip && clip.writeText) {
            return clip.writeText(text);
        }
    } catch (err) {
        // fall through to execCommand fallback
    }

    return new Promise((resolve) => {
        const textarea = document.createElement("textarea");
        textarea.value = text || "";
        textarea.style.position = "fixed";
        textarea.style.opacity = "0";
        document.body.appendChild(textarea);
        textarea.focus();
        textarea.select();
        try {
            document.execCommand("copy");
        } finally {
            textarea.remove();
        }
        resolve();
    });
}

patch(ErrorDialog.prototype, {
    async onClickClipboard(ev) {
        ev?.preventDefault?.();
        const text = [
            this.props.name,
            "",
            this.props.message,
            "",
            this.contextDetails,
            "",
            this.traceback ?? this.props.traceback ?? "",
        ].join("\n");
        try {
            await safeCopy(text);
            this.showTooltip?.();
        } catch (err) {
            // If everything fails, at least avoid throwing in the dialog
            console.warn("Clipboard copy failed", err);
        }
    },
});
