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
# WEEK 8 CLASS 3: ORM Methods demonstrated in this file:
#   * create(), write(), unlink()  -> CRUD operations
#   * search(), search_count()     -> Finding records
#   * read(), read_group()         -> Data retrieval
#   * browse(), mapped(), filtered() -> Recordset operations
#   * ensure_one(), name_get()     -> Utility methods
# =============================================================================
from odoo import api, fields, models, _


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

    # =========================================================================
    # WEEK 8 CLASS 3: ORM Methods
    # =========================================================================
    # Simple model demonstrating core ORM operations
    # =========================================================================

    def name_get(self):
        """Override name_get to show category with book count.

        WEEK 8 CLASS 3: name_get()

        Shell example:
            categories = Category.search([], limit=5)
            categories.name_get()
        """
        result = []
        for cat in self:
            name = f"{cat.name} ({cat.book_count} books)"
            result.append((cat.id, name))
        return result

    @api.model
    def get_category_statistics(self):
        """Get statistics for all categories using read_group.

        WEEK 8 CLASS 3: read_group()

        Shell example:
            Category.get_category_statistics()
        """
        return {
            'total_categories': self.search_count([]),
            'categories_with_books': self.search_count([('book_ids', '!=', False)]),
            'empty_categories': self.search_count([('book_ids', '=', False)]),
        }

    def get_all_book_titles(self):
        """Get all book titles for these categories using mapped.

        WEEK 8 CLASS 3: mapped()

        Shell example:
            cat = Category.search([], limit=1)
            cat.get_all_book_titles()
        """
        return self.mapped('book_ids.name')

    def get_all_authors(self):
        """Get unique authors from books in these categories.

        WEEK 8 CLASS 3: mapped()

        Shell example:
            categories = Category.search([])
            categories.get_all_authors()
        """
        return list(set(self.mapped('book_ids.author')))

    def get_categories_with_books(self):
        """Filter to get only categories that have books.

        WEEK 8 CLASS 3: filtered()

        Shell example:
            categories = Category.search([])
            with_books = categories.get_categories_with_books()
        """
        return self.filtered(lambda c: c.book_ids)

    def get_popular_categories(self, min_books=2):
        """Filter categories with at least N books.

        WEEK 8 CLASS 3: filtered()

        Shell example:
            categories = Category.search([])
            popular = categories.get_popular_categories(min_books=3)
        """
        return self.filtered(lambda c: len(c.book_ids) >= min_books)

    def get_category_data(self):
        """Read category data as dictionaries.

        WEEK 8 CLASS 3: read()

        Shell example:
            categories = Category.search([], limit=5)
            categories.get_category_data()
        """
        return self.read(['name', 'color', 'description', 'book_count'])

    def get_single_category_details(self):
        """Get detailed information for a single category.

        WEEK 8 CLASS 3: ensure_one()

        Shell example:
            cat = Category.search([], limit=1)
            cat.get_single_category_details()
        """
        self.ensure_one()
        return {
            'id': self.id,
            'name': self.name,
            'color': self.color,
            'description': self.description,
            'book_count': self.book_count,
            'books': self.book_ids.mapped(lambda b: {
                'id': b.id,
                'name': b.name,
                'author': b.author,
                'state': b.state,
            }),
        }

    @api.model
    def create_category(self, name, color=0, description=None):
        """Create a new category.

        WEEK 8 CLASS 3: create()

        Shell example:
            Category.create_category('Technology', color=5, description='Tech books')
        """
        vals = {
            'name': name,
            'color': color,
        }
        if description:
            vals['description'] = description
        return self.create(vals)

    @api.model
    def bulk_create_categories(self, categories_data):
        """Create multiple categories at once.

        WEEK 8 CLASS 3: create() batch

        Shell example:
            Category.bulk_create_categories([
                {'name': 'Art', 'color': 1},
                {'name': 'Music', 'color': 2},
                {'name': 'Sports', 'color': 3},
            ])
        """
        return self.create(categories_data)

    def update_color(self, new_color):
        """Update color for these categories.

        WEEK 8 CLASS 3: write()

        Shell example:
            cat = Category.search([('name', '=', 'Fiction')], limit=1)
            cat.update_color(5)
        """
        return self.write({'color': new_color})

    def safe_delete(self):
        """Delete categories that have no books.

        WEEK 8 CLASS 3: unlink() with filtered()

        Shell example:
            categories = Category.search([])
            categories.safe_delete()
        """
        # Only delete empty categories
        to_delete = self.filtered(lambda c: not c.book_ids)
        count = len(to_delete)
        if to_delete:
            to_delete.unlink()
        return {'deleted': count}

    @api.model
    def search_categories(self, name_filter=None, has_books=None, page=1, page_size=10):
        """Search categories with filters and pagination.

        WEEK 8 CLASS 3: search() and search_count()

        Shell example:
            # All categories
            Category.search_categories()
            # Filter by name
            Category.search_categories(name_filter='fiction')
            # Only with books
            Category.search_categories(has_books=True)
        """
        domain = []
        if name_filter:
            domain.append(('name', 'ilike', name_filter))
        if has_books is True:
            domain.append(('book_ids', '!=', False))
        elif has_books is False:
            domain.append(('book_ids', '=', False))

        offset = (page - 1) * page_size
        records = self.search(domain, offset=offset, limit=page_size, order='name')
        total = self.search_count(domain)

        return {
            'records': records,
            'data': records.get_category_data(),
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_records': total,
                'total_pages': (total + page_size - 1) // page_size,
            }
        }

    @api.model
    def browse_category(self, category_id):
        """Browse a category by ID.

        WEEK 8 CLASS 3: browse()

        Shell example:
            Category.browse_category(1)
        """
        record = self.browse(category_id)
        if not record.exists():
            return {'error': f'Category with ID {category_id} not found'}
        return record.get_single_category_details()
