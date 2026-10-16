# -*- coding: utf-8 -*-
# =============================================================================
# WEEK 11: Website form -> real record -> backend approval
# =============================================================================
# The "Request this book" form on the website creates a library.book.request.
# A librarian approves it from Library > Operations > Book Requests, which
# creates the library.borrowing for the requester (creating their
# library.member first if they are not a member yet).
#
#   requested --(Approve)--> approved  (borrowing created, book borrowed)
#             --(Reject)---> rejected
#             --(Cancel)---> cancelled (requester withdrew it)
# =============================================================================

from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError, ValidationError


class LibraryBookRequest(models.Model):
    _name = 'library.book.request'
    _description = 'Library Book Request'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _order = 'request_date desc, id desc'

    name = fields.Char(
        string='Reference',
        required=True,
        copy=False,
        readonly=True,
        default=lambda self: _('New'),
    )
    book_id = fields.Many2one(
        'library.book',
        string='Book',
        required=True,
        ondelete='restrict',
        tracking=True,
    )
    partner_id = fields.Many2one(
        'res.partner',
        string='Requested By',
        required=True,
        ondelete='cascade',
        index=True,
        tracking=True,
        default=lambda self: self.env.user.partner_id,
    )
    member_id = fields.Many2one(
        'library.member',
        string='Member',
        compute='_compute_member_id',
        store=True,
        help='Library member linked to the requester (created on approval if missing)',
    )
    message = fields.Text(string='Message')
    request_date = fields.Datetime(
        string='Requested On',
        required=True,
        readonly=True,
        default=fields.Datetime.now,
    )
    expected_return_date = fields.Date(
        string='Return By',
        default=lambda self: fields.Date.context_today(self) + timedelta(days=14),
        help='Expected return date used for the borrowing created on approval',
    )
    state = fields.Selection(
        [
            ('requested', 'Requested'),
            ('approved', 'Approved'),
            ('rejected', 'Rejected'),
            ('cancelled', 'Cancelled'),
        ],
        string='Status',
        default='requested',
        required=True,
        tracking=True,
    )
    reject_reason = fields.Char(string='Rejection Reason', tracking=True)
    borrowing_id = fields.Many2one(
        'library.borrowing',
        string='Borrowing',
        readonly=True,
        copy=False,
    )
    book_state = fields.Selection(related='book_id.state', string='Book Status')

    @api.depends('partner_id')
    def _compute_member_id(self):
        Member = self.env['library.member']
        for request in self:
            request.member_id = Member.search(
                [('partner_id', '=', request.partner_id.id)], limit=1
            ) if request.partner_id else Member

    @api.constrains('book_id', 'partner_id', 'state')
    def _check_single_open_request(self):
        """One open request per person and book."""
        for request in self.filtered(lambda r: r.state == 'requested'):
            duplicate = self.search_count([
                ('id', '!=', request.id),
                ('book_id', '=', request.book_id.id),
                ('partner_id', '=', request.partner_id.id),
                ('state', '=', 'requested'),
            ])
            if duplicate:
                raise ValidationError(
                    _('%(partner)s already has an open request for "%(book)s".',
                      partner=request.partner_id.name, book=request.book_id.name)
                )

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('name', _('New')) == _('New'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'library.book.request'
                ) or _('New')
        return super().create(vals_list)

    # -------------------------------------------------------------------------
    # Actions
    # -------------------------------------------------------------------------
    def _get_or_create_member(self):
        """Return the requester's library.member, creating it if needed.

        library.member uses delegation inheritance on res.partner (Week 7),
        so passing partner_id links the new member to the existing contact
        instead of creating a duplicate contact.
        """
        self.ensure_one()
        # Search again: a member may have been created after the request.
        member = self.member_id or self.env['library.member'].search(
            [('partner_id', '=', self.partner_id.id)], limit=1)
        if not member:
            member = self.env['library.member'].create({'partner_id': self.partner_id.id})
        self.member_id = member
        return member

    def action_approve(self):
        for request in self:
            if request.state != 'requested':
                raise UserError(_('Only pending requests can be approved.'))
            if request.book_id.state != 'available':
                raise UserError(
                    _('"%s" is currently borrowed. Approve the request once it is returned.',
                      request.book_id.name)
                )
            member = request._get_or_create_member()
            partner = request.partner_id
            borrowing = self.env['library.borrowing'].create({
                'book_id': request.book_id.id,
                'member_id': member.id,
                'borrower_name': partner.name,
                'borrower_email': partner.email,
                'borrower_phone': partner.phone,
                'expected_return_date': request.expected_return_date,
                'notes': request.message,
            })
            request.write({'state': 'approved', 'borrowing_id': borrowing.id})
            request.message_post(
                body=_('Request approved. Borrowing %s created.', borrowing.name),
                subtype_xmlid='mail.mt_note',
            )
        return True

    def action_reject(self):
        for request in self:
            if request.state != 'requested':
                raise UserError(_('Only pending requests can be rejected.'))
            request.state = 'rejected'
            request.message_post(
                body=_('Request rejected. %s', request.reject_reason or ''),
                subtype_xmlid='mail.mt_note',
            )
        return True

    def action_cancel(self):
        for request in self:
            if request.state != 'requested':
                raise UserError(_('Only pending requests can be cancelled.'))
            request.state = 'cancelled'
        return True

    def action_reset_to_requested(self):
        self.filtered(lambda r: r.state in ('rejected', 'cancelled')).write({
            'state': 'requested',
            'reject_reason': False,
        })
        return True

    def action_view_borrowing(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'library.borrowing',
            'res_id': self.borrowing_id.id,
            'view_mode': 'form',
        }


class LibraryBook(models.Model):
    _inherit = 'library.book'

    request_ids = fields.One2many('library.book.request', 'book_id', string='Requests')
    pending_request_count = fields.Integer(
        string='Pending Requests',
        compute='_compute_pending_request_count',
    )

    @api.depends('request_ids.state')
    def _compute_pending_request_count(self):
        groups = self.env['library.book.request']._read_group(
            [('book_id', 'in', self.ids), ('state', '=', 'requested')],
            ['book_id'], ['__count'],
        )
        counts = {book.id: count for book, count in groups}
        for book in self:
            book.pending_request_count = counts.get(book.id, 0)

    def action_view_requests(self):
        self.ensure_one()
        return {
            'name': _('Book Requests'),
            'type': 'ir.actions.act_window',
            'res_model': 'library.book.request',
            'view_mode': 'list,form',
            'domain': [('book_id', '=', self.id)],
            'context': {'default_book_id': self.id},
        }
