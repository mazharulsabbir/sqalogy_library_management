// =============================================================================
// WEEK 14: Creating a Custom Widget (step 1: the smallest useful field widget)
// =============================================================================
// A field widget is an OWL component + a registry entry:
//
//   1. Component  -> receives `record` and `name` (standardFieldProps) and
//                    reads the value with this.props.record.data[this.props.name]
//   2. Template   -> QWeb (OWL flavour) in a .xml file next to the .js
//   3. Registry   -> registry.category("fields").add("<widget name>", {...})
//
// Usage in a view:
//   <field name="days_borrowed" widget="library_days_badge"
//          options="{'warn_after': 14, 'danger_after': 30}"/>
// =============================================================================
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class DaysBadgeField extends Component {
    static template = "library_management.DaysBadgeField";
    // standardFieldProps = record, name, readonly, id, ... (what every field gets)
    static props = {
        ...standardFieldProps,
        warnAfter: { type: Number, optional: true },
        dangerAfter: { type: Number, optional: true },
    };
    static defaultProps = {
        warnAfter: 14,
        dangerAfter: 30,
    };

    get days() {
        return this.props.record.data[this.props.name] || 0;
    }

    get badgeClass() {
        if (this.days >= this.props.dangerAfter) {
            return "text-bg-danger";
        }
        if (this.days >= this.props.warnAfter) {
            return "text-bg-warning";
        }
        return "text-bg-success";
    }

    get label() {
        return this.days === 1 ? _t("1 day") : _t("%s days", this.days);
    }
}

// The "field descriptor": what the view needs to know about the widget.
export const daysBadgeField = {
    component: DaysBadgeField,
    displayName: _t("Days Badge"),
    supportedTypes: ["integer"],
    // XML options={...} -> component props
    extractProps: ({ options }) => ({
        warnAfter: options.warn_after,
        dangerAfter: options.danger_after,
    }),
};

registry.category("fields").add("library_days_badge", daysBadgeField);
