# Week 14: Frontend & Widgets

## Learning Objectives

By the end of this week, you will be able to:

- Explain how Odoo's web client is built: asset bundles, ES modules, OWL components, registries and services
- Write an OWL component (template, props, state, lifecycle hooks) and call Python from it with the `orm` service
- Extend an existing view with JavaScript using `js_class` (and know when to use `patch()` instead)
- Create a custom **field widget** and pass it options from the XML view
- Use Bootstrap (grid, utilities, components, SCSS variables) in Odoo website pages, and add JS to them with an **Interaction**
- **Hands-on:** build a custom datepicker widget (`library_due_date`) with business rules, for the backend and the website

---

## Table of Contents

1. [Odoo Web Framework (JS & OWL)](#1-odoo-web-framework-js--owl)
2. [Extending Views with JavaScript](#2-extending-views-with-javascript)
3. [Creating a Custom Widget](#3-creating-a-custom-widget)
4. [Using Bootstrap in Odoo Website](#4-using-bootstrap-in-odoo-website)
5. [Hands-On: Custom Datepicker Widget](#5-hands-on-custom-datepicker-widget)
6. [Hands-on Lab Setup](#6-hands-on-lab-setup)
7. [Practice Exercises](#7-practice-exercises)
8. [Exercise Solutions](#8-exercise-solutions)
9. [Troubleshooting Cheat-sheet](#9-troubleshooting-cheat-sheet)

---

## 1. Odoo Web Framework (JS & OWL)

### 1.1 The big picture

```
Browser
├── /odoo  (backend web client)  = ONE OWL application
│     WebClient ─► ActionManager ─► View (list/form/kanban) ─► Fields (widgets)
│     loaded from bundle  web.assets_backend
│
└── /library, /my ... (website & portal) = server-rendered QWeb HTML
      + small JS "Interactions" attached to elements
      loaded from bundle  web.assets_frontend
```

| Piece | What it is | Where you meet it |
|---|---|---|
| **Asset bundle** | A named list of JS/SCSS/XML files, concatenated and minified | `'assets'` key of `__manifest__.py` |
| **ES module** | A normal `import` / `export` JS file. `@<module>/...` maps to `<module>/static/src/...` | Every `.js` file |
| **OWL** | Odoo's component framework (like a small React/Vue): class + XML template + reactive state | Components, field widgets, views |
| **Registry** | A global key → value map, split in categories (`fields`, `views`, `actions`, `services`, `public.interactions`...) | How Odoo finds your code by name |
| **Service** | A shared singleton: `orm`, `action`, `notification`, `dialog`, `datetime_picker`... | `useService("orm")` |

### 1.2 Where the files go

Week 14 adds a `static/src/` tree to our module:

```
library_management/
├── __manifest__.py                     # 'assets': {...}                 <-- NEW
├── models/borrowing_dashboard.py       # @api.model used by the dashboard <-- NEW
├── views/borrowing_widget_views.xml    # widget=..., js_class=...        <-- NEW
└── static/src/                                                           <-- NEW
    ├── fields/
    │   ├── days_badge/                 # §3 simplest custom widget
    │   │   ├── days_badge_field.js
    │   │   └── days_badge_field.xml
    │   └── due_date/                   # §5 HANDS-ON datepicker widget
    │       ├── due_date_field.js
    │       ├── due_date_field.xml
    │       └── due_date_field.scss
    ├── views/borrowing_list/           # §2 js_class: dashboard above the list
    │   ├── borrowing_dashboard.js / .xml
    │   └── borrowing_list_view.js / .xml
    ├── interactions/
    │   └── book_request_form.js        # §4/§5 website datepicker
    └── scss/
        └── library_website.scss        # §4 Bootstrap SCSS
```

### 1.3 Declaring assets

```python
'assets': {
    'web.assets_backend': [                       # the /odoo web client
        'library_management/static/src/fields/**/*',
        'library_management/static/src/views/**/*',
    ],
    'web.assets_frontend': [                      # website + portal
        'library_management/static/src/interactions/**/*',
        'library_management/static/src/scss/library_website.scss',
    ],
},
```

> **Rule of thumb:** `.js`, `.xml` (OWL templates) and `.scss` live in **bundles**, never in `'data'`.
> Server QWeb templates and views (`views/*.xml` with `<odoo>` root) live in `'data'`.
> Two kinds of XML, two different places!

| File | Root tag | Goes in |
|---|---|---|
| `views/borrowing_widget_views.xml` | `<odoo>` | `'data'` |
| `static/src/.../due_date_field.xml` | `<templates>` | `'assets'` |

### 1.4 OWL in 5 minutes

```javascript
import { Component, useState, onWillStart } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

export class BookCounter extends Component {
    static template = "library_management.BookCounter";   // name of the XML template
    static props = { title: { type: String, optional: true } };

    setup() {                                   // NOT constructor()
        this.orm = useService("orm");
        this.state = useState({ count: 0 });     // reactive: changes re-render
        onWillStart(async () => {               // runs before the first render
            this.state.count = await this.orm.call("library.book", "get_available_books_count", []);
        });
    }

    increment() {
        this.state.count++;
    }
}
```

```xml
<templates xml:space="preserve">
    <t t-name="library_management.BookCounter">
        <div class="p-3">
            <h3 t-esc="props.title or 'Available books'"/>
            <span class="badge text-bg-primary" t-esc="state.count"/>
            <button class="btn btn-link" t-on-click="increment">+1</button>
        </div>
    </t>
</templates>
```

| Concept | Syntax | Notes |
|---|---|---|
| Template | `static template = "module.Name"` | Defined in a `<templates>` XML file in the bundle |
| Props (input) | `static props = {...}`, read `this.props.x` | Validated in dev mode (`?debug=assets`) |
| State | `useState({...})` | Only reactive objects trigger re-render |
| Lifecycle | `onWillStart`, `onMounted`, `onWillUpdateProps`, `onWillUnmount` | Call them in `setup()` |
| Events | `t-on-click="method"` or `t-on-click="() => this.m(x)"` | |
| Sub-components | `static components = { Child }` → `<Child prop="value"/>` | Prop values are **JS expressions**: strings need quotes `type="'date'"` |
| Output | `t-esc` (escaped) / `t-out` | Same idea as server QWeb |

> ⚠️ OWL templates look like server QWeb but expressions are **JavaScript**, not Python:
> `t-if="a and b"` works (Odoo translates `and`/`or`/`not`), but `None`, `len(x)`, `x.mapped(...)` do not.

### 1.5 Registries

Everything is found by name in a registry:

```javascript
import { registry } from "@web/core/registry";

registry.category("fields").add("library_due_date", dueDateField);          // widget="..."
registry.category("views").add("library_borrowing_list", borrowingListView); // js_class="..."
registry.category("actions").add("library_book_counter", BookCounter);      // ir.actions.client tag
registry.category("public.interactions").add("library_management.book_request_form", BookRequestForm);
```

### 1.6 Services you will use all the time

```javascript
const orm = useService("orm");
await orm.call("library.borrowing", "get_library_dashboard", []);  // any public Python method
await orm.searchRead("library.book", [["state", "=", "available"]], ["name", "author"]);
await orm.write("library.book", [bookId], { notes: "..." });

const action = useService("action");
action.doAction("library_management.action_library_borrowing");   // xml id or action dict

const notification = useService("notification");
notification.add("Saved!", { type: "success" });
```

> `orm.call` goes through access rights like any RPC: methods starting with `_` cannot be called.

---

## 2. Extending Views with JavaScript

### 2.1 Three ways, from lightest to heaviest

| Technique | Scope | Use when |
|---|---|---|
| `widget="..."` on a `<field>` | One field | Change how a value is shown/edited (§3) |
| `js_class="..."` on the view root | One view (opt-in) | Add things around a list/form/kanban: banners, buttons, dashboards |
| `patch(Class.prototype, {...})` | **Every** instance of a class | Change core behaviour everywhere (use sparingly) |

### 2.2 A view is a descriptor

```javascript
// @web/views/list/list_view.js (simplified)
export const listView = {
    type: "list",
    Controller: ListController,     // control panel, buttons, actions
    Renderer: ListRenderer,         // the <table>
    ArchParser: ListArchParser,     // reads the XML arch
    Model: RelationalModel,         // loads/saves records
};
registry.category("views").add("list", listView);
```

To customise one view: copy the descriptor, swap one piece, register a new key.

### 2.3 Our example: a dashboard above the Borrowings list

`static/src/views/borrowing_list/borrowing_list_view.js`:

```javascript
export class BorrowingListRenderer extends ListRenderer {
    static template = "library_management.BorrowingListRenderer";
    static components = { ...ListRenderer.components, BorrowingDashboard };
}

export const borrowingListView = {
    ...listView,
    Renderer: BorrowingListRenderer,
};

registry.category("views").add("library_borrowing_list", borrowingListView);
```

`borrowing_list_view.xml` (OWL template inheritance):

```xml
<t t-name="library_management.BorrowingListRenderer" t-inherit="web.ListRenderer" t-inherit-mode="primary">
    <xpath expr="//div[hasclass('o_list_renderer')]" position="before">
        <BorrowingDashboard list="props.list"/>
    </xpath>
</t>
```

| `t-inherit-mode` | Effect |
|---|---|
| `primary` | Creates a **new** template (copy + changes). Use with a subclass. |
| `extension` | Modifies the original **in place** → every list in Odoo changes! |

Opt in from the view (`views/borrowing_widget_views.xml`):

```xml
<xpath expr="/list" position="attributes">
    <attribute name="js_class">library_borrowing_list</attribute>
</xpath>
```

### 2.4 The dashboard component

`borrowing_dashboard.js` loads numbers from Python and toggles search filters:

```javascript
setup() {
    this.orm = useService("orm");
    this.state = useState({ data: {} });
    onWillStart(() => this.load());
    onWillUpdateProps(() => this.load());   // list re-rendered (new search...) -> refresh
}

async load() {
    this.state.data = await this.orm.call("library.borrowing", "get_library_dashboard", []);
}

applyFilter(filterName) {
    const searchModel = this.env.searchModel;          // the search bar of this view
    const [item] = searchModel.getSearchItems((item) => item.name === filterName);
    searchModel.query = [];
    searchModel.toggleSearchItem(item.id);
}
```

Python side (`models/borrowing_dashboard.py`):

```python
@api.model
def get_library_dashboard(self):
    today = fields.Date.context_today(self)
    borrowed = [('state', '=', 'borrowed')]
    return {
        'active': self.search_count(borrowed),
        'late': self.search_count(borrowed + [('expected_return_date', '<', today)]),
        ...
    }
```

The card's `filter` must match a `<filter name="...">` in the search view; we added
`late`, `due_this_week` and `returned_this_month` in `borrowing_widget_views.xml`.

> 💡 Why not use `is_overdue` in the domain? It is a **non-stored** compute: you cannot search on it.
> Domains (Python or XML) must use stored fields.

### 2.5 `patch()`: changing code you do not own

```javascript
import { patch } from "@web/core/utils/patch";
import { FormController } from "@web/views/form/form_controller";

patch(FormController.prototype, {
    setup() {
        super.setup(...arguments);          // ALWAYS call super
        console.log("Form opened for", this.props.resModel);
    },
});
```

This runs for **every** form in the database (sales, invoices, contacts...).
Prefer `js_class` unless you really need global behaviour.

---

## 3. Creating a Custom Widget

### 3.1 Anatomy of a field widget

A field widget = **component** + **descriptor** registered in `registry.category("fields")`.

```
<field name="days_borrowed" widget="library_days_badge" options="{'warn_after': 14}"/>
                                     │                         │
            registry.category("fields").get("library_days_badge")
                                     │                         │
          descriptor.component ◄─────┘   descriptor.extractProps({ options }) ─► props
```

Every field component receives `standardFieldProps`:

| Prop | Meaning |
|---|---|
| `record` | The record (`record.data`, `record.update()`, `record.fields`) |
| `name` | The field name → value is `this.props.record.data[this.props.name]` |
| `readonly` | Read-only rendering (list rows, `readonly="..."` in XML) |
| `id` | DOM id (for `<label for=...>`) |

### 3.2 Step 1: a read-only badge (`library_days_badge`)

`static/src/fields/days_badge/days_badge_field.js`:

```javascript
export class DaysBadgeField extends Component {
    static template = "library_management.DaysBadgeField";
    static props = {
        ...standardFieldProps,
        warnAfter: { type: Number, optional: true },
        dangerAfter: { type: Number, optional: true },
    };
    static defaultProps = { warnAfter: 14, dangerAfter: 30 };

    get days() {
        return this.props.record.data[this.props.name] || 0;
    }

    get badgeClass() {
        if (this.days >= this.props.dangerAfter) return "text-bg-danger";
        if (this.days >= this.props.warnAfter) return "text-bg-warning";
        return "text-bg-success";
    }
}

export const daysBadgeField = {
    component: DaysBadgeField,
    displayName: _t("Days Badge"),
    supportedTypes: ["integer"],
    extractProps: ({ options }) => ({
        warnAfter: options.warn_after,
        dangerAfter: options.danger_after,
    }),
};

registry.category("fields").add("library_days_badge", daysBadgeField);
```

```xml
<t t-name="library_management.DaysBadgeField">
    <span class="badge rounded-pill" t-att-class="badgeClass" t-esc="label"/>
</t>
```

Use it:

```xml
<field name="days_borrowed" widget="library_days_badge"
       options="{'warn_after': 14, 'danger_after': 30}"/>
```

### 3.3 Editable widgets: the golden rule

> **Never keep your own copy of the value.** Read it from `record.data`, write it with
> `await this.props.record.update({ [this.props.name]: newValue })`.
> The record handles onchange, dirty state, save and discard for you.

| Field type | Value in `record.data` | Write with |
|---|---|---|
| `char`, `text`, `selection` | string / `false` | string |
| `integer`, `float`, `monetary` | number | number |
| `boolean` | `true`/`false` | boolean |
| `date`, `datetime` | luxon `DateTime` / `false` | luxon `DateTime` |
| `many2one` | `{ id, display_name }` / `false` | `{ id, display_name }` |

### 3.4 Descriptor keys you will use

| Key | Purpose |
|---|---|
| `component` | The OWL class |
| `displayName` | Label in Studio / debug widget list |
| `supportedTypes` | Field types allowed (`["date"]`) |
| `extractProps({ attrs, options, placeholder, ... }, dynamicInfo)` | XML → props |
| `supportedOptions` | Documents the options (shown in Studio) |
| `fieldDependencies` | Extra fields to load even if not in the view |

---

## 4. Using Bootstrap in Odoo Website

### 4.1 Bootstrap 5 is already there

Both bundles ship **Bootstrap 5** (CSS **and** JS). In templates you only write classes:

| Need | Bootstrap |
|---|---|
| Layout | `container`, `row`, `col-12 col-md-6 col-lg-4`, `g-4` (gutters) |
| Spacing | `m-0`, `mt-3`, `px-2`, `py-4`, `gap-2` |
| Flexbox | `d-flex`, `align-items-center`, `justify-content-between`, `flex-column` |
| Text | `text-muted`, `fw-bold`, `small`, `text-truncate`, `fs-4` |
| Colours | `text-bg-success`, `bg-light`, `border-danger`, `link-secondary` |
| Responsive | `d-none d-md-block` (hide on phone), `col-6 col-md-3` |
| Components | `card`, `badge`, `alert`, `btn`, `list-group`, `input-group`, `collapse`, `modal` |
| Forms | `form-control`, `form-label`, `form-text`, `is-invalid` + `invalid-feedback` |

### 4.2 Components that need no JavaScript

Bootstrap's JS plugins are driven by `data-bs-*` attributes. Our book page uses a **collapse**:

```xml
<a class="link-secondary small" data-bs-toggle="collapse" href="#library_borrowing_rules"
   role="button" aria-expanded="false" aria-controls="library_borrowing_rules">
    <i class="fa fa-info-circle"/> Borrowing rules
</a>
<div class="collapse" id="library_borrowing_rules">
    <ul class="list-group list-group-flush small">
        <li class="list-group-item d-flex justify-content-between bg-transparent">
            Maximum loan <span class="badge text-bg-secondary">30 days</span>
        </li>
        ...
    </ul>
</div>
```

Same idea for `data-bs-toggle="modal"`, `"tab"`, `"dropdown"`.

### 4.3 Forms with validation styles

The request form (`views/website_templates.xml`) uses an `input-group` with feedback:

```xml
<div class="input-group has-validation">
    <span class="input-group-text"><i class="fa fa-calendar"/></span>
    <input id="library_return_date" class="form-control o_library_return_input"/>
    <div class="invalid-feedback o_library_return_error"/>   <!-- visible when input has .is-invalid -->
</div>
<div class="form-text o_library_return_hint"/>
```

Our JS only toggles `is-invalid` / `is-valid`. Bootstrap does the red border and shows the message.

### 4.4 SCSS: use the theme's variables

`static/src/scss/library_website.scss` (in `web.assets_frontend`):

```scss
.o_library_book_card {
    transition: transform 0.15s ease-in-out, box-shadow 0.15s ease-in-out;

    @include media-breakpoint-up(md) {        // Bootstrap mixin
        &:hover {
            transform: translateY(-4px);
            box-shadow: $box-shadow-lg !important;   // Bootstrap variable
        }
    }
}
```

> Use `$primary`, `$danger`, `$spacer`... instead of hex colours: they follow the colours chosen in
> **Website → Theme**, so your page stays on-brand when the theme changes.

### 4.5 JavaScript on the website: Interactions (Odoo 18+/19)

The website is not an OWL app. JS is attached to HTML elements with an **Interaction**:

```javascript
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

export class BookRequestForm extends Interaction {
    static selector = ".o_library_request_form";       // one instance per matching element

    dynamicContent = {                                  // declarative bindings, OWL-like
        ".o_library_return_input": {
            "t-att-class": () => ({ "is-invalid": !!this.error }),
        },
        ".o_library_return_hint": { "t-out": () => this.hint },
        "button[type='submit']": { "t-att-disabled": () => !!this.error },
    };

    setup() { /* read this.el.dataset, init state */ }
    start() { /* after setup: attach plugins, use this.services */ }
}

registry.category("public.interactions").add("library_management.book_request_form", BookRequestForm);
```

| Interaction API | Meaning |
|---|---|
| `this.el` | The matched element |
| `this.services` | Same services as the backend (`orm`, `notification`, `datetime_picker`...) |
| `dynamicContent` | `t-on-*`, `t-att-*`, `t-out`, `t-component` per CSS selector |
| `this.updateContent()` | Re-apply `dynamicContent` after a change made **outside** a `t-on-*` handler |
| `this.registerCleanup(fn)` | Undo on destroy (the website editor destroys/restarts interactions) |
| `this.waitFor(promise)` | Await safely (ignored if the interaction was destroyed) |

> 🕰️ Before Odoo 18 this was `publicWidget.Widget.extend({ selector, events, start })`.
> You will still see it in old tutorials and modules; in Odoo 19 write Interactions.

---

## 5. Hands-On: Custom Datepicker Widget

**Goal:** replace the plain `expected_return_date` date field on borrowings with
`widget="library_due_date"`:

- the calendar refuses dates before the **borrow date**
- **Fridays** (library closed) are disabled and struck through
- quick buttons **+7d / +14d / +21d** (counted from the borrow date, skipping Fridays)
- a live badge: *Due in 9 days* / *Due today* / *Overdue by 2 day(s)*
- read-only mode (list, returned borrowings): text + badge, no input

We will **not** draw a calendar ourselves. Odoo already has one:

| Building block | Import | What it gives |
|---|---|---|
| `DateTimeInput` | `@web/core/datetime/datetime_input` | `<input>` + calendar popover, parses/formats with the user's language |
| `useDateTimePicker` | `@web/core/datetime/datetime_picker_hook` | Lower level: attach the popover to your own `<input t-ref="start-date">` |
| `datetime_picker` service | `this.services.datetime_picker` / `useService` | Lowest level, no OWL needed (used on the website) |
| `@web/core/l10n/dates` | `formatDate`, `parseDate`, `serializeDate`, `today()` | Conversions; dates are **luxon** `DateTime` |

Picker props we use: `type`, `value`, `minDate`, `maxDate`, `isDateValid(date)`, `dayCellClass(date)`, plus `onApply(value)`.

### Step 1: skeleton that shows the value

`static/src/fields/due_date/due_date_field.js`:

```javascript
import { Component } from "@odoo/owl";
import { formatDate } from "@web/core/l10n/dates";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class DueDateField extends Component {
    static template = "library_management.DueDateField";
    static props = { ...standardFieldProps };

    get value() {
        return this.props.record.data[this.props.name];   // luxon DateTime or false
    }

    get formattedValue() {
        return formatDate(this.value);                      // "" when false
    }
}

export const dueDateField = {
    component: DueDateField,
    displayName: _t("Library Due Date"),
    supportedTypes: ["date"],
};

registry.category("fields").add("library_due_date", dueDateField);
```

`due_date_field.xml`:

```xml
<templates xml:space="preserve">
    <t t-name="library_management.DueDateField">
        <span t-esc="formattedValue"/>
    </t>
</templates>
```

In `views/borrowing_widget_views.xml`:

```xml
<xpath expr="//group//field[@name='expected_return_date']" position="attributes">
    <attribute name="widget">library_due_date</attribute>
</xpath>
```

Upgrade the module, hard-refresh the browser (`Ctrl+Shift+R`), open a borrowing. ✅ The date shows, but you cannot edit it yet.

> Why `//group//field[...]`? The form contains **two** `expected_return_date` fields: one in the red
> OVERDUE banner and one in the group. A plain `<field name=... position=...>` matches the first one only.

### Step 2: make it editable with `DateTimeInput`

```javascript
import { DateTimeInput } from "@web/core/datetime/datetime_input";

export class DueDateField extends Component {
    static components = { DateTimeInput };
    ...
    async onApply(date) {
        await this.props.record.update({ [this.props.name]: date || false });
    }
}
```

```xml
<t t-name="library_management.DueDateField">
    <div class="o_library_due_date w-100">
        <span t-if="props.readonly" t-esc="formattedValue"/>
        <DateTimeInput t-else=""
                       id="props.id"
                       type="'date'"
                       value="value"
                       onApply.bind="onApply"/>
    </div>
</t>
```

✅ Click the input → calendar. Pick a date → the form becomes dirty → Save.

> `type="'date'"`: prop values are **JS expressions**. `type="date"` would look for a variable called `date`.
> `onApply.bind="onApply"` binds `this` for you (same as `() => this.onApply(...)`).

### Step 3: business rules in the calendar

Read the start date from another field of the same record, and give the picker two callbacks:

```javascript
static props = {
    ...standardFieldProps,
    startField: { type: String, optional: true },
    closedWeekdays: { type: Array, element: Number, optional: true },
};
static defaultProps = { closedWeekdays: [] };

setup() {
    // Arrow functions: the picker calls them without `this`
    this.isDateValid = (date) => !this.isClosed(date);
    this.dayCellClass = (date) => (this.isClosed(date) ? "o_library_closed_day" : "");
}

get startDate() {
    return (this.props.startField && this.props.record.data[this.props.startField]) || false;
}

isClosed(date) {
    return this.props.closedWeekdays.includes(date.weekday);   // 1 = Monday ... 7 = Sunday
}
```

```xml
<DateTimeInput ... minDate="startDate" isDateValid="isDateValid" dayCellClass="dayCellClass"/>
```

Style the closed days. The popover is rendered **outside** the field (in the overlay container), so the
selector must be global (`due_date_field.scss`):

```scss
.o_date_item_cell.o_library_closed_day {
    color: $danger;
    text-decoration: line-through;
}
```

Connect the options with `extractProps`:

```javascript
extractProps: ({ options }) => ({
    startField: options.start_field,
    closedWeekdays: options.closed_weekdays,
}),
```

```xml
<attribute name="options">{'start_field': 'borrow_date', 'closed_weekdays': [5]}</attribute>
```

✅ Days before the borrow date and all Fridays are greyed out and cannot be clicked.

> 💡 ISO weekday numbers are the same in JS (luxon `date.weekday`) and Python (`date.isoweekday()`):
> 5 = Friday on both sides. Handy for server-side checks (Exercise 4).

### Step 4: quick-pick buttons

```javascript
static props = { ..., quickDays: { type: Array, element: Number, optional: true } };
static defaultProps = { closedWeekdays: [], quickDays: [7, 14, 21] };

nextOpenDay(date) {
    for (let i = 0; i < 7 && this.isClosed(date); i++) {
        date = date.plus({ days: 1 });
    }
    return date;
}

get quickPicks() {
    const base = this.startDate || today();
    return this.props.quickDays.map((days) => {
        const date = this.nextOpenDay(base.plus({ days }));
        return { days, date, title: formatDate(date),
                 isActive: Boolean(this.value && this.value.hasSame(date, "day")) };
    });
}
```

```xml
<t t-foreach="quickPicks" t-as="pick" t-key="pick.days">
    <button type="button" class="btn btn-sm o_library_quick_pick"
            t-att-class="pick.isActive ? 'btn-primary' : 'btn-outline-secondary'"
            t-att-title="pick.title"
            t-on-click="() => this.onApply(pick.date)">
        +<t t-esc="pick.days"/>d
    </button>
</t>
```

✅ Clicking **+14d** writes the date through `onApply` → `record.update`, and the input follows automatically
(the input re-renders from `value`, we never touched the `<input>` ourselves).

> Always `type="button"` inside a form: a `<button>` without type is a **submit** button.

### Step 5: live status badge + read-only mode

```javascript
get status() {
    if (!this.value || this.isDone) {
        return null;
    }
    const days = Math.round(this.value.diff(today(), "days").days);
    if (days < 0) return { className: "text-bg-danger", label: _t("Overdue by %s day(s)", -days) };
    if (days === 0) return { className: "text-bg-warning", label: _t("Due today") };
    if (days <= 3) return { className: "text-bg-warning", label: _t("Due in %s day(s)", days) };
    return { className: "text-bg-success", label: _t("Due in %s days", days) };
}
```

`isDone` reads a second optional field (`done_field: 'return_date'`): a returned book is never "overdue".

```xml
<t t-if="props.readonly">
    <div class="d-flex align-items-center gap-2">
        <span t-esc="formattedValue"/>
        <span t-if="status" class="badge rounded-pill" t-att-class="status.className" t-esc="status.label"/>
    </div>
</t>
```

✅ The list view shows `10/18/2026  [Due in 2 day(s)]`, returned borrowings show only the date.

### Step 6: make it a good citizen

```javascript
export const dueDateField = {
    component: DueDateField,
    displayName: _t("Library Due Date"),
    supportedTypes: ["date"],
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
```

Final XML (`views/borrowing_widget_views.xml`):

```xml
<attribute name="options">{
    'start_field': 'borrow_date',
    'done_field': 'return_date',
    'closed_weekdays': [5],
    'quick_days': [7, 14, 21]
}</attribute>
```

The same widget is reused on **Book Requests** with other options (`{'closed_weekdays': [5], 'quick_days': [7, 14, 30]}`).
That is the point of a widget: write once, configure per view.

The complete code is in `static/src/fields/due_date/`.

### Step 7: the same rules on the website

On the website there is no OWL form and no `record`. We use the **service** directly from the
`BookRequestForm` interaction (`static/src/interactions/book_request_form.js`):

```javascript
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
        onApply: (date) => {
            this.date = date || null;
            this.validate();
            this.updateContent();       // we are outside dynamicContent -> refresh by hand
        },
    });
    this.registerCleanup(picker.enable());
}
```

Two important details:

1. **Display format ≠ wire format.** The visible input shows `10/31/2026` (or `31/10/2026` in another
   language). The controller needs `2026-10-31`. A hidden input carries `serializeDate(this.date)`:

   ```xml
   <input type="text" class="form-control o_library_return_input"/>              <!-- for humans -->
   <input type="hidden" name="expected_return_date" class="o_library_return_iso"/> <!-- for Python -->
   ```

2. **Never trust the browser.** Anyone can POST any string, so the controller checks again
   (`library.book.request._parse_website_return_date`):

   ```python
   try:
       return_date = fields.Date.to_date(value)
   except ValueError:
       return None
   today = fields.Date.context_today(self)
   if (not return_date
           or not today < return_date <= today + timedelta(days=self._max_loan_days)
           or return_date.isoweekday() in self._closed_weekdays):
       return None
   return return_date
   ```

The rules (`_default_loan_days`, `_max_loan_days`, `_closed_weekdays`) live on the model and reach the JS
through `data-*` attributes rendered by QWeb:

```xml
<form class="... o_library_request_form"
      t-att-data-default-days="BookRequest._default_loan_days"
      t-att-data-max-days="BookRequest._max_loan_days"
      t-att-data-closed-weekdays="','.join(str(day) for day in BookRequest._closed_weekdays)">
```

```javascript
const { maxDays, defaultDays, closedWeekdays } = this.el.dataset;   // data-max-days -> maxDays
```

---

## 6. Hands-on Lab Setup

```bash
# 1. Upgrade the module
python odoo-bin -c odoo.conf -d YOUR_DB -u library_management

# 2. Run with asset debugging: readable JS, no minification, source maps
python odoo-bin -c odoo.conf -d YOUR_DB --dev xml
# then open http://localhost:8069/odoo?debug=assets
```

> JS / OWL XML / SCSS changes do **not** need a module upgrade: refresh the page with `?debug=assets`.
> Changes to the **manifest `assets` list**, Python, or `views/*.xml` need `-u` (and Python needs a restart).

Test data (Odoo shell):

```python
from datetime import timedelta
from odoo import fields
today = fields.Date.today()
book1, book2 = env['library.book'].search([('state', '=', 'available')], limit=2)
B = env['library.borrowing']
B.create({'book_id': book1.id, 'borrower_name': 'Late Reader',
          'borrow_date': today - timedelta(days=20), 'expected_return_date': today - timedelta(days=3)})
B.create({'book_id': book2.id, 'borrower_name': 'On-time Reader',
          'borrow_date': today - timedelta(days=5), 'expected_return_date': today + timedelta(days=2)})
env.cr.commit()
```

Smoke tests:

| Where | Do | Expected |
|---|---|---|
| Library → Borrowings → list view | Look above the table | 4 cards: On loan / Due in 7 days / Late / Returned this month |
| Same | Click **Late** | Search shows the *Late* facet, only late rows |
| List | Days column | Green/orange/red pill badges |
| List | Expected return column | Date + *Due in 2 day(s)* / *Overdue by 3 day(s)* |
| Borrowing form | Click the return date | Calendar: days before borrow date and Fridays disabled, Fridays struck through, borrow date circled |
| Borrowing form | Click **+14d** | Date changes, form becomes dirty, badge updates |
| Returned borrowing | Open it | Plain date, no badge, no buttons |
| Book Requests form | Return By | Same widget, buttons +7d / +14d / +30d |
| Website book page (logged in) | Look at the form | "Return by" pre-filled (14 days, moved off Friday), green border, hint text |
| Same | Open the calendar | Only tomorrow → +30 days, no Fridays |
| Same | Type a Friday date and leave the field | Red border, error message, **Send request** disabled |
| Same | Send request | Backend request has your date as *Return By* |
| Website book page | Click *Borrowing rules* | Bootstrap collapse opens |
| `/library` (desktop width) | Hover a card | Card lifts with a shadow |

Debugging tips:

- Browser console (F12) → errors with the file name. With `?debug=assets` the file names are real.
- `odoo.__WOWL_DEBUG__.root` in the console = the root OWL component of the web client.
- OWL props validation errors (`Invalid props for component 'DueDateField'`) appear only in debug mode: read them, they are precise.

---

## 7. Practice Exercises

### Exercise 1 (OWL basics): a client action
Create an `ir.actions.client` with tag `library_book_stats` and a menu **Library → Reporting → Book Stats**.
The OWL component calls `library.book.get_dashboard_data` and shows the numbers as Bootstrap cards.
Add a **Refresh** button.

### Exercise 2 (Widget): ISBN widget
Create `widget="library_isbn"` for the `isbn` Char field. In edit mode it is an `<input>`; while typing,
show a red border (`is-invalid`) if the digits are not 10 or 13. In read-only mode, show the ISBN with a
small `fa-barcode` icon.

### Exercise 3 (Widget options): maximum loan
Add an option `max_days` to `library_due_date`. When set, the calendar refuses dates later than
`start date + max_days`, and the quick-pick buttons beyond that limit are hidden.
Use it with `'max_days': 30` on borrowings.

### Exercise 4 (Server side): never trust the widget
The widget blocks Fridays, but an import, an RPC call or another view can still save a Friday.
Add an `@api.constrains` on `library.borrowing.expected_return_date` that refuses Fridays.
Which existing method must you double-check so that "Borrow Again" still works?

### Exercise 5 (Extending views): kanban dashboard
Reuse the same idea for **Books**: a `js_class="library_book_kanban"` that shows
*Total / Available / Borrowed* (from `get_dashboard_data`) above the kanban view.
Hint: `kanbanView`, `KanbanRenderer`, template `web.KanbanRenderer`.

### Exercise 6 (Bootstrap): request form in a modal
On the website book page, replace the inline request form by a **Request this book** button that opens a
Bootstrap modal containing the form. No new JS is allowed. Does the datepicker interaction still work? Why?

### Exercise 7 (Interaction): live availability
On `/library`, add an interaction on each book card that calls the Week 11 JSON-RPC endpoint
`/library/api/availability` every 30 seconds and updates the *Available / Borrowed* badge.
Make sure the timer stops when the interaction is destroyed.

---

## 8. Exercise Solutions

<details>
<summary>Exercise 1</summary>

```javascript
// static/src/client_actions/book_stats.js
import { Component, onWillStart, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";

export class BookStats extends Component {
    static template = "library_management.BookStats";
    static props = ["*"];          // client actions receive action, actionId, ...

    setup() {
        this.orm = useService("orm");
        this.state = useState({ data: {} });
        onWillStart(() => this.load());
    }

    async load() {
        this.state.data = await this.orm.call("library.book", "get_dashboard_data", []);
    }
}

registry.category("actions").add("library_book_stats", BookStats);
```

```xml
<!-- static/src/client_actions/book_stats.xml -->
<templates xml:space="preserve">
    <t t-name="library_management.BookStats">
        <div class="o_action p-4 overflow-auto">
            <div class="d-flex justify-content-between mb-3">
                <h2>Book statistics</h2>
                <button class="btn btn-secondary" t-on-click="load"><i class="fa fa-refresh"/> Refresh</button>
            </div>
            <div class="row g-3">
                <t t-foreach="Object.entries(state.data)" t-as="entry" t-key="entry[0]">
                    <div class="col-6 col-md-4 col-lg-2">
                        <div class="card text-center"><div class="card-body">
                            <div class="fs-2 fw-bold" t-esc="entry[1]"/>
                            <div class="text-muted text-capitalize" t-esc="entry[0].replace('_', ' ')"/>
                        </div></div>
                    </div>
                </t>
            </div>
        </div>
    </t>
</templates>
```

```xml
<!-- views/... (data) -->
<record id="action_library_book_stats" model="ir.actions.client">
    <field name="name">Book Stats</field>
    <field name="tag">library_book_stats</field>
</record>
<menuitem id="menu_library_book_stats" name="Book Stats"
          parent="menu_library_reporting" action="action_library_book_stats"/>
```

`menu_library_reporting` is defined in `views/menu_views.xml`. The `client_actions/` folder must be in
`web.assets_backend` (add `'library_management/static/src/client_actions/**/*'`).
</details>

<details>
<summary>Exercise 2</summary>

```javascript
import { Component } from "@odoo/owl";
import { _t } from "@web/core/l10n/translation";
import { registry } from "@web/core/registry";
import { standardFieldProps } from "@web/views/fields/standard_field_props";

export class IsbnField extends Component {
    static template = "library_management.IsbnField";
    static props = { ...standardFieldProps };

    get value() {
        return this.props.record.data[this.props.name] || "";
    }

    get isValid() {
        const digits = this.value.replace(/[-\s]/g, "");
        return !digits || (/^\d+$/.test(digits) && [10, 13].includes(digits.length));
    }

    onInput(ev) {
        // update on each key: the badge/border follows live
        this.props.record.update({ [this.props.name]: ev.target.value });
    }
}

registry.category("fields").add("library_isbn", {
    component: IsbnField,
    displayName: _t("ISBN"),
    supportedTypes: ["char"],
});
```

```xml
<t t-name="library_management.IsbnField">
    <span t-if="props.readonly"><i class="fa fa-barcode me-1"/><t t-esc="value"/></span>
    <input t-else="" t-att-id="props.id" class="o_input" t-att-class="{'is-invalid border-danger': !isValid}"
           t-att-value="value" t-on-input="onInput"/>
</t>
```

The Python `@api.constrains('isbn')` from Week 8 stays: the widget is comfort, the constraint is the rule.
</details>

<details>
<summary>Exercise 3</summary>

```javascript
static props = { ..., maxDays: { type: Number, optional: true } };

get maxDate() {
    const base = this.startDate || today();
    return this.props.maxDays ? base.plus({ days: this.props.maxDays }) : false;
}

get quickPicks() {
    const base = this.startDate || today();
    return this.props.quickDays
        .filter((days) => !this.props.maxDays || days <= this.props.maxDays)
        .map(/* ...unchanged... */);
}
```

```xml
<DateTimeInput ... minDate="startDate" maxDate="maxDate" .../>
```

```javascript
extractProps: ({ options, placeholder }) => ({ ..., maxDays: options.max_days }),
```
</details>

<details>
<summary>Exercise 4</summary>

```python
CLOSED_WEEKDAYS = (5,)  # ISO: Friday, same numbers as the JS widget

@api.constrains('expected_return_date')
def _check_expected_return_not_closed(self):
    for borrowing in self:
        date = borrowing.expected_return_date
        if date and date.isoweekday() in CLOSED_WEEKDAYS:
            raise ValidationError(_('The library is closed on %s.', date.strftime('%A')))
```

Check every place that computes a date automatically: `_onchange_borrow_date` (borrow date + 14 days)
and `action_borrow_again`. If they can land on a Friday, move the date to the next open day there too,
otherwise users get an error for a date they did not choose. Same for `library.book.request.action_approve`,
which copies the request's date.
</details>

<details>
<summary>Exercise 5</summary>

```javascript
import { registry } from "@web/core/registry";
import { kanbanView } from "@web/views/kanban/kanban_view";
import { KanbanRenderer } from "@web/views/kanban/kanban_renderer";
import { BookDashboard } from "./book_dashboard";   // like BorrowingDashboard, calls get_dashboard_data

export class BookKanbanRenderer extends KanbanRenderer {
    static template = "library_management.BookKanbanRenderer";
    static components = { ...KanbanRenderer.components, BookDashboard };
}

registry.category("views").add("library_book_kanban", { ...kanbanView, Renderer: BookKanbanRenderer });
```

```xml
<t t-name="library_management.BookKanbanRenderer" t-inherit="web.KanbanRenderer" t-inherit-mode="primary">
    <xpath expr="//div[hasclass('o_kanban_renderer')]" position="before">
        <BookDashboard/>
    </xpath>
</t>
```

Then `<kanban js_class="library_book_kanban" ...>` via an inherited view. Open `web.KanbanRenderer` in
`addons/web/static/src/views/kanban/kanban_renderer.xml` to check the root element's class before writing the xpath.
</details>

<details>
<summary>Exercise 6</summary>

```xml
<button type="button" class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#library_request_modal">
    <i class="fa fa-paper-plane"/> Request this book
</button>

<div class="modal fade" id="library_request_modal" tabindex="-1" aria-labelledby="library_request_modal_title" aria-hidden="true">
    <div class="modal-dialog modal-dialog-centered">
        <div class="modal-content">
            <div class="modal-header">
                <h5 class="modal-title" id="library_request_modal_title">Request <t t-out="book.name"/></h5>
                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"/>
            </div>
            <div class="modal-body">
                <form ... class="o_library_request_form" ...> <!-- the existing form, unchanged --> </form>
            </div>
        </div>
    </div>
</div>
```

The interaction still works: it is bound to `.o_library_request_form` when the **page** loads, and the
modal's HTML is already in the page (just hidden). Bootstrap only toggles its visibility.
</details>

<details>
<summary>Exercise 7</summary>

Add `data-book-id` and a class on the badge in `website_library_book_card`:

```xml
<div class="mt-auto o_library_availability" t-att-data-book-id="book.id">
    <span class="badge o_library_availability_badge" .../>
</div>
```

```javascript
import { rpc } from "@web/core/network/rpc";
import { registry } from "@web/core/registry";
import { Interaction } from "@web/public/interaction";

export class LiveAvailability extends Interaction {
    static selector = ".o_library_availability";

    dynamicContent = {
        ".o_library_availability_badge": {
            "t-out": () => (this.available ? "Available" : "Borrowed"),
            "t-att-class": () => ({
                "text-bg-success": this.available,
                "text-bg-warning": !this.available,
            }),
        },
    };

    setup() {
        this.bookId = parseInt(this.el.dataset.bookId);
        this.available = this.el.querySelector(".text-bg-success") !== null;
    }

    start() {
        const timer = setInterval(() => this.refresh(), 30000);
        this.registerCleanup(() => clearInterval(timer));   // stop when destroyed
    }

    async refresh() {
        const result = await this.waitFor(rpc("/library/api/availability", { book_id: this.bookId }));
        if (!result.error) {
            this.available = result.available;
            this.updateContent();
        }
    }
}

registry.category("public.interactions").add("library_management.live_availability", LiveAvailability);
```

`this.waitFor()` makes sure we do not touch the DOM if the interaction was destroyed during the request.
</details>

---

## 9. Troubleshooting Cheat-sheet

| Symptom | Likely cause |
|---|---|
| Widget not used, field looks normal | JS not in the bundle: check the `'assets'` paths, upgrade the module (manifest changed), hard refresh |
| `Missing widget: library_due_date for field of type date` | Typo in the registry key, or the JS file failed to load (look for the first red error in the console) |
| `Template library_management.X not found` | OWL `.xml` file not in the bundle, or `t-name` typo |
| Blank page / white screen after a JS change | Syntax error: open the console. Use `?debug=assets` to get the real file and line |
| `Invalid props for component` | Prop missing in `static props`, or wrong type (e.g. `type="date"` instead of `type="'date'"`) |
| Value changes but is not saved | You changed a local variable or the `<input>` instead of calling `record.update()` |
| Old JS still running | Browser cache: hard refresh (`Ctrl+Shift+R`), or run with `--dev xml` / `?debug=assets` |
| Calendar styling does not apply | Popover is outside the field: use a global selector (`.o_date_item_cell.o_library_closed_day`) |
| `js_class` ignored | Wrong key, or `js_class` set on an inherited view that is not the one the action opens |
| Every list in Odoo got the dashboard | Template used `t-inherit-mode="extension"` instead of `primary` |
| Dashboard filter click does nothing | Card `filter` ≠ `<filter name="...">` in the search view |
| Website JS not running | File in `web.assets_backend` instead of `web.assets_frontend`, or `static selector` does not match |
| Website value changes but `dynamicContent` not refreshed | Change made in a callback not managed by the interaction: call `this.updateContent()` |
| Controller receives `10/31/2026` and fails to parse | You named the **visible** input. Send the ISO date from a hidden input (`serializeDate`) |
| `publicWidget` examples do not work | Odoo 19 uses `Interaction` + `registry.category("public.interactions")` |
