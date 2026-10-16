// =============================================================================
// WEEK 14 HANDS-ON: a custom datepicker widget -> widget="library_due_date"
// =============================================================================
// What it adds on top of the standard `date` widget:
//   * the calendar refuses dates before the start date (borrow date)
//   * closed weekdays (e.g. Friday) are disabled and styled in the calendar
//   * quick-pick buttons: +7d / +14d / +21d from the start date
//   * a live Bootstrap badge: "Due in 3 days" / "Due today" / "Overdue by 2 days"
//
// We do NOT write a calendar ourselves: we reuse Odoo's <DateTimeInput/>
// (an <input> + the datetime_picker popover) and pass it extra props:
//   minDate, isDateValid(date) and dayCellClass(date).
//
// Usage (see views/borrowing_widget_views.xml):
//   <field name="expected_return_date" widget="library_due_date"
//          options="{'start_field': 'borrow_date', 'done_field': 'return_date',
//                    'closed_weekdays': [5], 'quick_days': [7, 14, 21]}"/>
//
// Weekday numbers are ISO (luxon `date.weekday`): 1 = Monday ... 7 = Sunday.
// Python's date.isoweekday() uses the same numbers, handy for server checks.
// =============================================================================
import { Component } from "@odoo/owl";
import { DateTimeInput } from "@web/core/datetime/datetime_input";
import { formatDate, today } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class DueDateField extends Component {
    static template = "library_management.DueDateField";
    static components = { DateTimeInput };
    static props = {
        ...standardFieldProps,
        startField: { type: String, optional: true },
        doneField: { type: String, optional: true },
        closedWeekdays: { type: Array, element: Number, optional: true },
        quickDays: { type: Array, element: Number, optional: true },
        placeholder: { type: String, optional: true },
    };
    static defaultProps = {
        closedWeekdays: [],
        quickDays: [7, 14, 21],
    };

    setup() {
        // Callbacks handed to the picker. Arrow functions keep `this`.
        this.isDateValid = (date) => !this.isClosed(date);
        this.dayCellClass = (date) => {
            if (this.isClosed(date)) {
                return "o_library_closed_day";
            }
            if (this.startDate && date.hasSame(this.startDate, "day")) {
                return "o_library_start_day";
            }
            return "";
        };
    }

    // -------------------------------------------------------------------------
    // Getters: read from the record, never keep a copy of the value
    // -------------------------------------------------------------------------

    /** @returns {luxon.DateTime | false} Date fields arrive as luxon DateTime */
    get value() {
        return this.props.record.data[this.props.name];
    }

    get startDate() {
        return (this.props.startField && this.props.record.data[this.props.startField]) || false;
    }

    get isDone() {
        return Boolean(this.props.doneField && this.props.record.data[this.props.doneField]);
    }

    get formattedValue() {
        return formatDate(this.value);
    }

    get quickPicks() {
        const base = this.startDate || today();
        return this.props.quickDays.map((days) => {
            const date = this.nextOpenDay(base.plus({ days }));
            return {
                days,
                date,
                title: formatDate(date),
                isActive: Boolean(this.value && this.value.hasSame(date, "day")),
            };
        });
    }

    /** Badge shown under the input: null when there is nothing to say. */
    get status() {
        if (!this.value || this.isDone) {
            return null;
        }
        const days = Math.round(this.value.diff(today(), "days").days);
        if (days < 0) {
            return { className: "text-bg-danger", label: _t("Overdue by %s day(s)", -days) };
        }
        if (days === 0) {
            return { className: "text-bg-warning", label: _t("Due today") };
        }
        if (days <= 3) {
            return { className: "text-bg-warning", label: _t("Due in %s day(s)", days) };
        }
        return { className: "text-bg-success", label: _t("Due in %s days", days) };
    }

    // -------------------------------------------------------------------------
    // Helpers
    // -------------------------------------------------------------------------

    isClosed(date) {
        return this.props.closedWeekdays.includes(date.weekday);
    }

    nextOpenDay(date) {
        // At most 7 tries, in case someone closes every day of the week.
        for (let i = 0; i < 7 && this.isClosed(date); i++) {
            date = date.plus({ days: 1 });
        }
        return date;
    }

    // -------------------------------------------------------------------------
    // Handlers: the ONLY way to change the value is record.update()
    // -------------------------------------------------------------------------

    async onApply(date) {
        await this.props.record.update({ [this.props.name]: date || false });
    }
}

export const dueDateField = {
    component: DueDateField,
    displayName: _t("Library Due Date"),
    supportedTypes: ["date"],
    // Shown in Studio / the debug "widget options" helper
    supportedOptions: [
        { label: _t("Start date field"), name: "start_field", type: "field", availableTypes: ["date"] },
        { label: _t("Done date field"), name: "done_field", type: "field", availableTypes: ["date"] },
    ],
    extractProps: ({ options, placeholder }) => ({
        startField: options.start_field,
        doneField: options.done_field,
        closedWeekdays: options.closed_weekdays,
        quickDays: options.quick_days,
        placeholder,
    }),
    // Load these fields even if the view does not display them
    fieldDependencies: ({ options }) =>
        [options.start_field, options.done_field]
            .filter(Boolean)
            .map((name) => ({ name, type: "date" })),
};

registry.category("fields").add("library_due_date", dueDateField);
