# -*- coding: utf-8 -*-
# =============================================================================
# WEEK 11: Odoo Website Development -> (2) Controllers / @http.route
# =============================================================================
# A controller is a Python class inheriting `http.Controller`. Each method
# decorated with `@http.route` answers one (or several) URLs.
#
# The most important @http.route arguments:
#   route    : '/url' or a list of URLs. Converters: <int:page>,
#              <model("library.book"):book>  (turns "the-hobbit-7" into a record)
#   type     : 'http'    -> returns HTML / any HTTP response (browser pages)
#              'jsonrpc' -> JSON-RPC 2.0 in/out (called from JS via rpc())
#   auth     : 'public'  -> anyone, anonymous visitors run as the Public user
#              'user'    -> must be logged in (redirects to /web/login)
#              'none'    -> no user, no env with a database (rarely used)
#   website  : True -> website context (layout, menus, language, pager...)
#   methods  : ['GET'] / ['POST'] ... restrict HTTP verbs
#   csrf     : True by default for POST on type='http' -> forms must send
#              the `csrf_token` hidden input
#   sitemap  : include the URL in /sitemap.xml
#
# Security golden rule: code runs AS THE VISITOR (request.env.user). Access
# rights (ir.model.access.csv) and record rules still apply. Only use
# .sudo() when you have *already* checked the visitor may do the action.
# =============================================================================

from markupsafe import escape
from werkzeug.exceptions import NotFound

from odoo import _, http
from odoo.http import request


class LibraryWebsite(http.Controller):

    _books_per_page = 12

    # -------------------------------------------------------------------------
    # 1. The smallest possible route
    # -------------------------------------------------------------------------
    @http.route('/library/hello', type='http', auth='public', website=True)
    def hello(self, name=None, **kwargs):
        """Query-string params arrive as keyword arguments.

        Try: /library/hello?name=Rahim
        Returning a plain string is allowed, but real pages use
        request.render() with a QWeb template (see catalog() below).
        escape() matters: `name` comes from the URL, never echo it raw
        into HTML (XSS). QWeb's t-out escapes automatically for us.
        """
        return _("Hello %s, welcome to the Library website!", escape(name or _("visitor")))

    # -------------------------------------------------------------------------
    # 2. Catalog page: multiple URLs, <int:> converter, search, pager
    # -------------------------------------------------------------------------
    @http.route(
        ['/library', '/library/page/<int:page>'],
        type='http', auth='public', website=True, sitemap=True,
    )
    def catalog(self, page=1, search='', category=None, **kwargs):
        Book = request.env['library.book']

        # Internal users bypass the "published only" record rule, so we filter
        # explicitly too: the public catalog must look the same for everyone.
        domain = [('is_published', '=', True)]
        if search:
            domain += ['|', '|',
                       ('name', 'ilike', search),
                       ('author', 'ilike', search),
                       ('isbn', 'ilike', search)]
        current_category = request.env['library.category']
        if category and str(category).isdigit():
            current_category = current_category.browse(int(category)).exists()
            if current_category:
                domain += [('category_ids', 'in', current_category.ids)]

        total = Book.search_count(domain)
        pager = request.website.pager(
            url='/library',
            total=total,
            page=page,
            step=self._books_per_page,
            url_args={'search': search, 'category': category},
        )
        books = Book.search(domain, limit=self._books_per_page, offset=pager['offset'])

        # request.render(template_xmlid, values) -> QWeb renders the template;
        # every key of the dict becomes a variable inside the template.
        return request.render('library_management.website_library_catalog', {
            'books': books,
            'categories': request.env['library.category'].search([]),
            'current_category': current_category,
            'search': search,
            'pager': pager,
            'total': total,
        })

    # -------------------------------------------------------------------------
    # 3. Detail page: the model() converter
    # -------------------------------------------------------------------------
    @http.route(
        '/library/book/<model("library.book"):book>',
        type='http', auth='public', website=True, sitemap=True,
    )
    def book_detail(self, book, requested=False, **kwargs):
        """`book` is already a library.book record (browsed as the visitor).

        The converter does NOT check access, so we do it ourselves:
        unpublished books must 404 unless the user can publish them.
        """
        if not book.exists() or not book.has_access('read'):
            raise NotFound()
        if not book.is_published and not book.can_publish:
            raise NotFound()
        return request.render('library_management.website_library_book', {
            'book': book,
            'requested': requested,
            # main_object lets the website editor's "Publish" toggle and
            # SEO tools work on this record.
            'main_object': book,
        })

    # -------------------------------------------------------------------------
    # 4. Handling a form POST (CSRF protected, logged-in users only)
    # -------------------------------------------------------------------------
    @http.route(
        '/library/book/<model("library.book"):book>/request',
        type='http', auth='user', website=True, methods=['POST'],
    )
    def book_request(self, book, message='', **kwargs):
        """Post a reservation request in the book's chatter.

        auth='user'      -> anonymous visitors are redirected to the login page
        methods=['POST'] -> a GET on this URL returns 405
        csrf (default)   -> the form MUST contain `csrf_token`
        """
        if not book.exists() or not book.has_access('read') or not book.is_published:
            raise NotFound()
        partner = request.env.user.partner_id
        body = _("Reservation request from %(name)s: %(msg)s",
                 name=partner.name, msg=message or _("(no message)"))
        # Portal users cannot write on books, so sudo() is needed to post.
        # Safe: we checked above that they may read this published book, and
        # message_post escapes the plain-text body.
        book.sudo().message_post(
            body=body,
            author_id=partner.id,
            message_type='comment',
            subtype_xmlid='mail.mt_note',
        )
        return request.redirect('%s?requested=1' % book.website_url)

    # -------------------------------------------------------------------------
    # 5. JSON endpoints
    # -------------------------------------------------------------------------
    @http.route('/library/api/books', type='http', auth='public', methods=['GET'])
    def api_books(self, **kwargs):
        """Plain HTTP GET returning JSON (easy to test with curl / browser).

        curl http://localhost:8069/library/api/books
        """
        books = request.env['library.book'].search(
            [('is_published', '=', True)], limit=50)
        return request.make_json_response([{
            'id': book.id,
            'title': book.name,
            'author': book.author,
            'isbn': book.isbn,
            'state': book.state,
            'url': book.website_url,
        } for book in books])

    @http.route('/library/api/availability', type='jsonrpc', auth='public')
    def api_availability(self, book_id):
        """JSON-RPC endpoint: params come from the JSON body, the return value
        is wrapped in {"jsonrpc": "2.0", "result": ...} automatically.

        curl -X POST http://localhost:8069/library/api/availability \\
             -H "Content-Type: application/json" \\
             -d '{"jsonrpc": "2.0", "params": {"book_id": 1}}'
        """
        book = request.env['library.book'].browse(int(book_id)).exists()
        if not book or not book.has_access('read') or not book.is_published:
            return {'error': _("Book not found")}
        return {'id': book.id, 'title': book.name, 'available': book.state == 'available'}
