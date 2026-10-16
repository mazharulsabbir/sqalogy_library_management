{
    'name': 'Library Management',
    'version': '19.0.4.0.0',
    'category': 'Productivity',
    'summary': 'Manage library book inventory and borrowing system',
    'description': """
Library Management System
=========================
This module provides comprehensive library management features:
* Book inventory management
* Borrowing and return tracking
* Availability status management
* Access control for librarians and members
* Inventory and borrowing history reports

Teaching Content
----------------
Week 7: Data Models & ORM
    - Odoo Models (models.Model)
    - Inheritance patterns (mixin, delegation, extension)
    - ORM basics and recordsets
    - Environment (self.env)
    - Domains for filtering
    - One2many/Many2many relations

Week 8: Odoo API Decorators
    - @api.model (model-level methods)
    - @api.model_create_multi (batch creation)
    - @api.depends (computed field dependencies)
    - @api.depends_context (context-aware computation)
    - @api.onchange (UI field change handlers)
    - @api.constrains (data validation)
    - @api.ondelete (deletion protection)

Week 11: Odoo Website Development
    - Website basics: module structure, website.published.mixin, website.menu
    - Controllers: @http.route (http / jsonrpc, auth, converters, POST + CSRF)
    - Templates: QWeb for website (website.layout, t-field, pager, inheritance)
    - Portal: /my pages, CustomerPortal, portal.mixin, access rights & rules

Week 14: Frontend & Widgets
    - Odoo web framework: assets bundles, OWL components, registries, services
    - Extending views with JavaScript: js_class (Borrowings list dashboard)
    - Custom field widgets: library_days_badge, library_due_date (datepicker)
    - Website: Bootstrap components/SCSS and an Interaction on the request form
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': ['base', 'mail', 'website', 'portal'],
    'data': [
        'security/library_security.xml',
        'security/ir.model.access.csv',
        'security/library_website_security.xml',

        'views/category_views.xml',
        'views/member_views.xml',
        'views/book_views.xml',
        'views/borrowing_views.xml',

        'reports/book_inventory_report.xml',
        'reports/borrowing_history_report.xml',

        'views/menu_views.xml',

        # Week 11: Website & Portal
        'views/book_website_views.xml',
        'views/website_templates.xml',
        'views/portal_templates.xml',
        'views/book_request_views.xml',
        'data/website_data.xml',

        # Week 14: Frontend & Widgets
        'views/borrowing_widget_views.xml',
    ],
    'demo': [
        # CSV file name = model name (Odoo uses it to know which model to load)
        'data/library.category.csv',
        'data/library.member.csv',
        'data/library.book.csv',
        'data/demo_data.xml',
        'data/website_demo.xml',
    ],
    # Week 14: JS/XML/SCSS are not "data": they go in asset bundles.
    #   web.assets_backend  -> the web client (/odoo)
    #   web.assets_frontend -> website and portal pages
    'assets': {
        'web.assets_backend': [
            'library_management/static/src/fields/**/*',
            'library_management/static/src/views/**/*',
        ],
        'web.assets_frontend': [
            'library_management/static/src/interactions/**/*',
            'library_management/static/src/scss/library_website.scss',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
}
