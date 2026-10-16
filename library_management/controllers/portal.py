# -*- coding: utf-8 -*-
# =============================================================================
# WEEK 11: Odoo Website Development -> (4) Portal: Views & Security
# =============================================================================
# The customer portal lives under /my. To add a section to it we INHERIT the
# `CustomerPortal` controller (Python class inheritance on controllers works
# like model inheritance: override a method, call super()).
#
#   _prepare_home_portal_values() -> counters shown on the /my home cards
#   _prepare_portal_layout_values() -> common values (breadcrumbs, user...)
#   _document_check_access()      -> "may this user see record X?" (+ token)
#   _get_page_view_values()       -> prev/next navigation, token handling
#   pager (portal_pager)          -> pagination helper for /my lists
# =============================================================================

from odoo import _, http
from odoo.exceptions import AccessError, MissingError
from odoo.fields import Date
from odoo.http import request

from odoo.addons.portal.controllers.portal import CustomerPortal, pager as portal_pager


class LibraryCustomerPortal(CustomerPortal):

    def _get_borrowings_domain(self):
        """Explicit ownership domain.

        The portal record rule already restricts what the user can read; we
        repeat the condition so the page also behaves for internal users
        (who are not limited by that rule).
        """
        return [('partner_id', '=', request.env.user.partner_id.id)]

    def _prepare_home_portal_values(self, counters):
        values = super()._prepare_home_portal_values(counters)
        # `counters` holds the placeholder names displayed on /my. They are
        # fetched asynchronously by /my/counters, so only compute ours.
        if 'borrowing_count' in counters:
            Borrowing = request.env['library.borrowing']
            values['borrowing_count'] = (
                Borrowing.search_count(self._get_borrowings_domain())
                if Borrowing.has_access('read') else 0
            )
        if 'book_request_count' in counters:
            BookRequest = request.env['library.book.request']
            values['book_request_count'] = (
                BookRequest.search_count(self._get_borrowings_domain())
                if BookRequest.has_access('read') else 0
            )
        return values

    def _get_borrowing_searchbar_sortings(self):
        return {
            'date': {'label': _('Newest'), 'order': 'borrow_date desc, id desc'},
            'due': {'label': _('Due Date'), 'order': 'expected_return_date asc'},
            'name': {'label': _('Reference'), 'order': 'name'},
        }

    def _get_borrowing_searchbar_filters(self):
        return {
            'all': {'label': _('All'), 'domain': []},
            'borrowed': {'label': _('Currently Borrowed'), 'domain': [('state', '=', 'borrowed')]},
            'overdue': {'label': _('Overdue'), 'domain': [('is_overdue', '=', True)]},
            'returned': {'label': _('Returned'), 'domain': [('state', '=', 'returned')]},
        }

    # -------------------------------------------------------------------------
    # /my/borrowings : list page
    # -------------------------------------------------------------------------
    @http.route(
        ['/my/borrowings', '/my/borrowings/page/<int:page>'],
        type='http', auth='user', website=True,
    )
    def portal_my_borrowings(self, page=1, sortby=None, filterby=None, **kwargs):
        values = self._prepare_portal_layout_values()
        Borrowing = request.env['library.borrowing']

        searchbar_sortings = self._get_borrowing_searchbar_sortings()
        searchbar_filters = self._get_borrowing_searchbar_filters()
        sortby = sortby if sortby in searchbar_sortings else 'date'
        filterby = filterby if filterby in searchbar_filters else 'all'

        domain = self._get_borrowings_domain() + searchbar_filters[filterby]['domain']
        total = Borrowing.search_count(domain)
        pager = portal_pager(
            url='/my/borrowings',
            url_args={'sortby': sortby, 'filterby': filterby},
            total=total,
            page=page,
            step=self._items_per_page,
        )
        # Search AS THE USER (record rules apply)...
        borrowings = Borrowing.search(
            domain,
            order=searchbar_sortings[sortby]['order'],
            limit=self._items_per_page,
            offset=pager['offset'],
        )
        # ...remember the ids for prev/next arrows on the detail page.
        request.session['my_borrowings_history'] = borrowings.ids[:100]

        values.update({
            # ...then sudo() ONLY for rendering, so related fields (book,
            # member) the portal user cannot read directly still display.
            'borrowings': borrowings.sudo(),
            'page_name': 'borrowing',
            'pager': pager,
            'default_url': '/my/borrowings',
            'searchbar_sortings': searchbar_sortings,
            'sortby': sortby,
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
            'today': Date.context_today(Borrowing),
        })
        return request.render('library_management.portal_my_borrowings', values)

    # -------------------------------------------------------------------------
    # /my/borrowings/<id> : detail page (also reachable with ?access_token=)
    # -------------------------------------------------------------------------
    @http.route(
        '/my/borrowings/<int:borrowing_id>',
        type='http', auth='public', website=True,
    )
    def portal_my_borrowing(self, borrowing_id, access_token=None, **kwargs):
        """auth='public' on purpose: a share link (Share button on the
        backend form) carries an access_token that lets a NOT logged-in
        person open this one record. _document_check_access() validates
        either the user's read access or the token, and returns a sudo
        record.
        """
        try:
            borrowing_sudo = self._document_check_access(
                'library.borrowing', borrowing_id, access_token)
        except (AccessError, MissingError):
            return request.redirect('/my')

        values = self._get_page_view_values(
            borrowing_sudo, access_token,
            {'borrowing': borrowing_sudo, 'page_name': 'borrowing'},
            'my_borrowings_history', False,
        )
        return request.render('library_management.portal_my_borrowing', values)

    # -------------------------------------------------------------------------
    # /my/requests : book requests made from the website
    # -------------------------------------------------------------------------
    @http.route(
        ['/my/requests', '/my/requests/page/<int:page>'],
        type='http', auth='user', website=True,
    )
    def portal_my_book_requests(self, page=1, filterby=None, **kwargs):
        values = self._prepare_portal_layout_values()
        BookRequest = request.env['library.book.request']

        searchbar_filters = {
            'all': {'label': _('All'), 'domain': []},
            'requested': {'label': _('Pending'), 'domain': [('state', '=', 'requested')]},
            'approved': {'label': _('Approved'), 'domain': [('state', '=', 'approved')]},
            'rejected': {'label': _('Rejected'), 'domain': [('state', '=', 'rejected')]},
        }
        filterby = filterby if filterby in searchbar_filters else 'all'
        # Same ownership condition as borrowings: partner_id = current user.
        domain = self._get_borrowings_domain() + searchbar_filters[filterby]['domain']

        pager = portal_pager(
            url='/my/requests',
            url_args={'filterby': filterby},
            total=BookRequest.search_count(domain),
            page=page,
            step=self._items_per_page,
        )
        book_requests = BookRequest.search(
            domain, limit=self._items_per_page, offset=pager['offset'])

        values.update({
            'book_requests': book_requests.sudo(),
            'page_name': 'book_request',
            'pager': pager,
            'default_url': '/my/requests',
            'searchbar_filters': searchbar_filters,
            'filterby': filterby,
        })
        return request.render('library_management.portal_my_book_requests', values)

    @http.route(
        '/my/requests/<int:request_id>/cancel',
        type='http', auth='user', website=True, methods=['POST'],
    )
    def portal_cancel_book_request(self, request_id, **kwargs):
        """Let requesters withdraw a pending request.

        The record rule only lets users READ their own requests, so we
        check ownership through _document_check_access() (raises if the
        user can't read it) before cancelling with the returned sudo record.
        """
        try:
            request_sudo = self._document_check_access('library.book.request', request_id)
        except (AccessError, MissingError):
            return request.redirect('/my/requests')
        if request_sudo.state == 'requested':
            request_sudo.action_cancel()
        return request.redirect('/my/requests')
