// =============================================================================
// WEEK 14: JavaScript on the WEBSITE -> an Interaction (Odoo 18+/19)
// =============================================================================
// The backend web client is one big OWL app. The website is server-rendered
// HTML (QWeb), and JS is attached to it with "interactions":
//
//   static selector   -> one instance per matching element (this.el)
//   dynamicContent    -> declarative t-on-* / t-att-* / t-out bound to selectors
//   setup() / start() -> lifecycle; this.services gives the same services
//                        as the backend (orm, notification, datetime_picker...)
//   registerCleanup() -> undo what you did (edit mode destroys interactions)
//
// This one turns the "Return by" text input of the book request form into a
// datepicker with the library rules (no Fridays, max N days) and keeps an
// ISO date (YYYY-MM-DD) in a hidden input for the controller.
// =============================================================================
import { formatDate, serializeDate, today } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class BookRequestForm extends Interaction {
    static selector = ".o_library_request_form";

    dynamicContent = {
        ".o_library_return_input": {
            "t-att-class": () => ({ "is-invalid": !!this.error, "is-valid": !!this.date && !this.error }),
        },
        ".o_library_return_iso": {
            "t-att-value": () => (this.date && !this.error ? serializeDate(this.date) : ""),
        },
        ".o_library_return_hint": { "t-out": () => this.hint },
        ".o_library_return_error": { "t-out": () => this.error },
        "button[type='submit']": { "t-att-disabled": () => !!this.error },
    };

    setup() {
        // Rules come from data-* attributes rendered by QWeb.
        const { maxDays, defaultDays, closedWeekdays } = this.el.dataset;
        this.maxDays = parseInt(maxDays || "30");
        this.closedWeekdays = (closedWeekdays || "").split(",").filter(Boolean).map(Number);
        this.inputEl = this.el.querySelector(".o_library_return_input");
        this.date = this.nextOpenDay(today().plus({ days: parseInt(defaultDays || "14") }));
        this.validate();
    }

    start() {
        this.inputEl.value = formatDate(this.date);
        const picker = this.services.datetime_picker.create({
            target: this.inputEl,
            pickerProps: {
                type: "date",
                value: this.date,
                minDate: today().plus({ days: 1 }),
                maxDate: today().plus({ days: this.maxDays }),
                isDateValid: (date) => !this.isClosed(date),
                dayCellClass: (date) => (this.isClosed(date) ? "o_library_closed_day" : ""),
            },
            // Called after a click in the calendar AND after typing + blur.
            // We are outside dynamicContent handlers, so refresh by hand.
            onApply: (date) => {
                this.date = date || null;
                this.validate();
                this.updateContent();
            },
        });
        this.registerCleanup(picker.enable());
    }

    isClosed(date) {
        return this.closedWeekdays.includes(date.weekday);
    }

    nextOpenDay(date) {
        for (let i = 0; i < 7 && this.isClosed(date); i++) {
            date = date.plus({ days: 1 });
        }
        return date;
    }

    validate() {
        this.error = "";
        this.hint = "";
        if (!this.date) {
            this.hint = _t("No date chosen: the librarian will use the default loan period.");
            return;
        }
        const days = Math.round(this.date.diff(today(), "days").days);
        if (days < 1) {
            this.error = _t("Pick a date after today.");
        } else if (days > this.maxDays) {
            this.error = _t("You can borrow a book for at most %s days.", this.maxDays);
        } else if (this.isClosed(this.date)) {
            this.error = _t("The library is closed that day.");
        } else {
            this.hint = _t("You will keep the book for %s day(s).", days);
        }
    }
}

registry.category("public.interactions").add("library_management.book_request_form", BookRequestForm);
