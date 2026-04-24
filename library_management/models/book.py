from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class LibraryBook(models.Model):
    _name = 'library.book'
    _description = 'Library Book'
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

    def _compute_borrowing_count(self):
        """Compute total number of times the book has been borrowed"""
        for book in self:
            book.borrowing_count = self.env['library.borrowing'].search_count([
                ('book_id', '=', book.id)
            ])

    @api.depends('state')
    def _compute_current_borrowing(self):
        """Get the current borrowing record if book is borrowed"""
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
        """Open list of all borrowing records for this book"""
        self.ensure_one()
        return {
            'name': _('Borrowing History'),
            'type': 'ir.actions.act_window',
            'res_model': 'library.borrowing',
            'view_mode': 'list,form',
            'domain': [('book_id', '=', self.id)],
            'context': {'default_book_id': self.id},
        }
