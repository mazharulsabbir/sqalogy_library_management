// =============================================================================
// WEEK 14: an OWL component that talks to the server
// =============================================================================
//   useService("orm")  -> call Python methods (here an @api.model method)
//   onWillStart        -> async work BEFORE the first render
//   onWillUpdateProps  -> reload when the list re-renders (new search, edit...)
//   this.env.searchModel -> the search panel of the current view: we toggle
//                           the filters declared in the search view XML
// =============================================================================
import { Component, onWillStart, onWillUpdateProps, useState } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class BorrowingDashboard extends Component {
    static template = "library_management.BorrowingDashboard";
    static props = { list: { type: Object, optional: true } };

    setup() {
        this.orm = useService("orm");
        this.state = useState({ data: {} });
        onWillStart(() => this.load());
        onWillUpdateProps(() => this.load());
    }

    async load() {
        this.state.data = await this.orm.call("library.borrowing", "get_library_dashboard", []);
    }

    get cards() {
        const data = this.state.data;
        return [
            { filter: "borrowed", label: _t("On loan"), value: data.active, color: "primary", icon: "fa-book" },
            { filter: "due_this_week", label: _t("Due in 7 days"), value: data.due_soon, color: "warning", icon: "fa-clock-o" },
            { filter: "late", label: _t("Late"), value: data.late, color: "danger", icon: "fa-exclamation-triangle" },
            { filter: "returned_this_month", label: _t("Returned this month"), value: data.returned_month, color: "success", icon: "fa-check" },
        ];
    }

    /** Replace the current search with the filter named `filterName`. */
    applyFilter(filterName) {
        const searchModel = this.env.searchModel;
        const [item] = searchModel.getSearchItems((item) => item.name === filterName);
        if (!item) {
            return;
        }
        searchModel.query = [];
        searchModel.toggleSearchItem(item.id);
    }
}
