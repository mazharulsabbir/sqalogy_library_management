# -*- coding: utf-8 -*-
# =============================================================================
# WEEK 7 TOPICS demonstrated in this file:
#   * Odoo Models           -> models.Model subclass => library_book table
#   * Odoo Inheritance      -> (3) CLASSICAL/MIXIN inheritance via _inherit list
#   * ORM Basics/Recordsets -> compute methods iterate recordsets
#   * Environment (env)      -> self.env[...] to reach other models
#   * Domains               -> search() domains below
#   * One2many/Many2many    -> category_ids (M2M) and borrowing_ids (O2M)
#                              plus the special Command.* ORM commands
# =============================================================================
# WEEK 8 TOPICS demonstrated in this file:
#   * @api.model            -> Model-level methods (get_available_books_count, etc.)
#   * @api.depends          -> Computed field dependencies (_compute_borrowing_count)
#   * @api.depends_context  -> Context-aware computation (_compute_availability_message)
#   * @api.constrains       -> Data validation (_check_isbn, _check_publication_year)
#   * @api.onchange         -> UI field updates (_onchange_category_ids)
#   * @api.ondelete         -> Deletion protection (_unlink_check_not_borrowed)
# =============================================================================
from odoo import api, fields, models, Command, _
from odoo.exceptions import ValidationError, UserError


class LibraryBook(models.Model):
    _name = 'library.book'
    _description = 'Library Book'
    # Odoo Inheritance -> MIXIN (classical) inheritance.
    # Listing abstract models in `_inherit` (with a _name set) mixes their
    # fields/behaviour into this model. mail.thread adds the chatter +
    # message_post; mail.activity.mixin adds scheduled activities.
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'name'

    name = fields.Char(
        string='Title',
        required=True,
        tracking=True,
        help='Book title'
    )
    author = fields.Char(
        string='Author',
        required=True,
        tracking=True,
        help='Book author name'
    )
    publication_date = fields.Date(
        string='Publication Date',
        tracking=True,
        help='Date when the book was published'
    )
    isbn = fields.Char(
        string='ISBN',
        tracking=True,
        help='International Standard Book Number',
        copy=False
    )
    state = fields.Selection(
        [
            ('available', 'Available'),
            ('borrowed', 'Borrowed'),
        ],
        string='Status',
        default='available',
        required=True,
        tracking=True,
        help='Current availability status of the book'
    )
    active = fields.Boolean(
        string='Active',
        default=True,
        help='Set to false to archive the book'
    )
    # One2many/Many2many fields.
    # One2many = the "many" side of a Many2one. It needs the inverse Many2one
    # field name on the other model (library.borrowing.book_id). No extra
    # column is stored on this table; Odoo derives it from book_id.
    borrowing_ids = fields.One2many(
        comodel_name='library.borrowing',
        inverse_name='book_id',
        string='Borrowings',
        help='All borrowing records for this book'
    )
    # Many2many = a relation table linking many books to many categories.
    category_ids = fields.Many2many(
        comodel_name='library.category',
        string='Categories',
        help='Tags/categories classifying this book'
    )
    borrowing_count = fields.Integer(
        string='Times Borrowed',
        compute='_compute_borrowing_count',
        store=True,
        help='Total number of times this book has been borrowed'
    )
    current_borrowing_id = fields.Many2one(
        'library.borrowing',
        string='Current Borrowing',
        compute='_compute_current_borrowing',
        help='Current active borrowing record if book is borrowed'
    )
    notes = fields.Text(
        string='Notes',
        help='Additional notes about the book'
    )
    # -------------------------------------------------------------------------
    # WEEK 8: @api.depends_context - Context-aware computed field
    # This field changes based on user's language setting
    # -------------------------------------------------------------------------
    availability_message = fields.Char(
        string='Availability',
        compute='_compute_availability_message',
        help='Human-readable availability status'
    )

    _sql_constraints = [
        ('isbn_unique', 'UNIQUE(isbn)', 'ISBN must be unique!'),
    ]

    @api.depends('borrowing_ids')
    def _compute_borrowing_count(self):
        """Compute total number of times the book has been borrowed.

        ORM Basics (Recordsets).
        Because we declared the borrowing_ids One2many, we no longer need a
        manual search_count(): `book.borrowing_ids` is already the recordset of
        related borrowings, so len() gives the count. The @api.depends tells the
        ORM to recompute automatically whenever the related borrowings change.
        """
        for book in self:
            book.borrowing_count = len(book.borrowing_ids)

    @api.depends('state')
    def _compute_current_borrowing(self):
        """Get the current borrowing record if book is borrowed.

        WEEK 7 TOPICS: Environment (env) + Domains.
        `self.env['library.borrowing']` reaches another model through the
        environment; `.search([...])` runs a query filtered by a DOMAIN
        (a list of (field, operator, value) leaves). `limit=1` returns a
        single-record recordset (or an empty one).
        """
        for book in self:
            if book.state == 'borrowed':
                book.current_borrowing_id = self.env['library.borrowing'].search([
                    ('book_id', '=', book.id),
                    ('state', '=', 'borrowed')
                ], limit=1)
            else:
                book.current_borrowing_id = False

    @api.constrains('isbn')
    def _check_isbn(self):
        """Validate ISBN format (basic validation)"""
        for book in self:
            if book.isbn:
                # Remove hyphens and spaces for validation
                isbn_clean = book.isbn.replace('-', '').replace(' ', '')
                if not isbn_clean.isdigit() or len(isbn_clean) not in [10, 13]:
                    raise ValidationError(
                        _('ISBN must be 10 or 13 digits (hyphens and spaces are allowed).')
                    )

    def action_set_available(self):
        """Manually mark book as available"""
        self.ensure_one()
        if self.state == 'borrowed':
            # Check if there's an active borrowing
            active_borrowing = self.env['library.borrowing'].search([
                ('book_id', '=', self.id),
                ('state', '=', 'borrowed')
            ], limit=1)
            if active_borrowing:
                raise ValidationError(
                    _('Cannot mark book as available while there is an active borrowing. '
                      'Please return the book through the borrowing record.')
                )
        self.state = 'available'
        return True

    def action_view_borrowings(self):
        """Open list of all borrowing records for this book.

        Domains.
        The returned action carries a DOMAIN that scopes the opened list to
        this book only, and a context that pre-fills book_id on new records.
        """
        self.ensure_one()
        return {
            'name': _('Borrowing History'),
            'type': 'ir.actions.act_window',
            'res_model': 'library.borrowing',
            'view_mode': 'list,form',
            'domain': [('book_id', '=', self.id)],
            'context': {'default_book_id': self.id},
        }

    def action_clear_categories(self):
        """Remove every category tag from the selected book(s).

        Special ORM Commands (One2many/Many2many).
        Writing to a One2many/Many2many field uses special command tuples,
        conveniently produced by the `Command` helper. Full cheat-sheet:

            Command.create(values)   -> (0, 0, values)  add a NEW related record
            Command.update(id, vals) -> (1, id, values) update an existing one
            Command.delete(id)       -> (2, id, 0)      unlink AND delete record
            Command.unlink(id)       -> (3, id, 0)      detach link, keep record
            Command.link(id)         -> (4, id, 0)      attach an existing record
            Command.clear()          -> (5, 0, 0)       detach ALL links
            Command.set([ids])       -> (6, 0, [ids])   replace links with this set

        Here we use Command.clear() to drop all category links (the categories
        themselves are NOT deleted, only the links from these books).
        """
        self.write({'category_ids': [Command.clear()]})
        return True

    # =========================================================================
    # WEEK 8: @api.model - Model-level methods
    # =========================================================================
    # These methods operate on the model itself, not on specific records.
    # `self` is an empty recordset. Use for utility functions, statistics,
    # search helpers, or methods called via XML-RPC.
    # =========================================================================

    @api.model
    def get_available_books_count(self):
        """Return the count of all available books in the library.

        WEEK 8: @api.model
        This method doesn't need any specific record - it queries the entire
        model. Notice `self` is an empty recordset; we use search_count()
        to get the statistic.
        """
        return self.search_count([('state', '=', 'available')])

    @api.model
    def get_borrowed_books_count(self):
        """Return the count of all currently borrowed books."""
        return self.search_count([('state', '=', 'borrowed')])

    @api.model
    def search_by_isbn(self, isbn):
        """Find a book by its ISBN number.

        WEEK 8: @api.model
        A utility method to look up books by ISBN. Returns a recordset
        (single record or empty). Can be called without any book context.
        """
        if not isbn:
            return self.browse()  # Return empty recordset
        # Clean the ISBN before searching
        isbn_clean = isbn.replace('-', '').replace(' ', '')
        return self.search([
            '|',
            ('isbn', '=', isbn),
            ('isbn', '=', isbn_clean),
        ], limit=1)

    @api.model
    def get_dashboard_data(self):
        """Return statistics for a dashboard widget.

        WEEK 8: @api.model
        Perfect use case: gathering statistics that don't depend on any
        specific record. Could be called from a controller or widget.
        """
        return {
            'total_books': self.search_count([]),
            'available': self.search_count([('state', '=', 'available')]),
            'borrowed': self.search_count([('state', '=', 'borrowed')]),
            'active': self.search_count([('active', '=', True)]),
            'archived': self.search_count([('active', '=', False)]),
        }

    @api.model
    def get_popular_books(self, limit=5):
        """Return the most borrowed books.

        WEEK 8: @api.model
        Another utility method - finds books ordered by borrowing_count.
        """
        return self.search([], order='borrowing_count desc', limit=limit)

    # =========================================================================
    # WEEK 8: @api.depends_context - Context-aware computed fields
    # =========================================================================
    # Use when a computed field's value depends on context keys like
    # 'lang' (user language), 'company' (current company), or 'tz' (timezone).
    # The cache key includes context values, so changes trigger recomputation.
    # =========================================================================

    @api.depends('state')
    @api.depends_context('lang')
    def _compute_availability_message(self):
        """Generate a human-readable availability message.

        WEEK 8: @api.depends_context
        This message is translated based on the user's language setting.
        When the user switches language, the message is recomputed.
        The @api.depends_context('lang') ensures proper cache invalidation.
        """
        for book in self:
            if book.state == 'available':
                book.availability_message = _("This book is available for borrowing")
            elif book.state == 'borrowed':
                book.availability_message = _("This book is currently borrowed")
            else:
                book.availability_message = _("Status unknown")

    # =========================================================================
    # WEEK 8: @api.constrains - Data validation
    # =========================================================================
    # Triggered on create() and write() AFTER values are set in memory but
    # BEFORE database commit. Raises ValidationError to block invalid data.
    # Always iterate over self as multiple records may be processed.
    # =========================================================================

    @api.constrains('publication_date')
    def _check_publication_date(self):
        """Ensure publication date is not in the future.

        WEEK 8: @api.constrains
        Validates that books aren't published in the future (with 1 year
        tolerance for upcoming releases). Raises ValidationError if invalid.
        """
        from datetime import timedelta
        today = fields.Date.today()
        max_future = today + timedelta(days=365)  # Allow 1 year future dates

        for book in self:
            if book.publication_date and book.publication_date > max_future:
                raise ValidationError(
                    _('Publication date for "%s" cannot be more than 1 year in the future.')
                    % book.name
                )

    # =========================================================================
    # WEEK 8: @api.onchange - UI field change handlers
    # =========================================================================
    # Triggered ONLY in the UI when a user changes a field value in a form.
    # Use to auto-fill related fields, show warnings, or provide guidance.
    # Does NOT run on programmatic writes or imports.
    # =========================================================================

    @api.onchange('category_ids')
    def _onchange_category_ids(self):
        """Show a message when categories are updated.

        WEEK 8: @api.onchange
        This runs in the form UI when categories change. We can return a
        warning dict to display a message to the user. The warning doesn't
        block saving - it's just informational.
        """
        if self.category_ids:
            category_names = ', '.join(self.category_ids.mapped('name'))
            return {
                'warning': {
                    'title': _("Categories Updated"),
                    'message': _("Book will be categorized under: %s") % category_names,
                }
            }

    @api.onchange('author')
    def _onchange_author(self):
        """Suggest related books when author is entered.

        WEEK 8: @api.onchange
        When user enters an author name, check if we have other books by
        the same author and show a helpful message.
        """
        if self.author and self._origin.id:
            # Find other books by the same author
            other_books = self.search([
                ('author', '=', self.author),
                ('id', '!=', self._origin.id),
            ], limit=5)
            if other_books:
                titles = ', '.join(other_books.mapped('name'))
                return {
                    'warning': {
                        'title': _("Other books by %s") % self.author,
                        'message': _("Library also has: %s") % titles,
                    }
                }

    # =========================================================================
    # WEEK 8: @api.ondelete - Deletion protection
    # =========================================================================
    # Intercepts unlink() calls to enforce business rules before deletion.
    # Use UserError for blocking deletions with a user-friendly message.
    # Set at_uninstall=False to skip checks during module uninstallation.
    # =========================================================================

    @api.ondelete(at_uninstall=False)
    def _unlink_check_not_borrowed(self):
        """Prevent deletion of currently borrowed books.

        WEEK 8: @api.ondelete
        Books that are currently borrowed cannot be deleted - the borrowing
        record still references them. This protects data integrity.
        """
        for book in self:
            if book.state == 'borrowed':
                raise UserError(
                    _('Cannot delete book "%s" because it is currently borrowed. '
                      'Please wait for the book to be returned first.') % book.name
                )

    @api.ondelete(at_uninstall=False)
    def _unlink_check_has_history(self):
        """Suggest archiving instead of deleting books with history.

        WEEK 8: @api.ondelete
        If a book has borrowing history, we suggest archiving it instead
        of deleting to preserve historical records.
        """
        for book in self:
            if book.borrowing_ids:
                raise UserError(
                    _('Cannot delete book "%s" because it has %d borrowing records. '
                      'To preserve history, archive the book instead using the '
                      '"Archive" action.') % (book.name, len(book.borrowing_ids))
                )
