# -*- coding: utf-8 -*-
# =============================================================================
# WEEK 11: Odoo Website Development -> (4) Portal
# =============================================================================
# `portal.mixin` makes a model "portal-aware":
#   * access_url      -> the /my/... URL of the record (we compute it)
#   * access_token    -> secret token for share links (Share button)
#   * get_portal_url() -> access_url + token/report params, used in templates
#
# Portal users are res.users in group `base.group_portal`. They can only see
# borrowings that belong to THEIR partner. That restriction is NOT done here:
# it is enforced by the record rule in security/library_website_security.xml.
# =============================================================================

from odoo import fields, models


class LibraryBorrowingPortal(models.Model):
    _name = 'library.borrowing'  # explicit: extend, don't create (see book_website.py)
    _inherit = ['library.borrowing', 'portal.mixin']

    # Stored shortcut to the member's contact. The portal record rule and the
    # controller domain both filter on this field.
    partner_id = fields.Many2one(
        'res.partner',
        string='Borrower Contact',
        related='member_id.partner_id',
        store=True,
        index=True,
    )

    def _compute_access_url(self):
        super()._compute_access_url()
        for borrowing in self:
            borrowing.access_url = '/my/borrowings/%s' % borrowing.id
