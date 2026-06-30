# Week 8: Odoo API Decorators

## Learning Objectives

By the end of this session, you will understand:

- What decorators are and why Odoo uses them
- How to use each API decorator correctly
- When to choose one decorator over another
- Common patterns and best practices

---

## Table of Contents

1. [Introduction to Decorators](#1-introduction-to-decorators)
2. [@api.model](#2-apimodel)
3. [@api.model_create_multi](#3-apimodel_create_multi)
4. [@api.depends](#4-apidepends)
5. [@api.depends_context](#5-apidepends_context)
6. [@api.onchange](#6-apionchange)
7. [@api.constrains](#7-apiconstrains)
8. [@api.ondelete](#8-apiondelete)
9. [Decorator Comparison Table](#9-decorator-comparison-table)
10. [Best Practices](#10-best-practices)

---

## 1. Introduction to Decorators

### What is a Decorator?

A decorator is a Python function that modifies the behavior of another function. In Odoo, decorators from the `api` module tell the ORM how to handle method calls.

```python
from odoo import api, fields, models

class MyModel(models.Model):
    _name = 'my.model'

    @api.depends('field_a')  # <-- This is a decorator
    def _compute_field_b(self):
        # Method logic here
        pass
```

### Why Does Odoo Use Decorators?

| Purpose | Benefit |
|---------|---------|
| **Caching** | Avoid redundant computations |
| **Dependency Tracking** | Automatically recompute when dependencies change |
| **Validation** | Enforce data integrity rules |
| **UI Behavior** | Control form field interactions |
| **Batch Processing** | Optimize database operations |

### Import Statement

```python
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
```

---

## 2. @api.model

### Definition

`@api.model` marks a method that operates at the **model level** rather than on specific records. The `self` parameter represents an empty recordset of that model.

### When to Use

- Methods that don't need existing record data
- Utility/helper methods
- Custom search methods
- Methods called from XML-RPC/external APIs

### Syntax

```python
@api.model
def method_name(self, arguments):
    # self is an empty recordset
    # Access model via self.env['model.name']
    pass
```

### Library Management Examples

```python
class LibraryBook(models.Model):
    _name = 'library.book'
    _description = 'Library Book'

    name = fields.Char(string='Title', required=True)
    isbn = fields.Char(string='ISBN')
    state = fields.Selection([
        ('available', 'Available'),
        ('borrowed', 'Borrowed'),
        ('lost', 'Lost'),
    ], default='available')

    @api.model
    def get_available_books_count(self):
        """
        Returns total count of available books.
        Called without any specific record context.
        """
        return self.search_count([('state', '=', 'available')])

    @api.model
    def search_by_isbn(self, isbn):
        """
        Find a book by its ISBN number.
        Returns a recordset (possibly empty).
        """
        return self.search([('isbn', '=', isbn)], limit=1)

    @api.model
    def get_books_by_category(self, category_name):
        """
        Utility method to find all books in a category.
        """
        category = self.env['library.category'].search([
            ('name', 'ilike', category_name)
        ], limit=1)
        if category:
            return category.book_ids
        return self.browse()  # Empty recordset

    @api.model
    def get_dashboard_data(self):
        """
        Return statistics for a dashboard widget.
        """
        return {
            'total_books': self.search_count([]),
            'available': self.search_count([('state', '=', 'available')]),
            'borrowed': self.search_count([('state', '=', 'borrowed')]),
            'lost': self.search_count([('state', '=', 'lost')]),
        }
```

### Key Points

- `self` is an **empty recordset** - no record IDs
- Use `self.env` to access other models
- Use `self.search()` to find records
- Ideal for utility methods and statistics

---

## 3. @api.model_create_multi

### Definition

`@api.model_create_multi` decorates the `create()` method to handle **batch creation** of records. The method receives a **list** of dictionaries instead of a single dictionary.

### When to Use

- Overriding the `create()` method
- Generating sequences or auto-values on record creation
- Performing actions before/after record creation

### Syntax

```python
@api.model_create_multi
def create(self, vals_list):
    # vals_list is a LIST of dictionaries
    # Process each dict if needed
    for vals in vals_list:
        # Modify vals here
        pass
    return super().create(vals_list)
```

### Library Management Examples

```python
class LibraryBorrowing(models.Model):
    _name = 'library.borrowing'
    _description = 'Book Borrowing Record'

    name = fields.Char(string='Reference', readonly=True, copy=False)
    book_id = fields.Many2one('library.book', required=True)
    member_id = fields.Many2one('library.member', required=True)
    borrow_date = fields.Date(default=fields.Date.today)
    expected_return_date = fields.Date()
    state = fields.Selection([
        ('borrowed', 'Borrowed'),
        ('returned', 'Returned'),
    ], default='borrowed')

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create to:
        1. Generate sequence number for each record
        2. Update book state to 'borrowed'
        3. Set default expected return date
        """
        for vals in vals_list:
            # Generate sequence number
            if not vals.get('name'):
                vals['name'] = self.env['ir.sequence'].next_by_code(
                    'library.borrowing'
                ) or 'New'

            # Set default expected return date (14 days from borrow)
            if not vals.get('expected_return_date') and vals.get('borrow_date'):
                borrow_date = fields.Date.from_string(vals['borrow_date'])
                vals['expected_return_date'] = borrow_date + timedelta(days=14)

        # Call parent create
        records = super().create(vals_list)

        # Update book states after creation
        for record in records:
            record.book_id.state = 'borrowed'

        return records


class LibraryMember(models.Model):
    _name = 'library.member'
    _description = 'Library Member'

    name = fields.Char(required=True)
    member_code = fields.Char(string='Member ID', readonly=True, copy=False)
    email = fields.Char()
    phone = fields.Char()
    membership_date = fields.Date(default=fields.Date.today)
    active = fields.Boolean(default=True)

    @api.model_create_multi
    def create(self, vals_list):
        """
        Generate unique member code on creation.
        Format: MEM-YYYY-XXXX
        """
        for vals in vals_list:
            if not vals.get('member_code'):
                vals['member_code'] = self.env['ir.sequence'].next_by_code(
                    'library.member'
                ) or 'MEM-0000'

        return super().create(vals_list)
```

### Batch Creation Example

```python
# Creating multiple records at once (efficient)
borrowings = self.env['library.borrowing'].create([
    {'book_id': 1, 'member_id': 10, 'borrow_date': '2024-01-15'},
    {'book_id': 2, 'member_id': 10, 'borrow_date': '2024-01-15'},
    {'book_id': 3, 'member_id': 11, 'borrow_date': '2024-01-15'},
])
# All 3 records created in optimized batch operation
```

### Key Points

- `vals_list` is always a **list** (even for single record creation)
- Always call `super().create(vals_list)` to complete creation
- Process **before** super() for pre-creation modifications
- Process **after** super() when you need the created record IDs

---

## 4. @api.depends

### Definition

`@api.depends` specifies which fields trigger **recomputation** of a computed field. When any dependency changes, the compute method is called automatically.

### When to Use

- All computed fields that depend on other field values
- Stored computed fields (`store=True`)
- Non-stored computed fields

### Syntax

```python
field_name = fields.Type(compute='_compute_field_name', store=True)

@api.depends('dependency_field_1', 'dependency_field_2')
def _compute_field_name(self):
    for record in self:
        record.field_name = # computed value
```

### Dependency Formats

```python
# Single field
@api.depends('name')

# Multiple fields
@api.depends('price', 'quantity')

# Related field (through Many2one)
@api.depends('partner_id.name')

# One2many/Many2many field and its subfield
@api.depends('line_ids.subtotal')

# Multiple levels deep
@api.depends('order_id.partner_id.country_id.code')
```

### Library Management Examples

```python
class LibraryBook(models.Model):
    _name = 'library.book'
    _description = 'Library Book'

    name = fields.Char(string='Title', required=True)
    author = fields.Char()
    borrowing_ids = fields.One2many('library.borrowing', 'book_id')
    state = fields.Selection([
        ('available', 'Available'),
        ('borrowed', 'Borrowed'),
    ])

    # Simple computed field
    borrowing_count = fields.Integer(
        string='Times Borrowed',
        compute='_compute_borrowing_count',
        store=True
    )

    # Computed from related records
    current_borrower = fields.Char(
        string='Current Borrower',
        compute='_compute_current_borrower'
    )

    # Multiple dependencies
    display_name_full = fields.Char(
        compute='_compute_display_name_full',
        store=True
    )

    @api.depends('borrowing_ids')
    def _compute_borrowing_count(self):
        """Count total number of times this book was borrowed."""
        for book in self:
            book.borrowing_count = len(book.borrowing_ids)

    @api.depends('borrowing_ids.state', 'borrowing_ids.member_id.name')
    def _compute_current_borrower(self):
        """Get name of current borrower if book is borrowed."""
        for book in self:
            active_borrowing = book.borrowing_ids.filtered(
                lambda b: b.state == 'borrowed'
            )
            if active_borrowing:
                book.current_borrower = active_borrowing[0].member_id.name
            else:
                book.current_borrower = False

    @api.depends('name', 'author')
    def _compute_display_name_full(self):
        """Combine title and author for display."""
        for book in self:
            if book.author:
                book.display_name_full = f"{book.name} by {book.author}"
            else:
                book.display_name_full = book.name


class LibraryBorrowing(models.Model):
    _name = 'library.borrowing'
    _description = 'Book Borrowing Record'

    book_id = fields.Many2one('library.book', required=True)
    member_id = fields.Many2one('library.member', required=True)
    borrow_date = fields.Date(default=fields.Date.today)
    return_date = fields.Date()
    expected_return_date = fields.Date()
    state = fields.Selection([
        ('borrowed', 'Borrowed'),
        ('returned', 'Returned'),
    ], default='borrowed')

    # Computed fields
    days_borrowed = fields.Integer(
        compute='_compute_days_borrowed',
        store=True
    )
    is_overdue = fields.Boolean(
        compute='_compute_is_overdue',
        store=True
    )
    overdue_days = fields.Integer(
        compute='_compute_overdue_days',
        store=True
    )

    @api.depends('borrow_date', 'return_date', 'state')
    def _compute_days_borrowed(self):
        """Calculate number of days the book was/is borrowed."""
        today = fields.Date.today()
        for record in self:
            if record.borrow_date:
                end_date = record.return_date or today
                delta = end_date - record.borrow_date
                record.days_borrowed = delta.days
            else:
                record.days_borrowed = 0

    @api.depends('expected_return_date', 'return_date', 'state')
    def _compute_is_overdue(self):
        """Check if borrowing is overdue."""
        today = fields.Date.today()
        for record in self:
            if record.state == 'borrowed' and record.expected_return_date:
                record.is_overdue = today > record.expected_return_date
            else:
                record.is_overdue = False

    @api.depends('expected_return_date', 'state')
    def _compute_overdue_days(self):
        """Calculate number of days overdue."""
        today = fields.Date.today()
        for record in self:
            if record.is_overdue and record.expected_return_date:
                delta = today - record.expected_return_date
                record.overdue_days = delta.days
            else:
                record.overdue_days = 0
```

### Key Points

- Always iterate over `self` (recordset may contain multiple records)
- Stored computed fields are written to database
- Non-stored computed fields are calculated on-the-fly
- Dependencies can traverse relations with dot notation
- Over-specifying dependencies impacts performance

---

## 5. @api.depends_context

### Definition

`@api.depends_context` specifies **context keys** that affect a computed field's value. When the context changes, the field is recomputed.

### When to Use

- Computed fields that depend on user's language
- Fields that depend on current company (multi-company)
- Fields affected by other context values (timezone, etc.)

### Syntax

```python
@api.depends_context('context_key_1', 'context_key_2')
def _compute_field_name(self):
    context_value = self.env.context.get('context_key_1')
    for record in self:
        # Use context_value in computation
        pass
```

### Library Management Examples

```python
class LibraryBook(models.Model):
    _name = 'library.book'
    _description = 'Library Book'

    name = fields.Char(string='Title', required=True)
    description = fields.Text()
    price = fields.Float()
    currency_id = fields.Many2one('res.currency')

    # Context-dependent computed fields
    price_in_company_currency = fields.Float(
        compute='_compute_price_in_company_currency'
    )

    availability_message = fields.Char(
        compute='_compute_availability_message'
    )

    @api.depends('price', 'currency_id')
    @api.depends_context('company')
    def _compute_price_in_company_currency(self):
        """
        Convert book price to current company's currency.
        Result changes based on which company user is working in.
        """
        for book in self:
            if book.price and book.currency_id:
                company = self.env.company
                book.price_in_company_currency = book.currency_id._convert(
                    book.price,
                    company.currency_id,
                    company,
                    fields.Date.today()
                )
            else:
                book.price_in_company_currency = book.price

    @api.depends('state')
    @api.depends_context('lang')
    def _compute_availability_message(self):
        """
        Generate availability message in user's language.
        Changes when user switches language.
        """
        for book in self:
            if book.state == 'available':
                book.availability_message = _("This book is available for borrowing")
            elif book.state == 'borrowed':
                book.availability_message = _("This book is currently borrowed")
            else:
                book.availability_message = _("This book is not available")


class LibraryMember(models.Model):
    _name = 'library.member'
    _description = 'Library Member'

    name = fields.Char(required=True)
    borrowing_ids = fields.One2many('library.borrowing', 'member_id')
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)

    # Company-specific statistics
    borrowing_count_company = fields.Integer(
        compute='_compute_borrowing_count_company'
    )

    @api.depends('borrowing_ids')
    @api.depends_context('company')
    def _compute_borrowing_count_company(self):
        """
        Count borrowings for current company only.
        In multi-company setup, shows only relevant data.
        """
        current_company = self.env.company
        for member in self:
            company_borrowings = member.borrowing_ids.filtered(
                lambda b: b.company_id == current_company
            )
            member.borrowing_count_company = len(company_borrowings)
```

### Common Context Keys

| Key | Description |
|-----|-------------|
| `'lang'` | User's language code (e.g., 'en_US', 'ar_001') |
| `'company'` | Current company ID |
| `'tz'` | User's timezone |
| `'uid'` | Current user ID |
| `'allowed_company_ids'` | List of allowed company IDs |

### Key Points

- Combine with `@api.depends` when needed
- Access context via `self.env.context.get('key')`
- Current company: `self.env.company`
- Current user: `self.env.user`
- Non-stored computed fields only (usually)

---

## 6. @api.onchange

### Definition

`@api.onchange` triggers a method when specified fields change **in the UI form view**. Used to auto-fill related fields or show warnings.

### When to Use

- Auto-populate fields based on selection
- Show warnings or guidance to users
- Calculate preview values before saving
- Provide real-time feedback in forms

### Syntax

```python
@api.onchange('field_name')
def _onchange_field_name(self):
    # self is a pseudo-record (not saved yet)
    # Modify self.other_field directly
    # Optionally return a warning
    pass
```

### Library Management Examples

```python
class LibraryBorrowing(models.Model):
    _name = 'library.borrowing'
    _description = 'Book Borrowing Record'

    book_id = fields.Many2one('library.book', required=True)
    member_id = fields.Many2one('library.member')
    borrower_name = fields.Char()
    borrower_email = fields.Char()
    borrower_phone = fields.Char()
    borrow_date = fields.Date(default=fields.Date.today)
    expected_return_date = fields.Date()

    @api.onchange('member_id')
    def _onchange_member_id(self):
        """
        Auto-fill borrower details when member is selected.
        """
        if self.member_id:
            self.borrower_name = self.member_id.name
            self.borrower_email = self.member_id.email
            self.borrower_phone = self.member_id.phone

    @api.onchange('book_id')
    def _onchange_book_id(self):
        """
        Warn user if selected book is already borrowed.
        Also set default expected return date.
        """
        if self.book_id:
            # Set default return date (14 days)
            if not self.expected_return_date:
                self.expected_return_date = fields.Date.today() + timedelta(days=14)

            # Check if book is available
            if self.book_id.state == 'borrowed':
                return {
                    'warning': {
                        'title': _("Book Not Available"),
                        'message': _(
                            "The book '%s' is currently borrowed by another member. "
                            "Please choose a different book or wait for its return."
                        ) % self.book_id.name,
                    }
                }

    @api.onchange('borrow_date')
    def _onchange_borrow_date(self):
        """
        Update expected return date when borrow date changes.
        """
        if self.borrow_date:
            self.expected_return_date = self.borrow_date + timedelta(days=14)


class LibraryBook(models.Model):
    _name = 'library.book'
    _description = 'Library Book'

    name = fields.Char(string='Title', required=True)
    isbn = fields.Char()
    author = fields.Char()
    category_ids = fields.Many2many('library.category')

    # Auto-filled fields
    suggested_category_ids = fields.Many2many(
        'library.category',
        'book_suggested_category_rel',
        string='Suggested Categories'
    )

    @api.onchange('author')
    def _onchange_author(self):
        """
        Suggest categories based on author's other books.
        """
        if self.author:
            # Find other books by same author
            other_books = self.env['library.book'].search([
                ('author', '=', self.author),
                ('id', '!=', self._origin.id),  # Exclude current record
            ])
            if other_books:
                # Collect categories from author's other books
                categories = other_books.mapped('category_ids')
                if categories:
                    return {
                        'warning': {
                            'title': _("Category Suggestion"),
                            'message': _(
                                "Other books by %s are in these categories: %s"
                            ) % (self.author, ', '.join(categories.mapped('name'))),
                        }
                    }

    @api.onchange('isbn')
    def _onchange_isbn(self):
        """
        Validate ISBN format and show warning if invalid.
        """
        if self.isbn:
            # Remove hyphens and spaces
            clean_isbn = self.isbn.replace('-', '').replace(' ', '')

            if len(clean_isbn) not in (10, 13):
                return {
                    'warning': {
                        'title': _("Invalid ISBN"),
                        'message': _("ISBN must be 10 or 13 digits."),
                    }
                }

            if not clean_isbn.isdigit():
                return {
                    'warning': {
                        'title': _("Invalid ISBN"),
                        'message': _("ISBN must contain only digits."),
                    }
                }
```

### Warning Return Format

```python
return {
    'warning': {
        'title': "Warning Title",
        'message': "Detailed warning message for the user.",
    }
}
```

### Domain Return Format

```python
@api.onchange('country_id')
def _onchange_country_id(self):
    """Filter cities based on selected country."""
    if self.country_id:
        return {
            'domain': {
                'city_id': [('country_id', '=', self.country_id.id)]
            }
        }
```

### Key Points

- Runs **only in UI** (form views), not on API/import
- `self` is a pseudo-record, not yet saved to database
- Use `self._origin` to access the original saved record
- Changes to `self` fields are reflected immediately in form
- Does NOT trigger `@api.constrains` validation

---

## 7. @api.constrains

### Definition

`@api.constrains` validates data **on create and write operations**. If validation fails, raises a `ValidationError` to prevent saving.

### When to Use

- Enforce business rules
- Validate field values
- Check relationships between fields
- Ensure data integrity

### Syntax

```python
from odoo.exceptions import ValidationError

@api.constrains('field1', 'field2')
def _check_constraint_name(self):
    for record in self:
        if not valid_condition:
            raise ValidationError(_("Error message"))
```

### Library Management Examples

```python
class LibraryBook(models.Model):
    _name = 'library.book'
    _description = 'Library Book'

    name = fields.Char(string='Title', required=True)
    isbn = fields.Char()
    publication_year = fields.Integer()
    page_count = fields.Integer()
    price = fields.Float()

    @api.constrains('isbn')
    def _check_isbn(self):
        """Validate ISBN format: must be 10 or 13 digits."""
        for book in self:
            if book.isbn:
                clean_isbn = book.isbn.replace('-', '').replace(' ', '')
                if len(clean_isbn) not in (10, 13):
                    raise ValidationError(_(
                        "ISBN must be exactly 10 or 13 digits. "
                        "Got %d digits for book '%s'."
                    ) % (len(clean_isbn), book.name))
                if not clean_isbn.isdigit():
                    raise ValidationError(_(
                        "ISBN must contain only digits (and optional hyphens). "
                        "Invalid ISBN for book '%s'."
                    ) % book.name)

    @api.constrains('publication_year')
    def _check_publication_year(self):
        """Ensure publication year is reasonable."""
        current_year = fields.Date.today().year
        for book in self:
            if book.publication_year:
                if book.publication_year < 1450:  # Before printing press
                    raise ValidationError(_(
                        "Publication year cannot be before 1450. "
                        "Check the year for '%s'."
                    ) % book.name)
                if book.publication_year > current_year + 1:
                    raise ValidationError(_(
                        "Publication year cannot be in the future. "
                        "Check the year for '%s'."
                    ) % book.name)

    @api.constrains('page_count', 'price')
    def _check_positive_values(self):
        """Ensure page count and price are positive."""
        for book in self:
            if book.page_count and book.page_count < 1:
                raise ValidationError(_(
                    "Page count must be positive for book '%s'."
                ) % book.name)
            if book.price and book.price < 0:
                raise ValidationError(_(
                    "Price cannot be negative for book '%s'."
                ) % book.name)


class LibraryBorrowing(models.Model):
    _name = 'library.borrowing'
    _description = 'Book Borrowing Record'

    book_id = fields.Many2one('library.book', required=True)
    member_id = fields.Many2one('library.member')
    borrow_date = fields.Date(required=True)
    return_date = fields.Date()
    expected_return_date = fields.Date()
    state = fields.Selection([
        ('borrowed', 'Borrowed'),
        ('returned', 'Returned'),
    ], default='borrowed')

    @api.constrains('book_id', 'state')
    def _check_book_availability(self):
        """Ensure book is not already borrowed by someone else."""
        for record in self:
            if record.state == 'borrowed':
                # Check for other active borrowings of same book
                other_borrowings = self.search([
                    ('book_id', '=', record.book_id.id),
                    ('state', '=', 'borrowed'),
                    ('id', '!=', record.id),
                ])
                if other_borrowings:
                    raise ValidationError(_(
                        "The book '%s' is already borrowed. "
                        "A book can only be borrowed by one member at a time."
                    ) % record.book_id.name)

    @api.constrains('borrow_date', 'return_date')
    def _check_dates(self):
        """Ensure return date is not before borrow date."""
        for record in self:
            if record.return_date and record.borrow_date:
                if record.return_date < record.borrow_date:
                    raise ValidationError(_(
                        "Return date cannot be before borrow date."
                    ))

    @api.constrains('borrow_date', 'expected_return_date')
    def _check_expected_return_date(self):
        """Ensure expected return date is after borrow date."""
        for record in self:
            if record.expected_return_date and record.borrow_date:
                if record.expected_return_date < record.borrow_date:
                    raise ValidationError(_(
                        "Expected return date must be after borrow date."
                    ))

    @api.constrains('member_id')
    def _check_member_borrowing_limit(self):
        """Ensure member hasn't exceeded borrowing limit (max 5 books)."""
        for record in self:
            if record.member_id and record.state == 'borrowed':
                active_borrowings = self.search_count([
                    ('member_id', '=', record.member_id.id),
                    ('state', '=', 'borrowed'),
                ])
                if active_borrowings > 5:
                    raise ValidationError(_(
                        "Member '%s' has reached the maximum borrowing limit "
                        "of 5 books. Please return a book before borrowing more."
                    ) % record.member_id.name)
```

### Key Points

- Triggered on `create()` and `write()` operations
- Always iterate over `self` (may contain multiple records)
- Raise `ValidationError` with translated message using `_()`
- Runs **after** values are in memory but **before** commit
- Also use SQL constraints for database-level uniqueness

### SQL Constraints (Complementary)

```python
_sql_constraints = [
    ('isbn_unique', 'UNIQUE(isbn)', 'ISBN must be unique!'),
    ('positive_price', 'CHECK(price >= 0)', 'Price cannot be negative!'),
]
```

---

## 8. @api.ondelete

### Definition

`@api.ondelete` intercepts record deletion to enforce rules or perform cleanup. Can prevent deletion or execute code before deletion.

### When to Use

- Prevent deletion of records in certain states
- Clean up related data before deletion
- Enforce referential integrity beyond SQL constraints
- Log or audit deletions

### Syntax

```python
@api.ondelete(at_uninstall=False)
def _unlink_check_condition(self):
    for record in self:
        if not_allowed_to_delete:
            raise UserError(_("Cannot delete this record."))
```

### Parameters

- `at_uninstall=False`: Skip check during module uninstall (recommended)
- `at_uninstall=True`: Also check during module uninstall (use carefully)

### Library Management Examples

```python
from odoo.exceptions import UserError

class LibraryBook(models.Model):
    _name = 'library.book'
    _description = 'Library Book'

    name = fields.Char(string='Title', required=True)
    state = fields.Selection([
        ('available', 'Available'),
        ('borrowed', 'Borrowed'),
    ])
    borrowing_ids = fields.One2many('library.borrowing', 'book_id')

    @api.ondelete(at_uninstall=False)
    def _unlink_check_not_borrowed(self):
        """Prevent deletion of currently borrowed books."""
        for book in self:
            if book.state == 'borrowed':
                raise UserError(_(
                    "Cannot delete book '%s' because it is currently borrowed. "
                    "Please wait for the book to be returned first."
                ) % book.name)

    @api.ondelete(at_uninstall=False)
    def _unlink_check_borrowing_history(self):
        """Warn about deletion of books with borrowing history."""
        for book in self:
            if book.borrowing_ids:
                # Instead of blocking, we could archive instead
                raise UserError(_(
                    "Cannot delete book '%s' because it has borrowing history. "
                    "Consider archiving the book instead to preserve records."
                ) % book.name)


class LibraryMember(models.Model):
    _name = 'library.member'
    _description = 'Library Member'

    name = fields.Char(required=True)
    borrowing_ids = fields.One2many('library.borrowing', 'member_id')
    active = fields.Boolean(default=True)

    @api.ondelete(at_uninstall=False)
    def _unlink_check_active_borrowings(self):
        """Prevent deletion of members with unreturned books."""
        for member in self:
            active_borrowings = member.borrowing_ids.filtered(
                lambda b: b.state == 'borrowed'
            )
            if active_borrowings:
                book_names = ', '.join(active_borrowings.mapped('book_id.name'))
                raise UserError(_(
                    "Cannot delete member '%s' because they have unreturned books: %s. "
                    "Please ensure all books are returned first."
                ) % (member.name, book_names))

    @api.ondelete(at_uninstall=False)
    def _unlink_suggest_archive(self):
        """Suggest archiving instead of deleting for members with history."""
        for member in self:
            if member.borrowing_ids:
                raise UserError(_(
                    "Member '%s' has borrowing history. "
                    "Instead of deleting, consider archiving the member "
                    "to preserve historical records. "
                    "Use the 'Archive' action instead."
                ) % member.name)


class LibraryBorrowing(models.Model):
    _name = 'library.borrowing'
    _description = 'Book Borrowing Record'

    name = fields.Char(string='Reference')
    book_id = fields.Many2one('library.book', required=True)
    member_id = fields.Many2one('library.member')
    state = fields.Selection([
        ('borrowed', 'Borrowed'),
        ('returned', 'Returned'),
    ], default='borrowed')

    @api.ondelete(at_uninstall=False)
    def _unlink_check_state(self):
        """Prevent deletion of active borrowings."""
        for record in self:
            if record.state == 'borrowed':
                raise UserError(_(
                    "Cannot delete borrowing record '%s' while the book is still borrowed. "
                    "Please return the book first using the 'Return Book' action."
                ) % record.name)

    @api.ondelete(at_uninstall=False)
    def _unlink_update_book_state(self):
        """
        Update book state if deleting a borrowed record.
        Note: This runs before the record is deleted.
        """
        for record in self:
            if record.state == 'borrowed':
                # This code runs but UserError above prevents reaching here
                # In practice, you'd handle cleanup for allowed deletions
                record.book_id.state = 'available'
```

### Key Points

- Use `UserError` for user-facing deletion blocks
- Use `ValidationError` for data integrity issues
- `at_uninstall=False` is recommended to allow module uninstall
- Runs **before** actual deletion
- Can perform cleanup actions before deletion

---

## 9. Decorator Comparison Table

| Decorator | Trigger | Purpose | Raises |
|-----------|---------|---------|--------|
| `@api.model` | Method call | Model-level operations | N/A |
| `@api.model_create_multi` | `create()` | Batch record creation | N/A |
| `@api.depends` | Field change | Computed field recalc | N/A |
| `@api.depends_context` | Context change | Context-aware computation | N/A |
| `@api.onchange` | UI field change | Form field updates | Warning dict |
| `@api.constrains` | Create/Write | Data validation | `ValidationError` |
| `@api.ondelete` | `unlink()` | Deletion protection | `UserError` |

### Execution Order

```
1. User changes field in form
   └── @api.onchange (UI only, no save yet)

2. User clicks Save
   ├── @api.constrains (validation)
   ├── @api.model_create_multi (if creating)
   └── @api.depends (computed fields update)

3. User clicks Delete
   └── @api.ondelete (before deletion)
```

---

## 10. Best Practices

### General Guidelines

```python
# DO: Use appropriate exception types
from odoo.exceptions import ValidationError, UserError

@api.constrains('field')
def _check_field(self):
    raise ValidationError(_("Data validation error"))  # For data issues

@api.ondelete(at_uninstall=False)
def _check_delete(self):
    raise UserError(_("Operation not allowed"))  # For business rules
```

### Performance Tips

```python
# DO: Iterate over self (handles recordsets efficiently)
@api.depends('line_ids.amount')
def _compute_total(self):
    for record in self:
        record.total = sum(record.line_ids.mapped('amount'))

# DON'T: Make unnecessary database queries in loops
@api.depends('partner_id')
def _compute_something(self):
    for record in self:
        # BAD: Query in loop
        partner = self.env['res.partner'].search([...])
```

### Avoiding Common Mistakes

```python
# DON'T: Forget to iterate over self
@api.depends('name')
def _compute_display(self):
    self.display = self.name.upper()  # WRONG! Fails for multiple records

# DO: Always iterate
@api.depends('name')
def _compute_display(self):
    for record in self:
        record.display = record.name.upper() if record.name else ''
```

### Combining Decorators

```python
# Correct order: depends_context before depends
@api.depends_context('company')
@api.depends('amount', 'currency_id')
def _compute_amount_company_currency(self):
    for record in self:
        # Computation here
        pass
```

### Testing Your Decorators

```python
# Test @api.constrains
def test_isbn_validation(self):
    with self.assertRaises(ValidationError):
        self.env['library.book'].create({
            'name': 'Test Book',
            'isbn': 'invalid',
        })

# Test @api.depends
def test_computed_field(self):
    book = self.env['library.book'].create({'name': 'Test'})
    self.env['library.borrowing'].create({'book_id': book.id, ...})
    self.assertEqual(book.borrowing_count, 1)
```

---

## Summary

| Decorator | Key Point |
|-----------|-----------|
| `@api.model` | Empty recordset, model-level operations |
| `@api.model_create_multi` | List of dicts, batch creation |
| `@api.depends` | Field dependencies, auto-recompute |
| `@api.depends_context` | Context keys, user/company aware |
| `@api.onchange` | UI only, warnings, auto-fill |
| `@api.constrains` | Validation, create/write |
| `@api.ondelete` | Deletion protection, cleanup |

---

## Exercises

1. Add a computed field `days_until_due` that calculates remaining days until expected return
2. Create an onchange that suggests similar books when a category is selected
3. Add a constraint preventing members from borrowing the same book twice simultaneously
4. Implement ondelete protection for categories that have books assigned

---

*Week 8 - Odoo API Decorators | Library Management Module*