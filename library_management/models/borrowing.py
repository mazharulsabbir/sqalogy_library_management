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
# WEEK 8 TOPICS demonstrated in this file:
#   * @api.model_create_multi -> Batch creation with sequence generation
#   * @api.depends            -> Computed fields (is_overdue, days_borrowed)
#   * @api.constrains         -> Data validation (dates, availability, limits)
#   * @api.onchange           -> UI auto-fill (_onchange_member_id, _onchange_book_id)
#   * @api.ondelete           -> Deletion protection (_unlink_check_state)
# =============================================================================
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
from datetime import date, timedelta


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

    # =========================================================================
    # WEEK 8: @api.onchange - UI field change handlers
    # =========================================================================

    @api.onchange('member_id')
    def _onchange_member_id(self):
        """Auto-fill borrower contact details from the selected member.

        WEEK 8: @api.onchange
        Environment + delegation inheritance in action.
        Because library.member delegates to res.partner, member_id.name/email/
        phone read straight through to the partner record.
        """
        if self.member_id:
            self.borrower_name = self.member_id.name
            self.borrower_email = self.member_id.email
            self.borrower_phone = self.member_id.phone

    @api.onchange('book_id')
    def _onchange_book_id(self):
        """Warn user if selected book is unavailable and set default return date.

        WEEK 8: @api.onchange
        This demonstrates multiple behaviors in one onchange:
        1. Show a warning if the book is already borrowed
        2. Auto-set the expected return date to 14 days from borrow date
        """
        if self.book_id:
            # Set default expected return date (14 days from borrow date)
            if not self.expected_return_date and self.borrow_date:
                self.expected_return_date = self.borrow_date + timedelta(days=14)

            # Warn if book is already borrowed
            if self.book_id.state == 'borrowed':
                return {
                    'warning': {
                        'title': _("Book Not Available"),
                        'message': _(
                            "The book '%s' is currently borrowed by another member. "
                            "Please choose a different book or wait for its return."
                        ) % self.book_id.name,
                    }
                }

    @api.onchange('borrow_date')
    def _onchange_borrow_date(self):
        """Update expected return date when borrow date changes.

        WEEK 8: @api.onchange
        Keeps the expected return date 14 days after the borrow date.
        """
        if self.borrow_date:
            self.expected_return_date = self.borrow_date + timedelta(days=14)

    # =========================================================================
    # WEEK 8: @api.depends - Computed field dependencies
    # =========================================================================

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

    # =========================================================================
    # WEEK 8: @api.constrains - Data validation
    # =========================================================================

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

    # =========================================================================
    # WEEK 8: @api.model_create_multi - Batch creation handler
    # =========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        """Generate the reference sequence and update book status on create.

        WEEK 8: @api.model_create_multi
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

    # =========================================================================
    # WEEK 8: @api.ondelete - Deletion protection
    # =========================================================================

    @api.ondelete(at_uninstall=False)
    def _unlink_check_state(self):
        """Prevent deletion of active borrowings.

        WEEK 8: @api.ondelete
        Active borrowing records (state='borrowed') cannot be deleted directly.
        The user must first return the book using the 'Return Book' action.
        This protects data integrity and ensures proper book state management.
        """
        for record in self:
            if record.state == 'borrowed':
                raise UserError(
                    _('Cannot delete borrowing record "%s" while the book is still borrowed. '
                      'Please return the book first using the "Return Book" action.') % record.name
                )

    @api.ondelete(at_uninstall=False)
    def _unlink_update_book_state(self):
        """Ensure book state is updated when borrowing is deleted.

        WEEK 8: @api.ondelete
        This is a cleanup hook that runs before deletion. Since we block
        active borrowings above, this only runs for 'returned' records.
        Note: We could perform additional cleanup here if needed.
        """
        # This method demonstrates that multiple @api.ondelete can be defined
        # The first one blocks active borrowings, this one could do cleanup
        pass

    # =========================================================================
    # WEEK 8: @api.constrains - Additional member limit validation
    # =========================================================================

    @api.constrains('member_id', 'state')
    def _check_member_borrowing_limit(self):
        """Ensure member hasn't exceeded the borrowing limit (max 5 books).

        WEEK 8: @api.constrains
        Business rule: A member can only borrow up to 5 books at a time.
        This prevents library abuse and ensures fair access to resources.
        """
        MAX_BORROWINGS = 5
        for record in self:
            if record.member_id and record.state == 'borrowed':
                active_borrowings = self.search_count([
                    ('member_id', '=', record.member_id.id),
                    ('state', '=', 'borrowed'),
                ])
                if active_borrowings > MAX_BORROWINGS:
                    raise ValidationError(
                        _('Member "%s" has reached the maximum borrowing limit '
                          'of %d books. Please return a book before borrowing more.')
                        % (record.member_id.name, MAX_BORROWINGS)
                    )

    # =========================================================================
    # WEEK 8 CLASS 3: ORM Methods
    # =========================================================================
    # These methods demonstrate core ORM operations for borrowing records
    # =========================================================================

    @api.model
    def default_get(self, fields_list):
        """Override default_get to set smart defaults for borrowings.

        WEEK 8 CLASS 3: default_get()

        Shell example:
            Borrowing.default_get(['borrow_date', 'expected_return_date', 'state'])
        """
        defaults = super().default_get(fields_list)
        # Auto-set expected return date to 14 days from today
        if 'expected_return_date' in fields_list and not defaults.get('expected_return_date'):
            defaults['expected_return_date'] = date.today() + timedelta(days=14)
        return defaults

    def name_get(self):
        """Override name_get to show borrowing reference with book info.

        WEEK 8 CLASS 3: name_get()

        Shell example:
            borrowings = Borrowing.search([], limit=5)
            borrowings.name_get()
        """
        result = []
        for rec in self:
            name = rec.name or _('New')
            if rec.book_id:
                name = f"{name} - {rec.book_id.name}"
            result.append((rec.id, name))
        return result

    @api.model
    def get_borrowing_statistics(self):
        """Get borrowing statistics using read_group.

        WEEK 8 CLASS 3: read_group()

        Shell example:
            Borrowing.get_borrowing_statistics()
        """
        by_state = self.read_group(
            domain=[],
            fields=['state', 'days_borrowed:sum', 'days_borrowed:avg'],
            groupby=['state']
        )
        return {
            'by_state': by_state,
            'total': self.search_count([]),
            'active': self.search_count([('state', '=', 'borrowed')]),
            'returned': self.search_count([('state', '=', 'returned')]),
            'overdue': self.search_count([('is_overdue', '=', True)]),
        }

    @api.model
    def get_monthly_statistics(self):
        """Get borrowing statistics grouped by month.

        WEEK 8 CLASS 3: read_group() with date grouping

        Shell example:
            Borrowing.get_monthly_statistics()
        """
        return self.read_group(
            domain=[],
            fields=['borrow_date'],
            groupby=['borrow_date:month'],
            orderby='borrow_date:month desc'
        )

    def get_overdue_borrowings(self):
        """Filter to get only overdue borrowings from this recordset.

        WEEK 8 CLASS 3: filtered()

        Shell example:
            borrowings = Borrowing.search([('state', '=', 'borrowed')])
            overdue = borrowings.get_overdue_borrowings()
        """
        return self.filtered(lambda b: b.is_overdue)

    def get_active_borrowings(self):
        """Filter to get only active (not returned) borrowings.

        WEEK 8 CLASS 3: filtered_domain()

        Shell example:
            borrowings = Borrowing.search([])
            active = borrowings.get_active_borrowings()
        """
        return self.filtered_domain([('state', '=', 'borrowed')])

    def get_book_titles(self):
        """Get all book titles from these borrowings using mapped.

        WEEK 8 CLASS 3: mapped()

        Shell example:
            borrowings = Borrowing.search([], limit=10)
            borrowings.get_book_titles()
        """
        return self.mapped('book_id.name')

    def get_member_names(self):
        """Get all member names from these borrowings using mapped.

        WEEK 8 CLASS 3: mapped()

        Shell example:
            borrowings = Borrowing.search([], limit=10)
            borrowings.get_member_names()
        """
        return self.mapped('member_id.name')

    def get_borrowing_summary(self):
        """Read specific fields as dictionaries for API response.

        WEEK 8 CLASS 3: read()

        Shell example:
            borrowings = Borrowing.search([], limit=3)
            borrowings.get_borrowing_summary()
        """
        return self.read([
            'name', 'borrower_name', 'book_id', 'borrow_date',
            'expected_return_date', 'return_date', 'state', 'is_overdue', 'days_borrowed'
        ])

    def get_single_borrowing_details(self):
        """Get detailed information for a single borrowing.

        WEEK 8 CLASS 3: ensure_one()

        Shell example:
            borrowing = Borrowing.search([], limit=1)
            borrowing.get_single_borrowing_details()
        """
        self.ensure_one()
        return {
            'id': self.id,
            'reference': self.name,
            'borrower': self.borrower_name,
            'borrower_email': self.borrower_email,
            'book': {
                'id': self.book_id.id,
                'name': self.book_id.name,
                'author': self.book_id.author,
            } if self.book_id else None,
            'member': {
                'id': self.member_id.id,
                'name': self.member_id.name,
                'code': self.member_id.member_code,
            } if self.member_id else None,
            'dates': {
                'borrowed': str(self.borrow_date) if self.borrow_date else None,
                'expected_return': str(self.expected_return_date) if self.expected_return_date else None,
                'returned': str(self.return_date) if self.return_date else None,
            },
            'status': self.state,
            'is_overdue': self.is_overdue,
            'days_borrowed': self.days_borrowed,
        }

    @api.model
    def search_borrowings(self, state=None, overdue_only=False, member_id=None, page=1, page_size=10):
        """Search borrowings with filters and pagination.

        WEEK 8 CLASS 3: search() and search_count()

        Shell example:
            # All borrowings
            Borrowing.search_borrowings()
            # Only active borrowings
            Borrowing.search_borrowings(state='borrowed')
            # Only overdue
            Borrowing.search_borrowings(overdue_only=True)
            # By member
            Borrowing.search_borrowings(member_id=1)
        """
        domain = []
        if state:
            domain.append(('state', '=', state))
        if overdue_only:
            domain.append(('is_overdue', '=', True))
        if member_id:
            domain.append(('member_id', '=', member_id))

        offset = (page - 1) * page_size
        records = self.search(domain, offset=offset, limit=page_size, order='borrow_date desc')
        total = self.search_count(domain)

        return {
            'records': records,
            'data': records.get_borrowing_summary(),
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_records': total,
                'total_pages': (total + page_size - 1) // page_size,
            }
        }

    @api.model
    def create_borrowing(self, book_id, borrower_name, member_id=None, borrower_email=None):
        """Create a new borrowing record.

        WEEK 8 CLASS 3: create()

        Shell example:
            book = env['library.book'].search([('state', '=', 'available')], limit=1)
            Borrowing.create_borrowing(
                book_id=book.id,
                borrower_name='John Doe',
                borrower_email='john@example.com'
            )
        """
        vals = {
            'book_id': book_id,
            'borrower_name': borrower_name,
            'state': 'borrowed',
        }
        if member_id:
            vals['member_id'] = member_id
        if borrower_email:
            vals['borrower_email'] = borrower_email
        return self.create(vals)

    def mark_as_returned(self):
        """Mark these borrowings as returned.

        WEEK 8 CLASS 3: write()

        Shell example:
            borrowing = Borrowing.search([('state', '=', 'borrowed')], limit=1)
            borrowing.mark_as_returned()
        """
        return self.write({
            'state': 'returned',
            'return_date': date.today(),
        })

    def safe_delete(self):
        """Delete borrowing records that are returned.

        WEEK 8 CLASS 3: unlink() with filtered()

        Shell example:
            # Only deletes returned borrowings
            borrowings = Borrowing.search([])
            borrowings.safe_delete()
        """
        # Only delete returned borrowings
        to_delete = self.filtered(lambda b: b.state == 'returned')
        if to_delete:
            to_delete.unlink()
            return {'deleted': len(to_delete)}
        return {'deleted': 0, 'message': 'No returned borrowings to delete'}

    @api.model
    def browse_borrowing(self, borrowing_id):
        """Browse a borrowing by ID and return details.

        WEEK 8 CLASS 3: browse()

        Shell example:
            Borrowing.browse_borrowing(1)
        """
        record = self.browse(borrowing_id)
        if not record.exists():
            return {'error': f'Borrowing with ID {borrowing_id} not found'}
        return record.get_single_borrowing_details()
