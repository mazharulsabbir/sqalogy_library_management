# Week 11: Odoo Website Development

## Learning Objectives

By the end of this week, you will be able to:

- Explain how a website feature is laid out inside an Odoo module
- Publish backend records on the website with `website.published.mixin`
- Write controllers with `@http.route` (`http` / `jsonrpc`, `auth`, converters, POST + CSRF)
- Build website pages with QWeb (`website.layout`, `t-field`, `t-foreach`, pager, template inheritance)
- Add a section to the customer portal (`/my`) and secure it with access rights, record rules and access tokens

---

## Table of Contents

1. [Website Basics: Module Structure](#1-website-basics-module-structure)
2. [Controllers: @http.route](#2-controllers-httproute)
3. [Templates: QWeb for Website](#3-templates-qweb-for-website)
4. [Portal: Views & Security](#4-portal-views--security)
5. [Hands-on Lab Setup](#5-hands-on-lab-setup)
6. [Practice Exercises](#6-practice-exercises)
7. [Exercise Solutions](#7-exercise-solutions)
8. [Troubleshooting Cheat-sheet](#8-troubleshooting-cheat-sheet)

---

## 1. Website Basics: Module Structure

### 1.1 What changes when a module "goes web"?

A website feature is still a normal module. We only add three things:

| Piece | Folder | Purpose |
|---|---|---|
| **Controllers** | `controllers/` | Python classes that answer URLs |
| **QWeb templates** | `views/*_templates.xml` | The HTML of the pages |
| **Security for visitors** | `security/` | Rights for `base.group_public` / `base.group_portal` |

Our library module after Week 11:

```
library_management/
├── __init__.py                     # from . import models, controllers   <-- NEW
├── __manifest__.py                 # depends: website, portal            <-- NEW
├── controllers/                                                          <-- NEW
│   ├── __init__.py
│   ├── main.py                     # public website: /library, /library/book/...
│   └── portal.py                   # customer portal: /my/borrowings
├── models/
│   ├── book_website.py             # website.published.mixin on library.book
│   └── borrowing_portal.py         # portal.mixin on library.borrowing
├── security/
│   ├── ir.model.access.csv         # + public/portal READ lines
│   └── library_website_security.xml  # record rules for visitors
├── views/
│   ├── book_website_views.xml      # backend: Publish button, cover, description
│   ├── website_templates.xml       # QWeb: catalog + book page
│   └── portal_templates.xml        # QWeb: /my cards, list, detail
└── data/
    ├── website_data.xml            # "Library" entry in the top menu
    └── website_demo.xml            # publish demo books
```

### 1.2 The manifest

```python
'depends': ['base', 'mail', 'website', 'portal'],
'data': [
    'security/library_security.xml',
    'security/ir.model.access.csv',
    'security/library_website_security.xml',   # rules need the models -> after CSV
    ...
    'views/book_website_views.xml',
    'views/website_templates.xml',
    'views/portal_templates.xml',
    'data/website_data.xml',                   # website.menu needs website installed
],
```

> **Rule of thumb:** templates are just `ir.ui.view` records, so they go in `data` like any other view.
> Controllers are **not** declared in the manifest. They are Python, so they are imported from `__init__.py`.

```python
# library_management/__init__.py
from . import models
from . import controllers      # forget this line and every route returns 404
```

### 1.3 Making a model "publishable": `website.published.mixin`

`models/book_website.py`:

```python
class LibraryBookWebsite(models.Model):
    _name = 'library.book'                                  # extend, don't create
    _inherit = ['library.book', 'website.published.mixin']

    cover_image = fields.Image(max_width=512, max_height=512)
    website_description = fields.Html(sanitize=True, translate=True)

    def _compute_website_url(self):
        super()._compute_website_url()
        for book in self:
            if book.id:
                book.website_url = '/library/book/%s' % self.env['ir.http']._slug(book)
```

What the mixin gives us for free:

| Field / method | Meaning |
|---|---|
| `is_published` (`website_published`) | The publish toggle |
| `website_url` | Where the record lives (**we** compute it) |
| `can_publish` | Can the current user publish this record? |
| `website_publish_button()` | Backend "Go to Website" smart button |

> ⚠️ **Odoo 19 gotcha:** with a multi-item `_inherit` you **must** write `_name` explicitly.
> Without it, Odoo 19 derives a *new* model name from the class name (`library.book.website`)
> and you get `Invalid field library.book.is_published` at install time.

`_slug(book)` → `"pather-panchali-1"` (readable name + id). The `model()` route converter turns it
back into a record (section 2).

### 1.4 Website menu

`data/website_data.xml`:

```xml
<record id="menu_website_library" model="website.menu">
    <field name="name">Library</field>
    <field name="url">/library</field>
    <field name="parent_id" ref="website.main_menu"/>
    <field name="sequence" type="int">50</field>
</record>
```

### 1.5 Backend side: the Publish button

`views/book_website_views.xml` inherits the book form:

```xml
<div name="button_box" position="inside">
    <field name="is_published" widget="website_redirect_button"/>
</div>
```

**Try it:** open a book in the backend → click **Unpublished**, which switches it to **Published**.
Use the same button to open the page on the website.

---

## 2. Controllers: @http.route

### 2.1 Anatomy of a route

```python
from odoo import http
from odoo.http import request

class LibraryWebsite(http.Controller):

    @http.route('/library/hello', type='http', auth='public', website=True)
    def hello(self, name=None, **kwargs):
        return _("Hello %s, welcome to the Library website!", escape(name or _("visitor")))
```

Open `http://localhost:8069/library/hello?name=Rahim`. Query-string parameters arrive as **keyword arguments**.
Always keep `**kwargs` so unknown parameters (e.g. tracking params) don't crash the route.

### 2.2 The `@http.route` arguments you need

| Argument | Values | Notes |
|---|---|---|
| `route` | `'/url'` or `['/a', '/a/page/<int:page>']` | Several URLs → one method |
| `type` | `'http'` | Browser pages, files, redirects, `make_json_response` |
| | `'jsonrpc'` | JSON-RPC 2.0 (called by JS `rpc()`). Odoo ≤17 called it `'json'` |
| `auth` | `'public'` | Anyone. Anonymous visitors run as the **Public user** |
| | `'user'` | Must be logged in, otherwise redirected to `/web/login` |
| | `'none'` | No user/env at all (rare: health checks) |
| `website` | `True` | Website context: layout, menu, language, `request.website` |
| `methods` | `['GET']`, `['POST']` | Restrict HTTP verbs (others → 405) |
| `csrf` | `True` (default) | POST forms must send `csrf_token` |
| `sitemap` | `True/False` | Include in `/sitemap.xml` |

### 2.3 URL converters

```python
@http.route(['/library', '/library/page/<int:page>'], ...)          # page -> int
def catalog(self, page=1, search='', category=None, **kwargs): ...

@http.route('/library/book/<model("library.book"):book>', ...)      # slug -> record
def book_detail(self, book, **kwargs):
    if not book.exists() or not book.has_access('read'):
        raise NotFound()
```

> The `model()` converter **does not** check that the visitor may read the record. Always check it yourself.

### 2.4 Rendering a page

```python
return request.render('library_management.website_library_catalog', {
    'books': books,
    'pager': pager,
    ...
})
```

Every dict key becomes a variable in the QWeb template.
`request.website.pager(url, total, page, step, url_args)` builds the dict that `website.pager` displays.

### 2.5 Handling a form (POST + CSRF)

```python
@http.route('/library/book/<model("library.book"):book>/request',
            type='http', auth='user', website=True, methods=['POST'])
def book_request(self, book, message='', **kwargs):
    ...
    book.sudo().message_post(body=body, author_id=partner.id, ...)
    return request.redirect('%s?requested=1' % book.website_url)
```

The form **must** contain:

```xml
<input type="hidden" name="csrf_token" t-att-value="request.csrf_token()"/>
```

Post-Redirect-Get: after a POST we **redirect**. Refreshing the page then won't resubmit the form.

### 2.6 JSON endpoints

```python
# Plain HTTP GET -> JSON (easy to test in the browser)
@http.route('/library/api/books', type='http', auth='public', methods=['GET'])
def api_books(self, **kwargs):
    return request.make_json_response([...])

# JSON-RPC: params in the body, result wrapped automatically
@http.route('/library/api/availability', type='jsonrpc', auth='public')
def api_availability(self, book_id): ...
```

```bash
curl http://localhost:8069/library/api/books

curl -X POST http://localhost:8069/library/api/availability \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc": "2.0", "params": {"book_id": 1}}'
# {"jsonrpc": "2.0", "id": null, "result": {"id": 1, "title": "...", "available": true}}
```

### 2.7 Security golden rules for controllers

1. Code runs **as the visitor** (`request.env.user`). ACLs and record rules apply. That's good.
2. `sudo()` only **after** you checked the visitor is allowed to do that exact action.
3. Never trust URL/form input: validate ids (`.exists()`, `has_access`), escape output (QWeb `t-out` does it).
4. Mutating routes = `methods=['POST']` + CSRF. Never change data on GET.

---

## 3. Templates: QWeb for Website

### 3.1 Page skeleton

```xml
<template id="website_library_catalog" name="Library: Catalog">
    <t t-call="website.layout">                         <!-- header, menu, footer -->
        <t t-set="additional_title">Library Catalog</t>  <!-- browser tab title -->
        <div id="wrap">
            <div class="oe_structure" id="oe_structure_library_catalog_top"/>  <!-- snippet drop zone -->
            <div class="container py-4">
                ...
            </div>
        </div>
    </t>
</template>
```

### 3.2 Directive cheat-sheet

| Directive | Example | Notes |
|---|---|---|
| `t-out` | `<span t-out="book.author"/>` | Prints a value, **HTML-escaped** (replaces old `t-esc`) |
| `t-field` | `<h1 t-field="book.name"/>` | Uses the field widget **and** is editable in website edit mode. Not allowed on `<td>`/`<th>`, so wrap it in a `<span>` |
| `t-options` | `t-options="{'widget': 'date', 'format': 'MMMM y'}"` | Formats `t-field`/`t-out` |
| `t-if/t-elif/t-else` | `<span t-if="book.state == 'available'">` | |
| `t-foreach/t-as` | `<div t-foreach="books" t-as="book">` | Extra vars: `book_index`, `book_first`, `book_last` |
| `t-set/t-value` | `<t t-set="x" t-value="2"/>` | Body form: `<t t-set="title">Text</t>` |
| `t-att-*` | `t-att-href="book.website_url"` | Dynamic attribute |
| `t-attf-*` | `t-attf-class="nav-link #{'active' if ok else ''}"` | Format string (`#{}` or `{{ }}`) |
| `t-call` | `<t t-call="website.pager"/>` | Include a template. Current variables are visible inside |

### 3.3 Reusable sub-templates

The catalog loops and calls a card template. `book` is visible inside the card because `t-call`
shares the current variables:

```xml
<div t-foreach="books" t-as="book" class="col-sm-6 col-lg-4 col-xl-3">
    <t t-call="library_management.website_library_book_card"/>
</div>
```

### 3.4 Images

```xml
<!-- URL to the image field (public access goes through ACL + record rules) -->
<img t-attf-src="/web/image/library.book/{{ book.id }}/cover_image"/>

<!-- or the widget, editable in edit mode -->
<div t-field="book.cover_image" t-options="{'widget': 'image', 'class': 'img-fluid'}"/>
```

### 3.5 Template inheritance and Customize options

Templates inherit exactly like backend views (`inherit_id` + `xpath`).
With `active="False" customize_show="True"`, the extension becomes an **on/off option** in the website editor:

```xml
<template id="website_library_book_card_isbn" name="Show ISBN on Book Cards"
          inherit_id="library_management.website_library_book_card"
          active="False" customize_show="True">
    <xpath expr="//p[hasclass('o_library_card_author')]" position="after">
        <p t-if="book.isbn" class="card-text small mb-2"><i class="fa fa-barcode"/> <t t-out="book.isbn"/></p>
    </xpath>
</template>
```

> Tip: give the elements you expect others to target a stable class or `name` (`o_library_card_author`).
> That makes xpaths robust.

### 3.6 `main_object`

```python
return request.render('...website_library_book', {'book': book, 'main_object': book})
```

`main_object` tells the website editor which record the page is about. The **Publish** toggle in the top
bar and the SEO "Optimize" dialog then act on the book.

---

## 4. Portal: Views & Security

### 4.1 Portal vs Website

| | Website | Portal |
|---|---|---|
| Audience | Everyone (public user) | Logged-in **customers** (`base.group_portal`) |
| URLs | Anything (`/library`) | `/my/...` |
| Data | Published content | **The customer's own** documents |
| Base controller | `http.Controller` | `CustomerPortal` (inherit it!) |

### 4.2 Linking a portal user to their data

A portal user is a `res.users` whose `partner_id` is their contact. Our member **is** a partner
(Week 7 delegation inheritance), so we expose it on the borrowing:

```python
# models/borrowing_portal.py
class LibraryBorrowingPortal(models.Model):
    _name = 'library.borrowing'
    _inherit = ['library.borrowing', 'portal.mixin']

    partner_id = fields.Many2one('res.partner', related='member_id.partner_id',
                                 store=True, index=True)

    def _compute_access_url(self):
        super()._compute_access_url()
        for borrowing in self:
            borrowing.access_url = '/my/borrowings/%s' % borrowing.id
```

`portal.mixin` adds `access_url`, `access_token` and `get_portal_url()`, and it powers the **Share** feature.

### 4.3 Security: two layers, both required

**Layer 1: access rights (model level).** "May this group read the model *at all*?"

```csv
access_library_book_public,library.book.public,model_library_book,base.group_public,1,0,0,0
access_library_book_portal,library.book.portal,model_library_book,base.group_portal,1,0,0,0
access_library_category_public,...,base.group_public,1,0,0,0
access_library_category_portal,...,base.group_portal,1,0,0,0
access_library_borrowing_portal,...,model_library_borrowing,base.group_portal,1,0,0,0
```

**Layer 2: record rules (row level).** "*Which* records?"

```xml
<record id="library_book_public_published_rule" model="ir.rule">
    <field name="model_id" ref="model_library_book"/>
    <field name="domain_force">[('is_published', '=', True)]</field>
    <field name="groups" eval="[(4, ref('base.group_public')), (4, ref('base.group_portal'))]"/>
</record>

<record id="library_borrowing_portal_rule" model="ir.rule">
    <field name="model_id" ref="model_library_borrowing"/>
    <field name="domain_force">[('partner_id', '=', user.partner_id.id)]</field>
    <field name="groups" eval="[(4, ref('base.group_portal'))]"/>
</record>
```

> No rule on a model + ACL read = the group sees **every** record. Forgetting the borrowing rule would
> leak all customers' borrowings to every portal user.

**Layer 3: access tokens (one record, no login).**
The backend **Share** action builds `/my/borrowings/5?access_token=...`.
`_document_check_access()` accepts **either** normal read access **or** a valid token.

### 4.4 The portal controller

`controllers/portal.py` inherits `CustomerPortal`:

```python
class LibraryCustomerPortal(CustomerPortal):

    def _prepare_home_portal_values(self, counters):        # counter on the /my card
        values = super()._prepare_home_portal_values(counters)
        if 'borrowing_count' in counters:
            values['borrowing_count'] = request.env['library.borrowing'].search_count(
                self._get_borrowings_domain())
        return values

    @http.route(['/my/borrowings', '/my/borrowings/page/<int:page>'],
                type='http', auth='user', website=True)
    def portal_my_borrowings(self, page=1, sortby=None, filterby=None, **kwargs):
        ...  # searchbar_sortings / searchbar_filters / portal_pager
        borrowings = Borrowing.search(domain, ...)           # AS THE USER: rules apply
        values['borrowings'] = borrowings.sudo()            # sudo only to RENDER related fields
        return request.render('library_management.portal_my_borrowings', values)

    @http.route('/my/borrowings/<int:borrowing_id>', type='http', auth='public', website=True)
    def portal_my_borrowing(self, borrowing_id, access_token=None, **kwargs):
        try:
            borrowing_sudo = self._document_check_access('library.borrowing', borrowing_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')
        ...
```

Why `auth='public'` on the detail page? A share-link recipient may not have an account.
The token check is the security there.

### 4.5 The portal templates (`views/portal_templates.xml`)

| # | Template | Inherits / calls | Shows |
|---|---|---|---|
| 1 | `portal_breadcrumbs_borrowing` | inherits `portal.portal_breadcrumbs` | Home / Borrowings / BRW00001 |
| 2 | `portal_my_home_borrowing` | inherits `portal.portal_my_home`, calls `portal.portal_docs_entry` | Card on `/my` (`placeholder_count='borrowing_count'`) |
| 3 | `portal_my_borrowings` | `portal.portal_layout` + `portal.portal_searchbar` + `portal.portal_table` | List with sort/filter |
| 4 | `portal_my_borrowing` | `portal.portal_layout` | Detail card |

> The `/my` card is **hidden while its counter is 0**. If your card doesn't appear, check the counter first.

---

## 5. Hands-on Lab Setup

```bash
# 1. Upgrade the module (website + portal get installed as dependencies)
python odoo-bin -c odoo.conf -d YOUR_DB -u library_management

# 2. Start the server and open http://localhost:8069/library
```

Create test data (backend or Odoo shell):

```python
# python odoo-bin shell -c odoo.conf -d YOUR_DB
member = env['library.member'].create({'name': 'Portal Reader', 'email': 'reader@example.com'})
book = env['library.book'].search([], limit=1)
book.is_published = True
env['library.borrowing'].create({'book_id': book.id, 'member_id': member.id,
                                 'borrower_name': member.name})
env['res.users'].create({
    'name': 'Portal Reader', 'login': 'reader', 'password': 'reader123',
    'partner_id': member.partner_id.id,
    'group_ids': [(6, 0, [env.ref('base.group_portal').id])],
})
env.cr.commit()
```

(Or in the UI: **Contacts → Portal Reader → ⚙ Action → Grant portal access**.)

Smoke tests:

| URL | As | Expected |
|---|---|---|
| `/library/hello?name=Rahim` | anyone | "Hello Rahim…" |
| `/library` | anonymous | Only published books |
| `/library/book/<unpublished-slug>` | anonymous | 404 |
| `/library/api/books` | anyone | JSON list |
| `/my` | reader | "Library Borrowings" card with counter |
| `/my/borrowings` | reader | Only reader's borrowings |
| `/my/borrowings/<someone else's id>` | reader | Redirect to `/my` |
| Book page → "Send request" | reader | Message appears in the book's chatter (backend) |

---

## 6. Practice Exercises

### Exercise 1 (Basics): publish categories
Add `website.published.mixin` to `library.category` and only show published categories as pills on `/library`.
Remember the `_name` gotcha and the public/portal record rule.

### Exercise 2 (Controller): author page
Create `/library/author/<string:author>` that lists all published books by that author.
Render it with a new template that **reuses** `website_library_book_card`. Link the author name on the book page to it.

### Exercise 3 (Controller + JSON): availability badge
Call `/library/api/availability` from the browser console with `fetch` and print whether book 1 is available.
Then explain: why does a `jsonrpc` route not need a CSRF token, while our POST form does?

### Exercise 4 (QWeb): "New arrivals" ribbon
On the book card, show a **"New"** badge when the book was created in the last 30 days.
Do it in an **inheriting template** with `customize_show="True"`, so editors can turn it on and off.

### Exercise 5 (QWeb): sort dropdown
Add a "Sort by: Title / Author / Newest" dropdown to `/library`. Keep `search` and `category` when the sort changes,
and make the pager keep the sort too (`url_args`).

### Exercise 6 (Portal): "Return requested" button
On `/my/borrowings/<id>` (state *Borrowed* only), add a button that POSTs to
`/my/borrowings/<id>/return-request` and posts a chatter message on the borrowing.
Protect it with `_document_check_access` and CSRF.

### Exercise 7 (Security): break it, then fix it
1. Comment out `library_borrowing_portal_rule`, upgrade, and log in as `reader`. What do you see on `/my/borrowings`?
2. Restore the rule. Now remove the `borrowings.sudo()` in the list controller and unpublish the book of
   reader's borrowing. What error do you get, and why?

---

## 7. Exercise Solutions

<details>
<summary>Exercise 1</summary>

```python
# models/category.py (or a new file)
class LibraryCategoryWebsite(models.Model):
    _name = 'library.category'
    _inherit = ['library.category', 'website.published.mixin']
```

```xml
<record id="library_category_public_published_rule" model="ir.rule">
    <field name="name">Library Category: published only</field>
    <field name="model_id" ref="model_library_category"/>
    <field name="domain_force">[('is_published', '=', True)]</field>
    <field name="groups" eval="[(4, ref('base.group_public')), (4, ref('base.group_portal'))]"/>
</record>
```

In the controller: `'categories': request.env['library.category'].search([('is_published', '=', True)])`.
</details>

<details>
<summary>Exercise 2</summary>

```python
@http.route('/library/author/<string:author>', type='http', auth='public', website=True)
def author_books(self, author, **kwargs):
    books = request.env['library.book'].search([
        ('is_published', '=', True), ('author', '=', author)])
    if not books:
        raise NotFound()
    return request.render('library_management.website_library_author',
                          {'author': author, 'books': books})
```

```xml
<template id="website_library_author" name="Library: Author">
    <t t-call="website.layout">
        <div id="wrap" class="container py-4">
            <h1>Books by <t t-out="author"/></h1>
            <div class="row g-4">
                <div t-foreach="books" t-as="book" class="col-md-4">
                    <t t-call="library_management.website_library_book_card"/>
                </div>
            </div>
        </div>
    </t>
</template>
```

On the book page: `<a t-attf-href="/library/author/{{ book.author }}" t-out="book.author"/>`.
`<string:...>` does not match `/`, so an author name containing a slash would need a different URL design (e.g. `?author=` query param).
</details>

<details>
<summary>Exercise 3</summary>

```js
fetch('/library/api/availability', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({jsonrpc: '2.0', params: {book_id: 1}}),
}).then(r => r.json()).then(d => console.log(d.result));
```

CSRF attacks rely on a browser silently submitting a **form** (or a simple request) to another site.
A cross-site page can't send `Content-Type: application/json` without a CORS preflight, and Odoo sends no CORS headers for this route, so the browser blocks it.
So `jsonrpc` routes are not exposed to classic CSRF. `type='http'` POST routes are, which is why they check `csrf_token`.
</details>

<details>
<summary>Exercise 4</summary>

```xml
<template id="website_library_book_card_new" name="Show 'New' badge"
          inherit_id="library_management.website_library_book_card"
          active="True" customize_show="True">
    <xpath expr="//h5[hasclass('card-title')]" position="before">
        <span t-if="book.create_date and (datetime.datetime.now() - book.create_date).days &lt; 30"
              class="badge text-bg-primary align-self-start mb-1">New</span>
    </xpath>
</template>
```

`datetime` is available in QWeb. Note `&lt;` because we are inside XML.
</details>

<details>
<summary>Exercise 5</summary>

```python
SORTS = {'title': 'name asc', 'author': 'author asc, name asc', 'new': 'create_date desc'}

def catalog(self, page=1, search='', category=None, order='title', **kwargs):
    order = order if order in SORTS else 'title'
    ...
    pager = request.website.pager(..., url_args={'search': search, 'category': category, 'order': order})
    books = Book.search(domain, order=SORTS[order], limit=..., offset=pager['offset'])
    # pass `order` to the template
```

```xml
<select name="order" class="form-select w-auto" onchange="this.form.submit()">
    <option value="title" t-att-selected="order == 'title'">Title</option>
    <option value="author" t-att-selected="order == 'author'">Author</option>
    <option value="new" t-att-selected="order == 'new'">Newest</option>
</select>
```

Put the `<select>` **inside** the existing GET search form so `search`/`category` are kept.
Never put user input straight into `order=`. That's why we map keys through `SORTS`.
</details>

<details>
<summary>Exercise 6</summary>

```python
@http.route('/my/borrowings/<int:borrowing_id>/return-request',
            type='http', auth='public', website=True, methods=['POST'])
def portal_return_request(self, borrowing_id, access_token=None, **kwargs):
    try:
        borrowing_sudo = self._document_check_access('library.borrowing', borrowing_id, access_token)
    except (AccessError, MissingError):
        return request.redirect('/my')
    if borrowing_sudo.state == 'borrowed':
        borrowing_sudo.message_post(
            body=_("%s asked to return this book.", request.env.user.partner_id.name),
            message_type='comment', subtype_xmlid='mail.mt_note')
    return request.redirect(borrowing_sudo.get_portal_url())
```

```xml
<form t-if="borrowing.state == 'borrowed'" method="post"
      t-attf-action="/my/borrowings/{{ borrowing.id }}/return-request">
    <input type="hidden" name="csrf_token" t-att-value="request.csrf_token()"/>
    <input t-if="access_token" type="hidden" name="access_token" t-att-value="access_token"/>
    <button class="btn btn-primary">Request return</button>
</form>
```
</details>

<details>
<summary>Exercise 7</summary>

1. Without the rule, the portal ACL grants read on **all** borrowings, so the reader sees everyone's records
   on `/my/borrowings` (our explicit domain in the controller hides them in the list, but
   `/my/borrowings/<other id>` now opens!). That's why the **record rule** is the real protection, not the controller domain.
2. `AccessError` while rendering `borrowing.book_id.name`. The borrowing is readable, but the related book is
   unpublished, so the book rule blocks it. Searching as the user and then rendering with `sudo()` is the standard
   Odoo pattern (see `sale` / `account` portal controllers).
</details>

---

## 8. Troubleshooting Cheat-sheet

| Symptom | Likely cause |
|---|---|
| Every new URL is 404 | `controllers` not imported in `__init__.py`, or server not restarted (Python changes need a restart) |
| `Invalid field library.book.is_published` on install | Missing `_name` with multi-item `_inherit` (Odoo 19) |
| `QWeb widgets do not work correctly on 'td' elements` | `t-field` on `<td>`: wrap the value in `<span t-field=...>` |
| `400 Bad Request` / "Session expired" on form submit | Missing `csrf_token` hidden input |
| 403 / AccessError for anonymous visitors | No `base.group_public` line in `ir.model.access.csv` |
| Visitors see unpublished records | Missing record rule, or controller search with `sudo()` |
| `/my` card not shown | Counter key ≠ `placeholder_count`, or counter is 0 |
| Template change not visible | Template XML changes need `-u library_management` (or `--dev xml`) |
| `type='json'` route breaks after upgrade | Odoo 19 name is `type='jsonrpc'` |
