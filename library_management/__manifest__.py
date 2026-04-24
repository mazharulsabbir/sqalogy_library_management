{
    'name': 'Library Management',
    'version': '19.0.1.0.0',
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
    """,
    'author': 'Your Company',
    'website': 'https://www.yourcompany.com',
    'license': 'LGPL-3',
    'depends': ['base', 'mail'],
    'data': [
        'security/library_security.xml',
        'security/ir.model.access.csv',

        'views/book_views.xml',
        'views/borrowing_views.xml',

        'reports/book_inventory_report.xml',
        'reports/borrowing_history_report.xml',

        'views/menu_views.xml',
    ],
    'installable': True,
    'application': True,
    'auto_install': False,
}
