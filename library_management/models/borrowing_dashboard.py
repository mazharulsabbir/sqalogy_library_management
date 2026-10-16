# -*- coding: utf-8 -*-
# =============================================================================
# WEEK 14: server side of the Borrowings list dashboard (OWL component)
# =============================================================================
# The JS calls it with:  this.orm.call("library.borrowing", "get_library_dashboard", [])
# @api.model because it works on the whole model, not on specific records.
# Only STORED fields in the domains: is_overdue is a non-stored compute, so
# "late" is expressed with expected_return_date instead.
# =============================================================================
from datetime import timedelta

from odoo import api, fields, models


class LibraryBorrowingDashboard(models.Model):
    _inherit = 'library.borrowing'

    @api.model
    def get_library_dashboard(self):
        today = fields.Date.context_today(self)
        borrowed = [('state', '=', 'borrowed')]
        return {
            'active': self.search_count(borrowed),
            'late': self.search_count(borrowed + [('expected_return_date', '<', today)]),
            'due_soon': self.search_count(borrowed + [
                ('expected_return_date', '>=', today),
                ('expected_return_date', '<=', today + timedelta(days=7)),
            ]),
            'returned_month': self.search_count([
                ('state', '=', 'returned'),
                ('return_date', '>=', today.replace(day=1)),
            ]),
        }
