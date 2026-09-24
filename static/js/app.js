// static/js/app.js — shared across all three modules (AIS140, CRSC Calls, Billing)

// ---------------------------------------------------------------- History modal
function openHistoryModal(url) {
    const backdrop = document.getElementById("history-modal-backdrop");
    const body = document.getElementById("history-modal-body");
    if (!backdrop || !body) return;
    body.innerHTML = "<p>Loading history…</p>";
    backdrop.classList.add("open");
    fetch(url, { headers: { "X-Requested-With": "XMLHttpRequest" } })
        .then((res) => res.text())
        .then((html) => { body.innerHTML = html; })
        .catch(() => { body.innerHTML = "<p>Could not load history. Please try again.</p>"; });
}
function closeHistoryModal() {
    const backdrop = document.getElementById("history-modal-backdrop");
    if (backdrop) backdrop.classList.remove("open");
}
document.addEventListener("click", (e) => {
    if (e.target.matches("[data-history-url]")) {
        e.preventDefault();
        openHistoryModal(e.target.getAttribute("data-history-url"));
    }
    if (e.target.matches(".modal-backdrop") || e.target.matches(".modal-close")) {
        closeHistoryModal();
    }
});

// ---------------------------------------------------------------- Confirm-before-lock
// Any <form> with data-lock-field="fieldname" and data-lock-message="..."
// shows a confirm() dialog before submitting if that field is filled and
// not already disabled (i.e. it is about to be locked for the first time).
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("form[data-lock-field]").forEach((form) => {
        form.addEventListener("submit", (e) => {
            const fieldName = form.getAttribute("data-lock-field");
            const message = form.getAttribute("data-lock-message") || "This will be locked after submit. Continue?";
            const field = form.querySelector(`[name='${fieldName}']`);
            if (field && !field.disabled && field.value.trim()) {
                if (!window.confirm(message)) e.preventDefault();
            }
        });
    });
});

// ---------------------------------------------------------------- Remark -> comment autofill
// Any <select data-autofill-target="#id_comments" data-autofill-map='{"REMARK": "default comment"}'>
// fills the target textarea with the mapped comment when the remark changes,
// only if the target is currently empty (never overwrites something typed).
document.addEventListener("change", (e) => {
    if (!e.target.matches("[data-autofill-map]")) return;
    const map = JSON.parse(e.target.getAttribute("data-autofill-map") || "{}");
    const targetSel = e.target.getAttribute("data-autofill-target");
    const target = targetSel && document.querySelector(targetSel);
    if (!target || target.disabled) return;
    const mapped = map[e.target.value];
    if (mapped !== undefined && !target.value.trim()) {
        target.value = mapped;
    }
});

// ---------------------------------------------------------------- Dynamic (AJAX) filters
// Any <form data-live-filter data-live-target="#result-container"> re-fetches
// its action URL on every change/input (debounced for text inputs) and
// replaces the target container's HTML with the response — used for the
// live-updating Real-Time dashboards, and for VIN/PSN typeahead filters
// that only start searching once 5+ characters are typed.
function wireLiveFilterForm(form) {
    const targetSel = form.getAttribute("data-live-target");
    const target = document.querySelector(targetSel);
    if (!target) return;

    let debounceTimer = null;
    const run = () => {
        const params = new URLSearchParams(new FormData(form));
        fetch(form.getAttribute("action") + "?" + params.toString(), {
            headers: { "X-Requested-With": "XMLHttpRequest" },
        })
            .then((res) => res.text())
            .then((html) => {
                target.innerHTML = html;
                target.dispatchEvent(new CustomEvent("live-filter-updated"));
            })
            .catch(() => {});
    };

    form.querySelectorAll("select, input[type=date]").forEach((el) => {
        el.addEventListener("change", run);
    });
    // Elements associated to this form via the HTML `form="..."` attribute
    // (e.g. a bulk-search textarea living outside the <form> markup) are
    // included here too, since FormData(form) already picks them up.
    const formId = form.getAttribute("id");
    const externalFields = formId
        ? document.querySelectorAll(`[form="${formId}"]`)
        : [];
    const textLikeInputs = [
        ...form.querySelectorAll("input[type=text], input[data-typeahead], textarea"),
        ...Array.from(externalFields).filter((el) => el.matches("input[type=text], input[data-typeahead], textarea")),
    ];
    textLikeInputs.forEach((el) => {
        el.addEventListener("input", () => {
            clearTimeout(debounceTimer);
            const minChars = parseInt(el.getAttribute("data-min-chars") || "0", 10);
            if (minChars && el.value.trim().length > 0 && el.value.trim().length < minChars) return;
            debounceTimer = setTimeout(run, 350);
        });
    });
    form.addEventListener("submit", (e) => {
        // A button with its own `formaction` (e.g. "Export CSV") means this
        // submit should navigate the browser there natively, not be
        // hijacked into another AJAX live-filter refresh.
        if (e.submitter && e.submitter.hasAttribute("formaction")) return;
        e.preventDefault();
        run();
    });
}
document.addEventListener("DOMContentLoaded", () => {
    document.querySelectorAll("form[data-live-filter]").forEach(wireLiveFilterForm);
});
