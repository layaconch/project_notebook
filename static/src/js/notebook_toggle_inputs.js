/** Toggle collapse/expand for notebook cell inputs */
odoo.define("project_notebook.notebook_toggle_inputs", function (require) {
    "use strict";

    const { whenReady } = require("@web/core/utils/concurrency");

    function toggleAll(detailsList) {
        if (!detailsList.length) {
            return;
        }
        const shouldOpen = !detailsList[0].open;
        detailsList.forEach((el) => {
            el.open = shouldOpen;
        });
    }

    whenReady(() => {
        // Global toggle button on notebook form header
        document.addEventListener("click", (ev) => {
            const btn = ev.target.closest(".o_nb_toggle_all_inputs");
            if (!btn) return;
            const root = btn.closest(".o_form_view") || document;
            const detailsList = Array.from(
                root.querySelectorAll("details.o_nb_input_collapse")
            );
            toggleAll(detailsList);
        });

        // Per-cell toggle via summary click (native)
        // No extra code needed; native <details> handles it.
    });
});
