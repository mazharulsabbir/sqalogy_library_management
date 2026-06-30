{
    'name': 'Library Management',
    'version': '19.0.2.0.0',
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
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': ['base', 'mail'],
    'data': [
        'security/library_security.xml',
        'security/ir.model.access.csv',

        'views/category_views.xml',
        'views/member_views.xml',
        'views/book_views.xml',
        'views/borrowing_views.xml',

        'reports/book_inventory_report.xml',
        'reports/borrowing_history_report.xml',

        'views/menu_views.xml',
    ],
    'demo': [
        'data/categories_import.csv',
        'data/members_import.csv',
        'data/books_import.csv',
        'data/demo_data.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
