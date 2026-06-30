# Week 7: Odoo Models & ORM Fundamentals

## Learning Objectives

By the end of this session, you will understand:

- How to define Odoo models and their attributes
- The three types of Odoo inheritance
- How recordsets work and how to manipulate them
- How to use the environment (`self.env`)
- How to write domain expressions for filtering
- Special ORM commands for One2many/Many2many fields

---

## Table of Contents

1. [Odoo Models](#1-odoo-models)
2. [Odoo Inheritance](#2-odoo-inheritance)
3. [Recordsets](#3-recordsets)
4. [Environment (self.env)](#4-environment-selfenv)
5. [Domain Expressions](#5-domain-expressions)
6. [One2many & Many2many Fields](#6-one2many--many2many-fields)
7. [Special ORM Commands](#7-special-orm-commands)
8. [Summary](#8-summary)

---

## 1. Odoo Models

### What is a Model?

A model is a Python class that represents a database table. Each model defines the structure of data (fields) and behavior (methods) for a business object.

```python
from odoo import api, fields, models

class LibraryBook(models.Model):
    _name = 'library.book'           # Technical name (table: library_book)
    _description = 'Library Book'    # Human-readable description

    name = fields.Char(string='Title', required=True)
```

### Model Attributes

| Attribute | Purpose | Example |
|-----------|---------|---------|
| `_name` | Technical name (unique identifier) | `'library.book'` |
| `_description` | Human-readable label | `'Library Book'` |
| `_order` | Default sort order | `'name ASC, id DESC'` |
| `_rec_name` | Field used for display name | `'name'` |
| `_table` | Custom table name (rare) | `'lib_books'` |
| `_inherit` | Inherit from other model(s) | `['mail.thread']` |
| `_inherits` | Delegation inheritance | `{'res.partner': 'partner_id'}` |

### Library Management Example

```python
# library_management/models/category.py

class LibraryCategory(models.Model):
    _name = 'library.category'
    _description = 'Library Book Category'
    _order = 'name'  # Sort alphabetically by default

    name = fields.Char(string='Category', required=True)
    color = fields.Integer(string='Color Index')
    description = fields.Text(string='Description')
    book_ids = fields.Many2many('library.book', string='Books')

    # Computed field
    book_count = fields.Integer(
        string='Number of Books',
        compute='_compute_book_count'
    )

    @api.depends('book_ids')
    def _compute_book_count(self):
        for category in self:
            category.book_count = len(category.book_ids)

    # SQL constraints (database-level)
    _sql_constraints = [
        ('name_unique', 'UNIQUE(name)', 'Category name must be unique!'),
    ]
```

### Field Types Overview

| Type | Description | Example |
|------|-------------|---------|
| `Char` | Short text | `name = fields.Char()` |
| `Text` | Long text | `description = fields.Text()` |
| `Integer` | Whole number | `page_count = fields.Integer()` |
| `Float` | Decimal number | `price = fields.Float()` |
| `Boolean` | True/False | `active = fields.Boolean()` |
| `Date` | Date only | `publish_date = fields.Date()` |
| `Datetime` | Date and time | `created_at = fields.Datetime()` |
| `Selection` | Dropdown choices | `state = fields.Selection([...])` |
| `Many2one` | Link to one record | `author_id = fields.Many2one('res.partner')` |
| `One2many` | Link to many records | `line_ids = fields.One2many(...)` |
| `Many2many` | Link to many (both ways) | `tag_ids = fields.Many2many(...)` |

### Common Field Parameters

```python
name = fields.Char(
    string='Title',           # Label in UI
    required=True,            # Cannot be empty
    readonly=False,           # Editable by default
    default='New',            # Default value
    help='Enter book title',  # Tooltip
    index=True,               # Create database index
    copy=True,                # Copy when duplicating
    tracking=True,            # Track changes in chatter
)
```

---

## 2. Odoo Inheritance

Odoo provides three types of inheritance, each serving different purposes.

### Type 1: Extension Inheritance (Most Common)

**Purpose**: Add fields/methods to an existing model without creating a new table.

**Syntax**: Use `_inherit` with the same model name.

```python
# library_management/models/res_partner.py

class ResPartner(models.Model):
    _inherit = 'res.partner'  # Extend existing model
    # No _name = existing model is modified in-place

    # Add new fields to res.partner
    member_ids = fields.One2many(
        'library.member',
        'partner_id',
        string='Library Memberships'
    )
    is_library_member = fields.Boolean(
        string='Is Library Member',
        compute='_compute_is_library_member',
        store=True
    )

    @api.depends('member_ids')
    def _compute_is_library_member(self):
        for partner in self:
            partner.is_library_member = bool(partner.member_ids)
```

**Key Points**:
- No new database table created
- Fields added to existing table
- All existing partners now have these fields
- Can also override methods

### Type 2: Delegation Inheritance (_inherits)

**Purpose**: Create a new model that transparently accesses fields from a parent model.

**Syntax**: Use `_inherits` dictionary.

```python
# library_management/models/library_member.py

class LibraryMember(models.Model):
    _name = 'library.member'
    _description = 'Library Member'
    _inherits = {'res.partner': 'partner_id'}  # Delegation

    # Required: link to delegated model
    partner_id = fields.Many2one(
        'res.partner',
        required=True,
        ondelete='cascade',
        string='Related Partner'
    )

    # Member-specific fields
    member_code = fields.Char(string='Member ID', required=True)
    membership_date = fields.Date(string='Member Since')
    borrowing_ids = fields.One2many('library.borrowing', 'member_id')
```

**How It Works**:
```python
# Access partner fields directly through member
member = self.env['library.member'].browse(1)

# These work transparently:
print(member.name)       # Actually reads member.partner_id.name
print(member.email)      # Actually reads member.partner_id.email
print(member.member_code)  # Direct field on library.member
```

**Key Points**:
- Creates a NEW table (`library_member`)
- Partner fields accessible without explicit traversal
- Writing to `member.name` updates the partner record
- Both records exist; Odoo handles the linking

### Type 3: Mixin Inheritance (Abstract Models)

**Purpose**: Add reusable behavior (fields + methods) from abstract models.

**Syntax**: Use `_inherit` as a list.

```python
# library_management/models/book.py

class LibraryBook(models.Model):
    _name = 'library.book'
    _description = 'Library Book'
    _inherit = ['mail.thread', 'mail.activity.mixin']  # Mixins

    name = fields.Char(string='Title', required=True, tracking=True)
    state = fields.Selection([
        ('available', 'Available'),
        ('borrowed', 'Borrowed'),
        ('lost', 'Lost'),
    ], default='available', tracking=True)
```

**What `mail.thread` Provides**:
- `message_ids` field (chatter messages)
- `message_post()` method
- Field tracking (with `tracking=True`)
- Followers and notifications

**What `mail.activity.mixin` Provides**:
- `activity_ids` field
- Activity scheduling
- Activity tracking

### Inheritance Comparison

| Type | `_name` | `_inherit` | `_inherits` | New Table? | Use Case |
|------|---------|------------|-------------|------------|----------|
| Extension | No | `'model.name'` | No | No | Add fields to existing model |
| Delegation | Yes | Optional | `{'model': 'field'}` | Yes | Transparent field access |
| Mixin | Yes | `['mixin1', ...]` | No | Yes | Add reusable behavior |

### Visual Diagram

```
EXTENSION INHERITANCE
┌─────────────────────────────┐
│     res.partner (existing)  │
│  + member_ids (new field)   │
│  + is_library_member (new)  │
└─────────────────────────────┘
        Same table

DELEGATION INHERITANCE
┌──────────────────┐     ┌──────────────────┐
│   res.partner    │     │  library.member  │
│  - name          │◄────│  - partner_id    │
│  - email         │     │  - member_code   │
│  - phone         │     │  - membership_dt │
└──────────────────┘     └──────────────────┘
 Separate tables, transparent access

MIXIN INHERITANCE
┌──────────────────┐
│   mail.thread    │  (abstract)
│  - message_ids   │
│  - message_post()│
└────────┬─────────┘
         │ inherit
┌────────▼─────────┐
│   library.book   │
│  - name          │
│  - message_ids   │  (from mixin)
└──────────────────┘
```

---

## 3. Recordsets

### What is a Recordset?

A recordset is a collection of records from the same model. It can contain zero, one, or many records. All ORM methods operate on recordsets.

```python
# Single record (recordset of length 1)
book = self.env['library.book'].browse(1)

# Multiple records (recordset of length 3)
books = self.env['library.book'].browse([1, 2, 3])

# Empty recordset (length 0)
no_books = self.env['library.book'].browse([])
```

### Recordset Properties

```python
# Check if recordset is empty
if books:
    print("Has records")
else:
    print("Empty recordset")

# Get length
count = len(books)  # Number of records

# Get IDs
ids = books.ids  # [1, 2, 3]

# Check single record
books.ensure_one()  # Raises if not exactly 1 record
```

### Iterating Recordsets

**Critical Rule**: Always iterate over `self` in compute/constraint methods.

```python
@api.depends('borrowing_ids')
def _compute_borrowing_count(self):
    # self may contain multiple records!
    for book in self:
        book.borrowing_count = len(book.borrowing_ids)
```

### Recordset Operations

#### Filtering Records

```python
# Filter in-memory (no database query)
available_books = books.filtered(lambda b: b.state == 'available')

# Filter by field value
borrowed_books = books.filtered(lambda b: b.state == 'borrowed')

# Multiple conditions
old_borrowed = books.filtered(
    lambda b: b.state == 'borrowed' and b.borrowing_count > 5
)
```

#### Mapping Fields

```python
# Get list of field values
book_names = books.mapped('name')  # ['Book1', 'Book2', 'Book3']

# Map related field
author_names = borrowings.mapped('book_id.author')

# Map with transformation
upper_names = books.mapped(lambda b: b.name.upper())
```

#### Sorting Records

```python
# Sort by field
sorted_books = books.sorted(key='name')

# Sort descending
sorted_desc = books.sorted(key='name', reverse=True)

# Sort by multiple criteria
sorted_multi = books.sorted(key=lambda b: (b.state, b.name))
```

#### Set Operations

```python
# Union (combine recordsets)
all_books = books1 | books2

# Intersection (common records)
common = books1 & books2

# Difference (in first but not second)
diff = books1 - books2
```

### Library Management Examples

```python
# library_management/models/library_member.py

@api.depends('borrowing_ids', 'borrowing_ids.state')
def _compute_borrowing_stats(self):
    for member in self:
        # Total count
        member.borrowing_count = len(member.borrowing_ids)

        # Filter for active borrowings
        active = member.borrowing_ids.filtered(
            lambda b: b.state == 'borrowed'
        )
        member.active_borrowing_count = len(active)

        # Get list of borrowed book titles
        book_titles = active.mapped('book_id.name')
```

---

## 4. Environment (self.env)

### What is the Environment?

The environment (`self.env`) is the context in which ORM operations execute. It contains:

- **Database cursor**: Connection to database
- **User ID**: Current user performing operations
- **Context**: Dictionary of contextual values
- **Model registry**: Access to all models

### Accessing Other Models

```python
# Get a model's recordset (empty)
Partner = self.env['res.partner']

# Search for records
partners = self.env['res.partner'].search([('is_company', '=', True)])

# Browse specific IDs
partner = self.env['res.partner'].browse(1)

# Create a record
new_partner = self.env['res.partner'].create({
    'name': 'New Partner',
    'email': 'new@example.com',
})
```

### Library Management Examples

```python
# library_management/models/book.py

@api.depends('state')
def _compute_current_borrowing(self):
    for book in self:
        if book.state == 'borrowed':
            # Access another model through env
            borrowing = self.env['library.borrowing'].search([
                ('book_id', '=', book.id),
                ('state', '=', 'borrowed')
            ], limit=1)
            book.current_borrowing_id = borrowing
        else:
            book.current_borrowing_id = False


# library_management/models/library_member.py

@api.model_create_multi
def create(self, vals_list):
    for vals in vals_list:
        if not vals.get('member_code'):
            # Access ir.sequence through env
            vals['member_code'] = self.env['ir.sequence'].next_by_code(
                'library.member'
            ) or 'MEM-0000'
    return super().create(vals_list)
```

### Environment Properties

```python
# Current user
user = self.env.user              # res.users record
user_id = self.env.uid            # User ID (integer)

# Current company
company = self.env.company        # res.company record
company_id = self.env.company.id  # Company ID

# Context dictionary
ctx = self.env.context            # Immutable dict
lang = self.env.context.get('lang', 'en_US')

# Check superuser mode
if self.env.su:
    print("Running as superuser")
```

### Modifying Environment

```python
# Change context (returns new env)
new_env = self.env.with_context(lang='ar_001')
books_arabic = self.env['library.book'].with_context(lang='ar_001').search([])

# Run as different user
admin_env = self.env.with_user(1)
admin_env['res.partner'].create({...})

# Run as superuser (bypass access rights)
sudo_env = self.env.sudo()
sudo_env['library.book'].write({'state': 'lost'})

# Run with specific company
company2_env = self.env.with_company(2)
```

### Common env Patterns

```python
# Get translated text
message = self.env._("This book is available")

# Get system parameter
param = self.env['ir.config_parameter'].sudo().get_param('web.base.url')

# Get current date/time
today = fields.Date.context_today(self)
now = fields.Datetime.now()

# Access mail template
template = self.env.ref('library_management.email_template_overdue')
template.send_mail(self.id)
```

---

## 5. Domain Expressions

### What is a Domain?

A domain is a list of criteria used to filter records in database queries. Each criterion is a tuple: `(field, operator, value)`.

### Basic Syntax

```python
# Simple condition
[('state', '=', 'available')]

# Multiple conditions (implicit AND)
[('state', '=', 'available'), ('author', '=', 'Tagore')]

# Explicit AND
['&', ('state', '=', 'available'), ('author', '=', 'Tagore')]

# OR condition
['|', ('state', '=', 'available'), ('state', '=', 'borrowed')]

# NOT condition
['!', ('state', '=', 'lost')]
```

### Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `=` | Equals | `('state', '=', 'available')` |
| `!=` | Not equals | `('state', '!=', 'lost')` |
| `>` | Greater than | `('price', '>', 100)` |
| `>=` | Greater or equal | `('price', '>=', 100)` |
| `<` | Less than | `('page_count', '<', 200)` |
| `<=` | Less or equal | `('page_count', '<=', 200)` |
| `like` | Pattern match (case-sensitive) | `('name', 'like', 'Python')` |
| `ilike` | Pattern match (case-insensitive) | `('name', 'ilike', 'python')` |
| `=like` | SQL LIKE with wildcards | `('name', '=like', 'Python%')` |
| `=ilike` | Case-insensitive =like | `('name', '=ilike', 'python%')` |
| `in` | In list | `('state', 'in', ['available', 'borrowed'])` |
| `not in` | Not in list | `('state', 'not in', ['lost'])` |
| `child_of` | Hierarchical descendant | `('category_id', 'child_of', parent_id)` |
| `parent_of` | Hierarchical ancestor | `('category_id', 'parent_of', child_id)` |

### Traversing Relations

```python
# Through Many2one
[('book_id.author', '=', 'Tagore')]

# Through One2many/Many2many
[('borrowing_ids.state', '=', 'borrowed')]

# Multiple levels
[('book_id.category_ids.name', 'ilike', 'fiction')]
```

### Complex Domains

```python
# (A AND B) OR C
['|', '&', ('state', '=', 'available'), ('price', '<', 100), ('author', '=', 'Tagore')]

# A OR B OR C (left-associative)
['|', '|', ('state', '=', 'available'), ('state', '=', 'borrowed'), ('state', '=', 'lost')]

# NOT (A AND B) = (NOT A) OR (NOT B)
['!', '&', ('state', '=', 'lost'), ('active', '=', False)]
```

### Library Management Examples

```python
# library_management/models/book.py

@api.model
def search_by_isbn(self, isbn):
    """Search book by ISBN, handling different formats."""
    isbn_clean = isbn.replace('-', '').replace(' ', '')
    return self.search([
        '|',
        ('isbn', '=', isbn),
        ('isbn', '=', isbn_clean),
    ], limit=1)

@api.model
def get_available_books_count(self):
    """Count available books."""
    return self.search_count([('state', '=', 'available')])

def action_view_borrowings(self):
    """Open borrowing history for this book."""
    return {
        'name': 'Borrowing History',
        'type': 'ir.actions.act_window',
        'res_model': 'library.borrowing',
        'view_mode': 'list,form',
        'domain': [('book_id', '=', self.id)],  # Filter by current book
        'context': {'default_book_id': self.id},
    }


# library_management/models/borrowing.py

@api.constrains('book_id', 'state')
def _check_book_availability(self):
    """Ensure book isn't borrowed twice."""
    for borrowing in self:
        if borrowing.state == 'borrowed':
            # Domain to find other active borrowings
            other_borrowings = self.search([
                ('book_id', '=', borrowing.book_id.id),
                ('state', '=', 'borrowed'),
                ('id', '!=', borrowing.id),
            ])
            if other_borrowings:
                raise ValidationError(
                    f"Book '{borrowing.book_id.name}' is already borrowed!"
                )
```

### Domains in XML

```xml
<!-- Filter in action -->
<record id="action_available_books" model="ir.actions.act_window">
    <field name="name">Available Books</field>
    <field name="res_model">library.book</field>
    <field name="domain">[('state', '=', 'available')]</field>
</record>

<!-- Filter in search view -->
<filter name="filter_borrowed"
        string="Borrowed"
        domain="[('state', '=', 'borrowed')]"/>

<!-- Domain on Many2one field -->
<field name="book_id" domain="[('state', '=', 'available')]"/>
```

---

## 6. One2many & Many2many Fields

### One2many Fields

A One2many field represents a collection of records that reference this record through a Many2one field.

```python
# On the "one" side (library.book)
class LibraryBook(models.Model):
    _name = 'library.book'

    borrowing_ids = fields.One2many(
        comodel_name='library.borrowing',  # Related model
        inverse_name='book_id',            # Many2one field on related model
        string='Borrowings',
    )

# On the "many" side (library.borrowing)
class LibraryBorrowing(models.Model):
    _name = 'library.borrowing'

    book_id = fields.Many2one(
        comodel_name='library.book',
        string='Book',
        required=True,
        ondelete='cascade',
    )
```

**Key Points**:
- One2many has NO column in the database table
- It reads from the inverse Many2one field
- Changes flow through the Many2one side

### Many2many Fields

A Many2many field represents a symmetric relationship between two models.

```python
# On library.book
class LibraryBook(models.Model):
    _name = 'library.book'

    category_ids = fields.Many2many(
        comodel_name='library.category',
        relation='library_book_category_rel',   # Junction table name
        column1='book_id',                       # This model's column
        column2='category_id',                   # Other model's column
        string='Categories',
    )

# On library.category
class LibraryCategory(models.Model):
    _name = 'library.category'

    book_ids = fields.Many2many(
        comodel_name='library.book',
        relation='library_book_category_rel',   # Same junction table
        column1='category_id',                   # Reversed columns
        column2='book_id',
        string='Books',
    )
```

**Automatic Naming** (when relation is not specified):
```python
# Odoo auto-generates: model1_model2_rel
# For library.book + library.category:
#   library_book_library_category_rel
```

---

## 7. Special ORM Commands

When writing to One2many or Many2many fields, you must use special command tuples to specify what action to take.

### Command Syntax

```python
from odoo.fields import Command

# Modern syntax (recommended)
Command.create(values)     # Create new record
Command.update(id, values) # Update existing record
Command.delete(id)         # Delete record
Command.unlink(id)         # Remove link (keep record)
Command.link(id)           # Add link to existing
Command.clear()            # Remove all links
Command.set(ids)           # Replace with these IDs
```

### Command Reference Table

| Command | Tuple | Description |
|---------|-------|-------------|
| `Command.create(vals)` | `(0, 0, vals)` | Create new record and link it |
| `Command.update(id, vals)` | `(1, id, vals)` | Update existing linked record |
| `Command.delete(id)` | `(2, id, 0)` | Remove link AND delete record |
| `Command.unlink(id)` | `(3, id, 0)` | Remove link only (keep record) |
| `Command.link(id)` | `(4, id, 0)` | Link existing record |
| `Command.clear()` | `(5, 0, 0)` | Remove all links (keep records) |
| `Command.set(ids)` | `(6, 0, ids)` | Replace all links with these |

### Library Management Examples

```python
# library_management/models/book.py

def action_clear_categories(self):
    """Remove all category links from this book."""
    self.write({'category_ids': [Command.clear()]})

def action_add_fiction_category(self):
    """Add Fiction category to this book."""
    fiction = self.env.ref('library_management.library_category_fiction')
    self.write({'category_ids': [Command.link(fiction.id)]})

def action_set_categories(self, category_ids):
    """Replace categories with specified ones."""
    self.write({'category_ids': [Command.set(category_ids)]})

def action_remove_category(self, category_id):
    """Remove specific category (keep category record)."""
    self.write({'category_ids': [Command.unlink(category_id)]})
```

### Creating Records with Relations

```python
# Create book with new categories inline
book = self.env['library.book'].create({
    'name': 'New Book',
    'author': 'Author Name',
    'category_ids': [
        Command.create({'name': 'New Category 1'}),
        Command.create({'name': 'New Category 2'}),
    ],
})

# Create book with existing categories
book = self.env['library.book'].create({
    'name': 'Another Book',
    'category_ids': [
        Command.link(1),  # Link category ID 1
        Command.link(2),  # Link category ID 2
    ],
})

# Or using set command
book = self.env['library.book'].create({
    'name': 'Another Book',
    'category_ids': [Command.set([1, 2, 3])],
})
```

### One2many Commands

```python
# Create borrowing with inline member creation
borrowing = self.env['library.borrowing'].create({
    'book_id': book_id,
    'member_id': member_id,
})

# Update book's borrowings
book.write({
    'borrowing_ids': [
        Command.create({
            'member_id': 1,
            'borrow_date': '2024-01-15',
        }),
    ],
})

# Update existing borrowing through book
book.write({
    'borrowing_ids': [
        Command.update(borrowing_id, {'state': 'returned'}),
    ],
})
```

### Commands in XML Data Files

```xml
<!-- library_management/data/demo_data.xml -->

<record id="library_book_pather_panchali" model="library.book">
    <field name="name">Pather Panchali</field>
    <field name="author">Bibhutibhushan Bandyopadhyay</field>

    <!-- Command 6 (set): Replace categories with this list -->
    <field name="category_ids" eval="[(6, 0, [
        ref('library_category_fiction'),
        ref('library_category_classic'),
        ref('library_category_bengali')
    ])]"/>
</record>

<!-- Alternative: Link individual categories -->
<record id="library_book_example" model="library.book">
    <field name="name">Example Book</field>
    <field name="category_ids" eval="[
        (4, ref('library_category_fiction')),
        (4, ref('library_category_drama'))
    ]"/>
</record>

<!-- Create new related records inline -->
<record id="library_book_with_new_categories" model="library.book">
    <field name="name">Book With New Categories</field>
    <field name="category_ids" eval="[
        (0, 0, {'name': 'Inline Category 1'}),
        (0, 0, {'name': 'Inline Category 2'}),
    ]"/>
</record>
```

### Visual Command Reference

```
MANY2MANY / ONE2MANY COMMANDS
─────────────────────────────────────────────────────────────

Command.create({'name': 'X'})     (0, 0, values)
┌──────────┐                      ┌──────────┐
│  Book    │  ──creates──────────►│ Category │
│          │                      │ name='X' │
└──────────┘                      └──────────┘

Command.link(5)                   (4, 5, 0)
┌──────────┐                      ┌──────────┐
│  Book    │  ──links to────────►│ Cat ID=5 │
│          │                      │ (exists) │
└──────────┘                      └──────────┘

Command.unlink(5)                 (3, 5, 0)
┌──────────┐      ╳ link removed  ┌──────────┐
│  Book    │  ────────────────────│ Cat ID=5 │
│          │                      │ (kept)   │
└──────────┘                      └──────────┘

Command.delete(5)                 (2, 5, 0)
┌──────────┐      ╳ link removed
│  Book    │  ────────────────────  DELETED
│          │
└──────────┘

Command.clear()                   (5, 0, 0)
┌──────────┐      ╳ all links
│  Book    │  ────────────────────  All categories
│          │        removed        kept but unlinked
└──────────┘

Command.set([1,2,3])              (6, 0, [1,2,3])
┌──────────┐      ╳ old links     ┌────┐ ┌────┐ ┌────┐
│  Book    │  ────replaced────────│ 1  │ │ 2  │ │ 3  │
│          │      with new        └────┘ └────┘ └────┘
└──────────┘
```

---

## 8. Summary

### Quick Reference

| Topic | Key Concept |
|-------|-------------|
| **Models** | `_name`, `_description`, `_order`, fields |
| **Extension Inheritance** | `_inherit = 'model'` (no `_name`) |
| **Delegation Inheritance** | `_inherits = {'model': 'field_id'}` |
| **Mixin Inheritance** | `_inherit = ['mixin1', 'mixin2']` |
| **Recordsets** | Collection of records, iterate with `for` |
| **Environment** | `self.env['model']`, `self.env.user`, `self.env.context` |
| **Domains** | `[('field', 'operator', value)]` |
| **One2many** | `inverse_name` required, no DB column |
| **Many2many** | Junction table, symmetric relationship |
| **ORM Commands** | `Command.create/link/unlink/set/clear` |

### Files in Library Management

| File | Demonstrates |
|------|--------------|
| `category.py` | Basic model, SQL constraints, computed fields |
| `book.py` | Mixins, One2many, Many2many, ORM commands |
| `borrowing.py` | Many2one, constraints, state machine |
| `library_member.py` | Delegation inheritance, sequences |
| `res_partner.py` | Extension inheritance |
| `demo_data.xml` | XML data with Command syntax |

### Common Patterns

```python
# Search and filter
books = self.env['library.book'].search([
    ('state', '=', 'available'),
    ('category_ids.name', 'ilike', 'fiction'),
])

# Iterate and compute
for record in self:
    record.computed_field = len(record.related_ids)

# Modify relations
self.write({
    'category_ids': [
        Command.clear(),
        Command.link(category_id),
    ],
})

# Access through delegation
member.name  # Reads from partner_id.name

# Environment operations
self.env['ir.sequence'].next_by_code('sequence.code')
self.env.user.company_id
```

---

## Exercises

1. Create a `library.author` model with fields: name, birth_date, country, and a One2many to books
2. Add extension inheritance to `library.book` to add a `language` field
3. Write a method that uses domain to find all overdue borrowings
4. Create a button action that adds multiple categories using Command.set()
5. Implement a computed field that counts books by category using mapped()

---

*Week 7 - Odoo Models & ORM Fundamentals | Library Management Module*