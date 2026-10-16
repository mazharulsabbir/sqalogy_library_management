# -*- coding: utf-8 -*-
# =============================================================================
# WEEK 11: Odoo Website Development -> (1) Website Basics
# =============================================================================
# To show a model on the website we usually mix in `website.published.mixin`.
# It gives us, for free:
#   * is_published / website_published  -> the "Published" toggle
#   * website_url (computed)            -> where the record lives on the site
#   * website_publish_button()          -> the "Go to Website" smart button
#
# `_name` == the first `_inherit` item => we EXTEND library.book (same table)
# and add the mixin to it. Odoo 19 requires `_name` to be explicit here: with
# a multi-item `_inherit` and no `_name` it would derive a NEW model name from
# the class name ("library.book.website"). This keeps all Week 11 additions
# in one file instead of touching book.py.
# =============================================================================

from odoo import fields, models


class LibraryBookWebsite(models.Model):
    _name = 'library.book'
    _inherit = ['library.book', 'website.published.mixin']

    cover_image = fields.Image(
        string='Cover',
        max_width=512,
        max_height=512,
        help='Cover picture shown on the public catalog',
    )
    website_description = fields.Html(
        string='Website Description',
        sanitize=True,
        translate=True,
        help='Rich-text description displayed on the public book page',
    )

    def _compute_website_url(self):
        """Tell the mixin where a book lives on the website.

        WEEK 11: Controllers <-> Models
        The URL built here MUST match a route declared in
        controllers/main.py (`/library/book/<model("library.book"):book>`).
        `_slug()` turns a record into "the-hobbit-7" (name + id) which the
        `model(...)` route converter knows how to read back.
        """
        super()._compute_website_url()
        for book in self:
            if book.id:
                book.website_url = '/library/book/%s' % self.env['ir.http']._slug(book)
