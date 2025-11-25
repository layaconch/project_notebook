/** @odoo-module **/
"use strict";

const domReady = require("web.dom_ready");

function toggleSingle(btn) {
    const card = btn.closest(".o_nb_cell");
    const details = card && card.querySelector(".o_nb_input_collapse");
    if (!details) {
        return;
    }
    details.open = !details.open;
    btn.textContent = details.open ? "收起输入" : "展开输入";
}

function toggleAll(root, open) {
    root.querySelectorAll(".o_nb_input_collapse").forEach((d) => {
        d.open = open;
    });
    root.querySelectorAll(".o_nb_toggle_inputs").forEach((b) => {
        b.textContent = open ? "收起输入" : "展开输入";
    });
}

domReady(function () {
    const root = document.querySelector(".o_devops_nb_main");
    if (!root) {
        return;
    }

    // Capture phase handler to block kanban/open click before Odoo catches it.
    const blockOpen = (ev) => {
        const inCell = ev.target.closest(".o_nb_cell");
        if (!inCell) {
            return;
        }
        // Block default kanban open; allow inline editing/buttons to handle their own logic.
        ev.preventDefault();
        ev.stopPropagation();
        if (ev.stopImmediatePropagation) {
            ev.stopImmediatePropagation();
        }
    };

    ["click", "mousedown", "mouseup", "touchstart"].forEach((etype) => {
        document.addEventListener(etype, blockOpen, true);
    });

    root.addEventListener("click", (ev) => {
        const toggleBtn = ev.target.closest(".o_nb_toggle_inputs");
        if (toggleBtn) {
            ev.preventDefault();
            ev.stopPropagation(); // avoid opening modal
            if (ev.stopImmediatePropagation) {
                ev.stopImmediatePropagation();
            }
            toggleSingle(toggleBtn);
            return;
        }
        const toggleAllBtn = ev.target.closest(".o_nb_toggle_all_inputs");
        if (toggleAllBtn) {
            ev.preventDefault();
            ev.stopPropagation();
            if (ev.stopImmediatePropagation) {
                ev.stopImmediatePropagation();
            }
            const hasClosed = !!root.querySelector(".o_nb_input_collapse:not([open])");
            toggleAll(root, hasClosed);
            toggleAllBtn.textContent = hasClosed ? "全部收起输入" : "全部展开输入";
        }
    });

    // Block record open; allow explicit buttons/inputs to work.
    root.addEventListener(
        "click",
        (ev) => {
            const record = ev.target.closest(".o_kanban_record");
            if (!record) {
                return;
            }
            // Allow summary to toggle details but don't bubble to open record.
            if (ev.target.closest("summary")) {
                ev.stopPropagation();
                return;
            }
            // Allow action buttons/inputs/links to work as usual.
            if (ev.target.closest("button, a, input, textarea, select, summary")) {
                return;
            }
            ev.preventDefault();
            ev.stopPropagation();
            if (ev.stopImmediatePropagation) {
                ev.stopImmediatePropagation();
            }
        },
        true
    );
});
