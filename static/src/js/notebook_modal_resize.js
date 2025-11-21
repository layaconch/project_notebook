/** @odoo-module **/

import { whenReady } from "@odoo/owl";

const TEXTAREA_SELECTOR = ".o_nb_modal_input textarea";
const MODAL_SELECTOR = ".modal";
const MODAL_DIALOG_SELECTOR = ".modal-dialog";
const MAX_BTN_CLASS = "o_nb_modal_maximize_btn";

function adjustModalSize(modalDialog) {
    if (!modalDialog || modalDialog.classList.contains("o_nb_maximized")) {
        return;
    }
    const textarea = modalDialog.querySelector(TEXTAREA_SELECTOR);
    if (!textarea) {
        return;
    }
    const padding = 200;
    const maxWidth = window.innerWidth * 0.9;
    const maxHeight = window.innerHeight * 0.9;
    const newWidth = Math.min(maxWidth, textarea.offsetWidth + padding);
    const newHeight = Math.min(maxHeight, textarea.offsetHeight + padding);
    modalDialog.style.width = `${newWidth}px`;
    modalDialog.style.height = `${newHeight}px`;
}

function toggleMaximize(modal, modalDialog) {
    if (!modal || !modalDialog) {
        return;
    }
    if (modal.classList.toggle("o_nb_modal_fullscreen")) {
        modalDialog.classList.add("o_nb_maximized");
        modalDialog.style.width = "";
        modalDialog.style.height = "";
    } else {
        modalDialog.classList.remove("o_nb_maximized");
        adjustModalSize(modalDialog);
    }
}

function enhanceModal(modalDialog) {
    if (!modalDialog || modalDialog.dataset.nbEnhanced) {
        return;
    }
    const textarea = modalDialog.querySelector(TEXTAREA_SELECTOR);
    if (!textarea) {
        return;
    }
    modalDialog.dataset.nbEnhanced = "1";

    const header = modalDialog.querySelector(".modal-header");
    if (header && !header.querySelector(`.${MAX_BTN_CLASS}`)) {
        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = `btn btn-light btn-sm ${MAX_BTN_CLASS}`;
        btn.title = "最大化";
        btn.textContent = "⛶";
        const closeBtn = header.querySelector(".btn-close");
        if (closeBtn) {
            header.insertBefore(btn, closeBtn);
        } else {
            header.appendChild(btn);
        }
    }

    adjustModalSize(modalDialog);
    if (window.ResizeObserver) {
        const observer = new ResizeObserver(() => adjustModalSize(modalDialog));
        observer.observe(textarea);
        modalDialog._nbResizeObserver = observer;
    }
}

function cleanupModal(modalDialog) {
    if (modalDialog && modalDialog._nbResizeObserver) {
        modalDialog._nbResizeObserver.disconnect();
        delete modalDialog._nbResizeObserver;
    }
}

whenReady(() => {
    document.addEventListener(
        "click",
        (ev) => {
            const btn = ev.target.closest(`.${MAX_BTN_CLASS}`);
            if (btn) {
                const modal = btn.closest(MODAL_SELECTOR);
                const dialog = modal && modal.querySelector(MODAL_DIALOG_SELECTOR);
                toggleMaximize(modal, dialog);
            }
        },
        true
    );

    const observer = new MutationObserver((mutations) => {
        for (const mutation of mutations) {
            mutation.addedNodes.forEach((node) => {
                if (node instanceof HTMLElement) {
                    if (node.matches(MODAL_SELECTOR)) {
                        const dialog = node.querySelector(MODAL_DIALOG_SELECTOR);
                        enhanceModal(dialog);
                    } else {
                        node.querySelectorAll(MODAL_DIALOG_SELECTOR).forEach(enhanceModal);
                    }
                }
            });
            mutation.removedNodes.forEach((node) => {
                if (node instanceof HTMLElement) {
                    if (node.matches(MODAL_DIALOG_SELECTOR)) {
                        cleanupModal(node);
                    } else {
                        node.querySelectorAll(MODAL_DIALOG_SELECTOR).forEach(cleanupModal);
                    }
                }
            });
        }
    });

    observer.observe(document.body, { childList: true, subtree: true });
    document.querySelectorAll(MODAL_DIALOG_SELECTOR).forEach(enhanceModal);
});
