# -*- coding: utf-8 -*-
# =============================================================================
# WEEK 7 TOPICS demonstrated in this file:
#   * Odoo Models           -> the library_borrowing table
#   * Odoo Inheritance      -> MIXIN inheritance (mail.thread, activity.mixin)
#   * ORM Basics            -> create/write/unlink overrides, recordset ops
#   * Environment (env)      -> self.env['ir.sequence'] / self.env['library.book']
#   * Domains               -> search([...]) availability checks
#   * One2many/Many2many    -> book_id / member_id Many2one are the inverse
#                              sides of book.borrowing_ids / member.borrowing_ids
# =============================================================================
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError
from datetime import date


class LibraryBorrowing(models.Model):
    _name = 'library.borrowing'
    _description = 'Library Borrowing Record'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'borrow_date desc, id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        help='Unique borrowing reference number'
    )
    borrower_name = fields.Char(
        string='Borrower Name',
        required=True,
        tracking=True,
        help='Name of the person borrowing the book'
    )
    borrower_email = fields.Char(
        string='Email',
        help='Contact email of the borrower'
    )
    borrower_phone = fields.Char(
        string='Phone',
        help='Contact phone number of the borrower'
    )
    book_id = fields.Many2one(
        'library.book',
        string='Book',
        required=True,
        ondelete='restrict',
        tracking=True,
        help='Book being borrowed'
    )
    # One2many/Many2many.
    # This Many2one is the INVERSE side of library.member.borrowing_ids
    # (One2many). Optional: borrowings can still be recorded for a walk-in
    # borrower using just the borrower_* fields below.
    member_id = fields.Many2one(
        'library.member',
        string='Member',
        ondelete='set null',
        tracking=True,
        help='Registered library member borrowing the book (optional)'
    )
    book_author = fields.Char(
        related='book_id.author',
        string='Author',
        readonly=True,
        store=True
    )
    book_isbn = fields.Char(
        related='book_id.isbn',
        string='ISBN',
        readonly=True,
        store=True
    )
    borrow_date = fields.Date(
        string='Borrow Date',
        required=True,
        default=fields.Date.context_today,
        tracking=True,
        help='Date when the book was borrowed'
    )
    expected_return_date = fields.Date(
        string='Expected Return Date',
        tracking=True,
        help='Expected date for returning the book'
    )
    return_date = fields.Date(
        string='Actual Return Date',
        tracking=True,
        help='Actual date when the book was returned'
    )
    state = fields.Selection(
        [
            ('borrowed', 'Borrowed'),
            ('returned', 'Returned'),
        ],
        string='Status',
        default='borrowed',
        required=True,
        tracking=True,
        help='Current status of the borrowing'
    )
    is_overdue = fields.Boolean(
        string='Overdue',
        compute='_compute_is_overdue',
        store=True,
        help='Whether the book return is overdue'
    )
    days_borrowed = fields.Integer(
        string='Days Borrowed',
        compute='_compute_days_borrowed',
        store=True,
        help='Number of days the book has been/was borrowed'
    )
    notes = fields.Text(
        string='Notes',
        help='Additional notes about the borrowing'
    )

    @api.onchange('member_id')
    def _onchange_member_id(self):
        """Auto-fill borrower contact details from the selected member.

        Environment + delegation inheritance in action.
        Because library.member delegates to res.partner, member_id.name/email/
        phone read straight through to the partner record.
        """
        if self.member_id:
            self.borrower_name = self.member_id.name
            self.borrower_email = self.member_id.email
            self.borrower_phone = self.member_id.phone

    @api.depends('expected_return_date', 'return_date', 'state')
    def _compute_is_overdue(self):
        """Check if the borrowing is overdue"""
        today = date.today()
        for borrowing in self:
            if borrowing.state == 'borrowed' and borrowing.expected_return_date:
                borrowing.is_overdue = borrowing.expected_return_date < today
            else:
                borrowing.is_overdue = False

    @api.depends('borrow_date', 'return_date', 'state')
    def _compute_days_borrowed(self):
        """Calculate number of days borrowed"""
        for borrowing in self:
            if borrowing.borrow_date:
                end_date = borrowing.return_date if borrowing.state == 'returned' else date.today()
                borrowing.days_borrowed = (end_date - borrowing.borrow_date).days
            else:
                borrowing.days_borrowed = 0

    @api.constrains('book_id', 'state')
    def _check_book_availability(self):
        """Ensure book is available when creating a new borrowing"""
        for borrowing in self:
            if borrowing.state == 'borrowed':
                # Check if there are other active borrowings for this book
                other_borrowings = self.search([
                    ('book_id', '=', borrowing.book_id.id),
                    ('state', '=', 'borrowed'),
                    ('id', '!=', borrowing.id)
                ])
                if other_borrowings:
                    raise ValidationError(
                        _('Book "%s" is already borrowed and not available.') % borrowing.book_id.name
                    )

    @api.constrains('borrow_date', 'return_date')
    def _check_dates(self):
        """Validate that return date is after borrow date"""
        for borrowing in self:
            if borrowing.return_date and borrowing.borrow_date:
                if borrowing.return_date < borrowing.borrow_date:
                    raise ValidationError(
                        _('Return date cannot be earlier than borrow date.')
                    )

    @api.constrains('expected_return_date', 'borrow_date')
    def _check_expected_return_date(self):
        """Validate that expected return date is after borrow date"""
        for borrowing in self:
            if borrowing.expected_return_date and borrowing.borrow_date:
                if borrowing.expected_return_date < borrowing.borrow_date:
                    raise ValidationError(
                        _('Expected return date cannot be earlier than borrow date.')
                    )

    @api.model_create_multi
    def create(self, vals_list):
        """Generate the reference sequence and update book status on create.

        ORM Basics + Environment.
        This is the single, correct create override. @api.model_create_multi
        receives a LIST of value dicts (batch create), so we loop to assign the
        sequence per record via self.env['ir.sequence']. The book's
        borrowing_count recomputes automatically thanks to @api.depends on the
        One2many (no manual recompute needed).
        """
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'library.borrowing'
                ) or _('New')
        borrowings = super().create(vals_list)
        for borrowing in borrowings:
            if borrowing.state == 'borrowed':
                borrowing.book_id.state = 'borrowed'
        return borrowings

    def write(self, vals):
        """Override write to update book status on state change"""
        result = super().write(vals)
        for borrowing in self:
            if 'state' in vals:
                if borrowing.state == 'borrowed':
                    borrowing.book_id.state = 'borrowed'
                elif borrowing.state == 'returned':
                    # Check if there are other active borrowings for this book
                    other_borrowings = self.search([
                        ('book_id', '=', borrowing.book_id.id),
                        ('state', '=', 'borrowed'),
                        ('id', '!=', borrowing.id)
                    ])
                    if not other_borrowings:
                        borrowing.book_id.state = 'available'
        return result

    def unlink(self):
        """Delete borrowing record(s).

        ORM Basics (Recordsets).
        We no longer need to manually recompute borrowing_count: because it
        @api.depends on the One2many, the ORM invalidates and recomputes it
        automatically once the related links disappear on deletion.
        """
        return super().unlink()

    def action_return_book(self):
        """Mark book as returned"""
        self.ensure_one()
        if self.state == 'returned':
            raise ValidationError(_('This book has already been returned.'))

        self.write({
            'state': 'returned',
            'return_date': date.today()
        })
        return True

    def action_borrow_again(self):
        """Create a new borrowing for the same book and borrower"""
        self.ensure_one()
        return {
            'name': _('New Borrowing'),
            'type': 'ir.actions.act_window',
            'res_model': 'library.borrowing',
            'view_mode': 'form',
            'context': {
                'default_book_id': self.book_id.id,
                'default_borrower_name': self.borrower_name,
                'default_borrower_email': self.borrower_email,
                'default_borrower_phone': self.borrower_phone,
            },
            'target': 'current',
        }
