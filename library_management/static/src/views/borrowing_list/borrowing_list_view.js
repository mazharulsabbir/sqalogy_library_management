// =============================================================================
// WEEK 14: Extending Views with JavaScript -> js_class
// =============================================================================
// A view type ("list", "form", "kanban"...) is a descriptor object in the
// "views" registry: { type, Controller, Renderer, Model, ArchParser, ... }.
// To customise ONE view (not all list views!) we:
//   1. subclass the piece we need (here the Renderer)
//   2. spread the original descriptor and swap that piece
//   3. register it under a new key
//   4. opt in from the XML arch: <list js_class="library_borrowing_list">
// =============================================================================
import { registry } from "@web/core/registry";
import { ListRenderer } from "@web/views/list/list_renderer";
import { listView } from "@web/views/list/list_view";
import { BorrowingDashboard } from "./borrowing_dashboard";

export class BorrowingListRenderer extends ListRenderer {
    // Template = web.ListRenderer + our dashboard (t-inherit-mode="primary")
    static template = "library_management.BorrowingListRenderer";
    static components = { ...ListRenderer.components, BorrowingDashboard };
}

export const borrowingListView = {
    ...listView,
    Renderer: BorrowingListRenderer,
};

registry.category("views").add("library_borrowing_list", borrowingListView);
