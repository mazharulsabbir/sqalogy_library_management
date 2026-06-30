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
