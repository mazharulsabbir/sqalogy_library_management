# -*- coding: utf-8 -*-
# =============================================================================
# WEEK 7: Odoo Inheritance -> (2) DELEGATION inheritance (_inherits)
# -----------------------------------------------------------------------------
# Delegation inheritance uses `_inherits = {'target.model': 'link_field'}`.
# It DOES create a new table (library_member) BUT every field of the delegated
# model (res.partner) is transparently available on the new model. Under the
# hood Odoo stores a Many2one to res.partner and forwards attribute access to
# it. So a library.member "is a" partner: you can read/write member.name,
# member.email, member.phone even though those columns live on res.partner.
#
# This is different from EXTENSION inheritance (res_partner.py), which adds
# fields to res.partner itself without a new table.
# =============================================================================
# WEEK 8 TOPICS demonstrated in this file:
#   * @api.model_create_multi -> Batch creation with sequence generation
#   * @api.depends            -> Computed fields (borrowing_stats)
#   * @api.ondelete           -> Deletion protection (_unlink_check_active_borrowings)
# =============================================================================
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError


class LibraryMember(models.Model):
    _name = 'library.member'
    _description = 'Library Member'
    # mixin inheritance can be combined with delegation: chatter on members.
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _inherits = {'res.partner': 'partner_id'}
    _order = 'member_code'

    # The delegate link. required + ondelete='cascade' is the standard pattern:
    # deleting the member deletes its dedicated partner profile.
    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Related Partner',
        required=True,
        ondelete='cascade',
        help='The contact record this membership delegates to',
    )
    member_code = fields.Char(
        string='Member ID',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
        help='Auto-generated unique membership code',
    )
    membership_date = fields.Date(
        string='Member Since',
        default=fields.Date.context_today,
    )

    # One2many/Many2many fields.
    # One member -> many borrowings (inverse of library.borrowing.member_id).
    borrowing_ids = fields.One2many(
        comodel_name='library.borrowing',
        inverse_name='member_id',
        string='Borrowings',
    )
    borrowing_count = fields.Integer(
        string='Total Borrowings',
        compute='_compute_borrowing_stats',
        store=True,
    )
    active_borrowing_count = fields.Integer(
        string='Currently Borrowed',
        compute='_compute_borrowing_stats',
        store=True,
    )

    # =========================================================================
    # WEEK 8: @api.depends - Computed field dependencies
    # =========================================================================

    @api.depends('borrowing_ids', 'borrowing_ids.state')
    def _compute_borrowing_stats(self):
        """Calculate borrowing statistics for the member.

        WEEK 8: @api.depends
        Dependencies include both the One2many field and the nested state field.
        Using 'borrowing_ids.state' ensures recomputation when any borrowing's
        state changes (not just when borrowings are added/removed).
        """
        for member in self:
            member.borrowing_count = len(member.borrowing_ids)
            # ORM Basics + Recordsets.
            # `.filtered(...)` returns a new recordset keeping only matching
            # records -- in-memory, no SQL query. Great for already-loaded data.
            member.active_borrowing_count = len(
                member.borrowing_ids.filtered(lambda b: b.state == 'borrowed')
            )

    # =========================================================================
    # WEEK 8: @api.model_create_multi - Batch creation handler
    # =========================================================================

    @api.model_create_multi
    def create(self, vals_list):
        """Generate member code on creation.

        WEEK 8: @api.model_create_multi
        Environment (env).
        self.env gives access to other models, the current user, context,
        cursor, etc. Here we use it to pull the next sequence value.
        """
        for vals in vals_list:
            if vals.get('member_code', _('New')) == _('New'):
                vals['member_code'] = self.env['ir.sequence'].next_by_code(
                    'library.member'
                ) or _('New')
        return super().create(vals_list)

    def action_view_borrowings(self):
        self.ensure_one()
        # Domains.
        # A domain is a list of (field, operator, value) tuples used to filter
        # records. Here it scopes the opened list to this member's borrowings.
        return {
            'name': _('Borrowings'),
            'type': 'ir.actions.act_window',
            'res_model': 'library.borrowing',
            'view_mode': 'list,form',
            'domain': [('member_id', '=', self.id)],
            'context': {'default_member_id': self.id},
        }

    # =========================================================================
    # WEEK 8: @api.ondelete - Deletion protection
    # =========================================================================

    @api.ondelete(at_uninstall=False)
    def _unlink_check_active_borrowings(self):
        """Prevent deletion of members with unreturned books.

        WEEK 8: @api.ondelete
        Members who have books currently borrowed cannot be deleted.
        They must return all books first. This protects library resources
        and ensures proper tracking of borrowed materials.
        """
        for member in self:
            active_borrowings = member.borrowing_ids.filtered(
                lambda b: b.state == 'borrowed'
            )
            if active_borrowings:
                book_names = ', '.join(active_borrowings.mapped('book_id.name'))
                raise UserError(
                    _('Cannot delete member "%s" because they have unreturned books: %s. '
                      'Please ensure all books are returned first.')
                    % (member.name, book_names)
                )

    @api.ondelete(at_uninstall=False)
    def _unlink_suggest_archive(self):
        """Suggest archiving instead of deleting members with history.

        WEEK 8: @api.ondelete
        If a member has any borrowing history (even if all books are returned),
        we suggest archiving instead of deleting to preserve historical records.
        """
        for member in self:
            if member.borrowing_ids:
                raise UserError(
                    _('Member "%s" has %d borrowing record(s) in history. '
                      'To preserve this history, consider archiving the member '
                      'instead of deleting. You can archive members by '
                      'deactivating them.')
                    % (member.name, len(member.borrowing_ids))
                )

    # =========================================================================
    # WEEK 8 CLASS 3: ORM Methods
    # =========================================================================
    # Demonstrates ORM operations with delegation inheritance
    # =========================================================================

    def name_get(self):
        """Override name_get to show member code with name.

        WEEK 8 CLASS 3: name_get()

        Shell example:
            members = Member.search([], limit=5)
            members.name_get()
        """
        result = []
        for member in self:
            name = f"[{member.member_code}] {member.name}"
            result.append((member.id, name))
        return result

    @api.model
    def get_member_statistics(self):
        """Get member statistics using search_count.

        WEEK 8 CLASS 3: search_count()

        Shell example:
            Member.get_member_statistics()
        """
        return {
            'total_members': self.search_count([]),
            'members_with_active_borrowings': self.search_count([
                ('active_borrowing_count', '>', 0)
            ]),
            'members_with_history': self.search_count([
                ('borrowing_count', '>', 0)
            ]),
        }

    def get_borrowed_book_titles(self):
        """Get all book titles currently borrowed by these members.

        WEEK 8 CLASS 3: mapped()

        Shell example:
            member = Member.search([], limit=1)
            member.get_borrowed_book_titles()
        """
        # Traverse: member -> borrowing_ids -> book_id -> name
        active_borrowings = self.mapped('borrowing_ids').filtered(
            lambda b: b.state == 'borrowed'
        )
        return active_borrowings.mapped('book_id.name')

    def get_all_borrowing_references(self):
        """Get all borrowing references for these members.

        WEEK 8 CLASS 3: mapped()

        Shell example:
            members = Member.search([], limit=3)
            members.get_all_borrowing_references()
        """
        return self.mapped('borrowing_ids.name')

    def get_active_members(self):
        """Filter to get only members with active borrowings.

        WEEK 8 CLASS 3: filtered()

        Shell example:
            members = Member.search([])
            active = members.get_active_members()
        """
        return self.filtered(lambda m: m.active_borrowing_count > 0)

    def get_members_with_history(self):
        """Filter to get only members who have borrowed books.

        WEEK 8 CLASS 3: filtered_domain()

        Shell example:
            members = Member.search([])
            with_history = members.get_members_with_history()
        """
        return self.filtered_domain([('borrowing_count', '>', 0)])

    def get_member_data(self):
        """Read member data as dictionaries.

        WEEK 8 CLASS 3: read()

        Shell example:
            members = Member.search([], limit=5)
            members.get_member_data()
        """
        return self.read([
            'member_code', 'name', 'email', 'phone',
            'membership_date', 'borrowing_count', 'active_borrowing_count'
        ])

    def get_single_member_details(self):
        """Get detailed information for a single member.

        WEEK 8 CLASS 3: ensure_one()

        Shell example:
            member = Member.search([], limit=1)
            member.get_single_member_details()
        """
        self.ensure_one()
        return {
            'id': self.id,
            'member_code': self.member_code,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'membership_date': str(self.membership_date) if self.membership_date else None,
            'statistics': {
                'total_borrowings': self.borrowing_count,
                'active_borrowings': self.active_borrowing_count,
            },
            'current_books': self.borrowing_ids.filtered(
                lambda b: b.state == 'borrowed'
            ).mapped(lambda b: {
                'borrowing_id': b.id,
                'book_name': b.book_id.name,
                'borrow_date': str(b.borrow_date),
                'is_overdue': b.is_overdue,
            }),
            'borrowing_history': self.borrowing_ids.mapped(lambda b: {
                'reference': b.name,
                'book': b.book_id.name,
                'state': b.state,
                'borrow_date': str(b.borrow_date),
            }),
        }

    @api.model
    def create_member(self, name, email=None, phone=None):
        """Create a new library member.

        WEEK 8 CLASS 3: create()
        Demonstrates delegation inheritance - creates both member and partner.

        Shell example:
            Member.create_member('John Doe', email='john@example.com', phone='123-456-7890')
        """
        vals = {'name': name}
        if email:
            vals['email'] = email
        if phone:
            vals['phone'] = phone
        return self.create(vals)

    @api.model
    def bulk_create_members(self, members_data):
        """Create multiple members at once.

        WEEK 8 CLASS 3: create() batch

        Shell example:
            Member.bulk_create_members([
                {'name': 'Alice', 'email': 'alice@example.com'},
                {'name': 'Bob', 'email': 'bob@example.com'},
            ])
        """
        return self.create(members_data)

    def update_contact_info(self, email=None, phone=None):
        """Update member contact information.

        WEEK 8 CLASS 3: write()

        Shell example:
            member = Member.search([], limit=1)
            member.update_contact_info(email='new@email.com', phone='999-999-9999')
        """
        vals = {}
        if email:
            vals['email'] = email
        if phone:
            vals['phone'] = phone
        if vals:
            return self.write(vals)
        return True

    @api.model
    def search_members(self, name_filter=None, has_active_borrowings=None, page=1, page_size=10):
        """Search members with filters and pagination.

        WEEK 8 CLASS 3: search() and search_count()

        Shell example:
            # All members
            Member.search_members()
            # Filter by name
            Member.search_members(name_filter='john')
            # Only with active borrowings
            Member.search_members(has_active_borrowings=True)
        """
        domain = []
        if name_filter:
            domain.append(('name', 'ilike', name_filter))
        if has_active_borrowings is True:
            domain.append(('active_borrowing_count', '>', 0))
        elif has_active_borrowings is False:
            domain.append(('active_borrowing_count', '=', 0))

        offset = (page - 1) * page_size
        records = self.search(domain, offset=offset, limit=page_size, order='member_code')
        total = self.search_count(domain)

        return {
            'records': records,
            'data': records.get_member_data(),
            'pagination': {
                'page': page,
                'page_size': page_size,
                'total_records': total,
                'total_pages': (total + page_size - 1) // page_size,
            }
        }

    @api.model
    def browse_member(self, member_id):
        """Browse a member by ID.

        WEEK 8 CLASS 3: browse()

        Shell example:
            Member.browse_member(1)
        """
        record = self.browse(member_id)
        if not record.exists():
            return {'error': f'Member with ID {member_id} not found'}
        return record.get_single_member_details()

    @api.model
    def get_borrowing_report(self):
        """Get a comprehensive borrowing report using read_group.

        WEEK 8 CLASS 3: read_group()

        Shell example:
            Member.get_borrowing_report()
        """
        Borrowing = self.env['library.borrowing']

        # Get borrowings by member
        by_member = Borrowing.read_group(
            domain=[],
            fields=['member_id'],
            groupby=['member_id']
        )

        # Get borrowings by state
        by_state = Borrowing.read_group(
            domain=[],
            fields=['state'],
            groupby=['state']
        )

        return {
            'by_member': by_member,
            'by_state': by_state,
            'total_borrowings': Borrowing.search_count([]),
            'total_members': self.search_count([]),
        }
