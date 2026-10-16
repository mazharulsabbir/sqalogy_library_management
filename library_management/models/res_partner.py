# -*- coding: utf-8 -*-
# =============================================================================
# Odoo Inheritance  ->  (1) EXTENSION inheritance
# -----------------------------------------------------------------------------
# Extension inheritance = use `_inherit` WITHOUT `_name` (or with the same
# _name). It does NOT create a new table; instead it *adds to* an existing
# model. Here we add library-specific fields directly onto Odoo's built-in
# res.partner. Every contact in the database now gains these fields/methods.
#
# Compare with the other two styles used in this module:
#   - Delegation inheritance (_inherits) -> see library_member.py
#   - Classical / mixin inheritance      -> see book.py / borrowing.py
#                                           (_inherit = ['mail.thread', ...])
# =============================================================================
from odoo import api, fields, models


class ResPartner(models.Model):
    # Same _name as an existing model + no new table => we EXTEND res.partner.
    _inherit = 'res.partner'

    # One2many/Many2many fields.
    # Inverse of library.member._inherits (partner_id). One partner can be
    # linked to its library.member "profile" record(s).
    member_ids = fields.One2many(
        comodel_name='library.member',
        inverse_name='partner_id',
        string='Library Memberships',
    )
    is_library_member = fields.Boolean(
        string='Is Library Member',
        compute='_compute_is_library_member',
        store=True,
        help='True when this contact has at least one library membership',
    )

    @api.depends('member_ids')
    def _compute_is_library_member(self):
        for partner in self:
            # Recordset truthiness: a non-empty recordset is truthy.
            partner.is_library_member = bool(partner.member_ids)
