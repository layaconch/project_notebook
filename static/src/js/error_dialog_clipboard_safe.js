/** @odoo-module **/

import { patch } from "@web/core/utils/patch";
import { ErrorDialog, RPCErrorDialog } from "@web/core/errors/error_dialogs";
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

function buildText(props) {
    return [
        props.name,
        "",
        props.message,
        "",
        props.contextDetails,
        "",
        props.traceback ?? "",
    ].join("\n");
}

patch(ErrorDialog.prototype, {
    async onClickClipboard(ev) {
        ev?.preventDefault?.();
        const text = buildText({
            name: this.props.name,
            message: this.props.message,
            contextDetails: this.contextDetails,
            traceback: this.traceback ?? this.props.traceback,
        });
        try {
            await safeCopy(text);
            this.showTooltip?.();
        } catch (err) {
            // If everything fails, at least avoid throwing in the dialog
            console.warn("Clipboard copy failed", err);
        }
    },
});

patch(RPCErrorDialog.prototype, {
    async onClickClipboard(ev) {
        ev?.preventDefault?.();
        const text = buildText({
            name: this.props.name,
            message: this.props.message,
            contextDetails: this.props.contextDetails || this.contextDetails,
            traceback: this.props.traceback,
        });
        try {
            await safeCopy(text);
            this.showTooltip?.();
        } catch (err) {
            console.warn("Clipboard copy failed", err);
        }
    },
});
