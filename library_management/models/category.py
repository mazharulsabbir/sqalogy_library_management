# -*- coding: utf-8 -*-
# =============================================================================
# Odoo Models
# -----------------------------------------------------------------------------
# A model is a Python class that inherits from models.Model. Odoo turns it into
# a PostgreSQL table and gives it a full ORM API (create/read/write/unlink,
# search, recordsets, etc.). This is the simplest possible "regular" model:
# a table to tag/classify books. It is also the *target* of the Many2many
# relation defined on library.book (see book.py -> category_ids).
# =============================================================================
from odoo import fields, models


class LibraryCategory(models.Model):
    # _name registers a brand new model => a new database table "library_category".
    _name = 'library.category'
    # _description is required for every model (used in logs/UI metadata).
    _description = 'Library Book Category'
    # _order controls the default sort order of recordsets returned by search().
    _order = 'name'

    name = fields.Char(
        string='Category',
        required=True,
        help='Name of the category (e.g., Fiction, Science, History)'
    )
    color = fields.Integer(
        string='Color Index',
        help='Color used for the tag in kanban/list views'
    )
    description = fields.Text(string='Description')

    # One2many/Many2many fields.
    # This is the *inverse* side of the Many2many declared on library.book.
    # Because it is Many2many, Odoo creates a relation table linking the two
    # models; both sides share the same set of links.
    book_ids = fields.Many2many(
        comodel_name='library.book',
        string='Books',
        help='All books tagged with this category'
    )
    book_count = fields.Integer(
        string='Number of Books',
        compute='_compute_book_count',
        help='How many books currently use this category'
    )

    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Category name must be unique!'),
    ]

    def _compute_book_count(self):
        # ORM Basics (Recordsets).
        # `self` is a recordset; iterating yields one-record recordsets.
        # `category.book_ids` is itself a recordset, so len() = number of records.
        for category in self:
            category.book_count = len(category.book_ids)
