# -*- coding: utf-8 -*-
# =============================================================================
# Odoo Inheritance  ->  (2) DELEGATION inheritance (_inherits)
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
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


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
    )
    active_borrowing_count = fields.Integer(
        string='Currently Borrowed',
        compute='_compute_borrowing_stats',
    )

    @api.depends('borrowing_ids', 'borrowing_ids.state')
    def _compute_borrowing_stats(self):
        for member in self:
            member.borrowing_count = len(member.borrowing_ids)
            # ORM Basics + Recordsets.
            # `.filtered(...)` returns a new recordset keeping only matching
            # records -- in-memory, no SQL query. Great for already-loaded data.
            member.active_borrowing_count = len(
                member.borrowing_ids.filtered(lambda b: b.state == 'borrowed')
            )

    @api.model_create_multi
    def create(self, vals_list):
        # Environment (env).
        # self.env gives access to other models, the current user, context,
        # cursor, etc. Here we use it to pull the next sequence value.
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
