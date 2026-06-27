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
from odoo import api, fields, models, Command, _
from odoo.exceptions import ValidationError


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
