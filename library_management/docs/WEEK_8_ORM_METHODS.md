# Week 8 Class 3: Odoo ORM Methods

## Learning Objectives

By the end of this session, you will understand:

- How to use Odoo shell for testing ORM methods
- CRUD operations: `create()`, `write()`, `unlink()`
- Search operations: `search()`, `search_count()`, `browse()`
- Data retrieval: `read()`, `read_group()`, `default_get()`
- Recordset operations: `mapped()`, `filtered()`, `filtered_domain()`
- Utility methods: `ensure_one()`, `name_get()`

---

## Table of Contents

1. [Starting Odoo Shell](#1-starting-odoo-shell)
2. [create() - Creating Records](#2-create---creating-records)
3. [write() - Updating Records](#3-write---updating-records)
4. [unlink() - Deleting Records](#4-unlink---deleting-records)
5. [default_get() - Default Values](#5-default_get---default-values)
6. [search() - Finding Records](#6-search---finding-records)
7. [search_count() - Counting Records](#7-search_count---counting-records)
8. [browse() - Loading by ID](#8-browse---loading-by-id)
9. [read() - Reading Field Values](#9-read---reading-field-values)
10. [read_group() - Grouped Aggregations](#10-read_group---grouped-aggregations)
11. [mapped() - Extracting Values](#11-mapped---extracting-values)
12. [filtered() - Filtering Recordsets](#12-filtered---filtering-recordsets)
13. [filtered_domain() - Domain-based Filtering](#13-filtered_domain---domain-based-filtering)
14. [ensure_one() - Single Record Validation](#14-ensure_one---single-record-validation)
15. [name_get() - Display Names](#15-name_get---display-names)
16. [Method Comparison Table](#16-method-comparison-table)
17. [Shell Practice Exercises](#17-shell-practice-exercises)

---

## 1. Starting Odoo Shell

### How to Start the Shell

```bash
# Navigate to your Odoo directory
cd E:\Odoo\Odoo19

# Start Odoo shell with your database
python odoo-bin shell -d YOUR_DATABASE_NAME --addons-path=addons,sqalogy
```

### Initial Setup in Shell

```python
# The shell provides 'env' object - the Odoo environment
# Access models using env['model.name']

# Get references to our library models
Book = env['library.book']
Borrowing = env['library.borrowing']
Member = env['library.member']
Category = env['library.category']

# Check if models are accessible
print(f"Book model: {Book}")
print(f"Total books: {Book.search_count([])}")
```

---

## 2. create() - Creating Records

### Definition

`create(vals)` or `create(vals_list)` creates one or more new records in the database.

### Syntax

```python
# Single record creation
record = Model.create({'field1': value1, 'field2': value2})

# Batch creation (Odoo 19 - preferred for performance)
records = Model.create([
    {'field1': value1},
    {'field2': value2},
])
```

### Shell Examples

```python
# =============================================================================
# CREATE - Single Record
# =============================================================================

# Create a new category
fiction = Category.create({
    'name': 'Science Fiction',
    'color': 4,
    'description': 'Books about futuristic worlds and technology'
})
print(f"Created category: {fiction.name} (ID: {fiction.id})")

# Create a new book
book = Book.create({
    'name': 'The Hitchhiker\'s Guide to the Galaxy',
    'author': 'Douglas Adams',
    'isbn': '978-0345391803',
    'publication_date': '1979-10-12',
    'state': 'available',
    'category_ids': [(4, fiction.id)]  # Link to fiction category
})
print(f"Created book: {book.name} by {book.author}")

# =============================================================================
# CREATE - Batch Records (Better Performance)
# =============================================================================

# Create multiple categories at once
categories = Category.create([
    {'name': 'Mystery', 'color': 1},
    {'name': 'Romance', 'color': 5},
    {'name': 'History', 'color': 3},
])
print(f"Created {len(categories)} categories: {categories.mapped('name')}")

# Create multiple books at once
books = Book.create([
    {
        'name': 'Murder on the Orient Express',
        'author': 'Agatha Christie',
        'isbn': '978-0062693662',
        'state': 'available'
    },
    {
        'name': 'Pride and Prejudice',
        'author': 'Jane Austen',
        'isbn': '978-0141439518',
        'state': 'available'
    },
])
print(f"Created {len(books)} books")

# Commit changes to database
env.cr.commit()
```

### Key Points

| Aspect | Details |
|--------|---------|
| Return Value | Returns the created recordset |
| Triggers | `@api.model_create_multi`, `@api.constrains`, computed fields |
| Performance | Batch create is faster than multiple single creates |
| Relational Fields | Use Command tuples `(0,0,vals)`, `(4,id)`, etc. |

---

## 3. write() - Updating Records

### Definition

`write(vals)` updates all records in the recordset with the given values.

### Syntax

```python
# Update single record
record.write({'field': new_value})

# Update multiple records at once
recordset.write({'field': new_value})

# Direct assignment (single record only)
record.field = new_value
```

### Shell Examples

```python
# =============================================================================
# WRITE - Single Record Update
# =============================================================================

# Find a book
book = Book.search([('name', 'ilike', 'hitchhiker')], limit=1)
print(f"Before: {book.name}, State: {book.state}")

# Update using write()
book.write({
    'state': 'borrowed',
    'notes': 'Popular book - reserved often'
})
print(f"After: State: {book.state}, Notes: {book.notes}")

# Direct assignment (simpler for single fields)
book.author = 'Douglas Noel Adams'
print(f"Updated author: {book.author}")

# =============================================================================
# WRITE - Multiple Records at Once
# =============================================================================

# Mark all available books as borrowed (just for demo - don't do this!)
available_books = Book.search([('state', '=', 'available')], limit=3)
print(f"Updating {len(available_books)} books...")

available_books.write({
    'notes': 'Batch updated via shell'
})

# Verify the update
for book in available_books:
    print(f"  - {book.name}: {book.notes}")

# =============================================================================
# WRITE - Relational Fields
# =============================================================================

# Add categories to a book using Command
from odoo import Command

book = Book.search([], limit=1)
mystery = Category.search([('name', '=', 'Mystery')], limit=1)

book.write({
    'category_ids': [
        Command.link(mystery.id),      # Add existing category
        Command.create({'name': 'Thriller', 'color': 2})  # Create and link
    ]
})
print(f"Book categories: {book.category_ids.mapped('name')}")

# Clear all categories
book.write({'category_ids': [Command.clear()]})
print(f"Categories cleared: {book.category_ids}")

# Set specific categories (replace all)
book.write({
    'category_ids': [Command.set(Category.search([]).ids[:2])]
})
print(f"Categories set: {book.category_ids.mapped('name')}")

env.cr.commit()
```

### Command Reference for Relational Fields

| Command | Tuple | Description |
|---------|-------|-------------|
| `Command.create(vals)` | `(0, 0, vals)` | Create new record and link |
| `Command.update(id, vals)` | `(1, id, vals)` | Update existing linked record |
| `Command.delete(id)` | `(2, id, 0)` | Remove link AND delete record |
| `Command.unlink(id)` | `(3, id, 0)` | Remove link, keep record |
| `Command.link(id)` | `(4, id, 0)` | Link existing record |
| `Command.clear()` | `(5, 0, 0)` | Remove all links |
| `Command.set(ids)` | `(6, 0, ids)` | Replace with specified IDs |

---

## 4. unlink() - Deleting Records

### Definition

`unlink()` permanently deletes all records in the recordset from the database.

### Syntax

```python
# Delete records
recordset.unlink()
```

### Shell Examples

```python
# =============================================================================
# UNLINK - Delete Records
# =============================================================================

# Create a test record to delete
test_category = Category.create({
    'name': 'Test Category - Delete Me',
    'color': 9
})
print(f"Created: {test_category.name} (ID: {test_category.id})")

# Store the ID for verification
test_id = test_category.id

# Delete the record
test_category.unlink()
print(f"Deleted!")

# Verify deletion
exists = Category.browse(test_id).exists()
print(f"Record exists? {bool(exists)}")  # Should be False

# =============================================================================
# UNLINK - Multiple Records
# =============================================================================

# Create multiple test records
test_cats = Category.create([
    {'name': 'Delete Test 1', 'color': 1},
    {'name': 'Delete Test 2', 'color': 2},
    {'name': 'Delete Test 3', 'color': 3},
])
print(f"Created {len(test_cats)} test categories")

# Delete all at once
test_cats.unlink()
print("All test categories deleted!")

# =============================================================================
# UNLINK - Deletion Protection (@api.ondelete)
# =============================================================================

# Try to delete a book that's currently borrowed (should fail!)
borrowed_book = Book.search([('state', '=', 'borrowed')], limit=1)
if borrowed_book:
    try:
        borrowed_book.unlink()
    except Exception as e:
        print(f"Cannot delete borrowed book: {e}")

env.cr.commit()
```

### Key Points

| Aspect | Details |
|--------|---------|
| Return Value | Returns `True` on success |
| Triggers | `@api.ondelete` hooks run BEFORE deletion |
| CASCADE | Records in related tables with `ondelete='cascade'` are also deleted |
| RESTRICT | Raises error if related records exist with `ondelete='restrict'` |
| Undo | **Cannot be undone** - records are permanently deleted |

---

## 5. default_get() - Default Values

### Definition

`default_get(fields_list)` returns a dictionary of default values for the specified fields.

### Syntax

```python
# Get defaults for specific fields
defaults = Model.default_get(['field1', 'field2'])

# Get all defaults
defaults = Model.default_get(Model._fields.keys())
```

### Shell Examples

```python
# =============================================================================
# DEFAULT_GET - Retrieve Default Values
# =============================================================================

# Get defaults for specific fields
book_defaults = Book.default_get(['state', 'active'])
print(f"Book defaults: {book_defaults}")
# Output: {'state': 'available', 'active': True}

# Get defaults for all fields
all_defaults = Book.default_get(list(Book._fields.keys()))
print("All book defaults:")
for field, value in all_defaults.items():
    if value is not None and value is not False:
        print(f"  {field}: {value}")

# =============================================================================
# DEFAULT_GET - With Context
# =============================================================================

# Context can affect defaults (e.g., default_book_id in views)
ctx = {'default_book_id': 1, 'default_state': 'borrowed'}
Borrowing_with_ctx = Borrowing.with_context(**ctx)

borrowing_defaults = Borrowing_with_ctx.default_get(['book_id', 'state', 'borrow_date'])
print(f"Borrowing defaults with context: {borrowing_defaults}")

# =============================================================================
# DEFAULT_GET - Useful for Form Initialization
# =============================================================================

# See what values a new member form would have
member_defaults = Member.default_get(['member_code', 'membership_date'])
print(f"Member defaults: {member_defaults}")
```

### Key Points

| Aspect | Details |
|--------|---------|
| Return Value | Dictionary of `{field_name: default_value}` |
| Sources | Field `default=`, `default_get()` override, context `default_*` keys |
| Usage | Forms call this to populate new record defaults |
| Override | Extend in model to add computed defaults |

---

## 6. search() - Finding Records

### Definition

`search(domain, offset=0, limit=None, order=None)` returns a recordset matching the domain criteria.

### Syntax

```python
# Basic search
records = Model.search([('field', 'operator', value)])

# With pagination and ordering
records = Model.search(
    domain=[('state', '=', 'active')],
    offset=0,
    limit=10,
    order='name asc'
)
```

### Shell Examples

```python
# =============================================================================
# SEARCH - Basic Queries
# =============================================================================

# Find all books
all_books = Book.search([])
print(f"Total books: {len(all_books)}")

# Find available books
available = Book.search([('state', '=', 'available')])
print(f"Available books: {len(available)}")

# Find borrowed books
borrowed = Book.search([('state', '=', 'borrowed')])
print(f"Borrowed books: {len(borrowed)}")

# =============================================================================
# SEARCH - Operators
# =============================================================================

# Case-insensitive search
adams_books = Book.search([('author', 'ilike', 'adams')])
print(f"Books by Adams: {adams_books.mapped('name')}")

# Not equal
non_fiction = Book.search([('state', '!=', 'borrowed')])

# In list
specific_states = Book.search([('state', 'in', ['available', 'borrowed'])])

# Like patterns
titles_with_the = Book.search([('name', 'like', 'The%')])  # Starts with "The"
titles_containing = Book.search([('name', 'ilike', '%guide%')])  # Contains "guide"

# Date comparisons
from datetime import date, timedelta
recent_date = date.today() - timedelta(days=365)
recent_borrowings = Borrowing.search([('borrow_date', '>=', recent_date)])
print(f"Borrowings in last year: {len(recent_borrowings)}")

# =============================================================================
# SEARCH - Complex Domains with AND/OR
# =============================================================================

# AND (implicit - list items)
# Find available books by Adams
available_adams = Book.search([
    ('state', '=', 'available'),
    ('author', 'ilike', 'adams')
])

# OR (explicit - using '|' operator)
# Find books that are available OR by Adams
available_or_adams = Book.search([
    '|',
    ('state', '=', 'available'),
    ('author', 'ilike', 'adams')
])
print(f"Available OR by Adams: {len(available_or_adams)}")

# Complex: (available AND adams) OR (borrowed AND christie)
complex_search = Book.search([
    '|',
    '&', ('state', '=', 'available'), ('author', 'ilike', 'adams'),
    '&', ('state', '=', 'borrowed'), ('author', 'ilike', 'christie')
])

# =============================================================================
# SEARCH - Pagination and Ordering
# =============================================================================

# First 5 books alphabetically
first_five = Book.search([], order='name asc', limit=5)
print("First 5 books:")
for book in first_five:
    print(f"  - {book.name}")

# Skip first 5, get next 5
next_five = Book.search([], order='name asc', limit=5, offset=5)
print("Next 5 books:")
for book in next_five:
    print(f"  - {book.name}")

# Order by multiple fields
ordered = Book.search([], order='author asc, name desc')

# =============================================================================
# SEARCH - Traversing Relations
# =============================================================================

# Find borrowings for books by specific author
borrowings_adams = Borrowing.search([('book_id.author', 'ilike', 'adams')])
print(f"Borrowings of Adams books: {len(borrowings_adams)}")

# Find books in specific category
mystery_books = Book.search([('category_ids.name', '=', 'Mystery')])
print(f"Mystery books: {len(mystery_books)}")

# Find members who borrowed specific book
book_borrowers = Borrowing.search([('book_id.name', 'ilike', 'hitchhiker')])
print(f"Hitchhiker borrowings: {book_borrowers.mapped('borrower_name')}")
```

### Domain Operators

| Operator | Description | Example |
|----------|-------------|---------|
| `=` | Equals | `('state', '=', 'available')` |
| `!=` | Not equals | `('state', '!=', 'borrowed')` |
| `>`, `<`, `>=`, `<=` | Comparison | `('date', '>=', '2024-01-01')` |
| `like` | Case-sensitive pattern | `('name', 'like', 'The%')` |
| `ilike` | Case-insensitive pattern | `('name', 'ilike', '%guide%')` |
| `in` | In list | `('state', 'in', ['a', 'b'])` |
| `not in` | Not in list | `('state', 'not in', ['x'])` |
| `child_of` | Hierarchy child | `('parent_id', 'child_of', id)` |
| `parent_of` | Hierarchy parent | `('id', 'parent_of', child_id)` |

---

## 7. search_count() - Counting Records

### Definition

`search_count(domain)` returns the number of records matching the domain, without loading them.

### Syntax

```python
count = Model.search_count([('field', 'operator', value)])
```

### Shell Examples

```python
# =============================================================================
# SEARCH_COUNT - Efficient Counting
# =============================================================================

# Count all books (faster than len(search([])))
total_books = Book.search_count([])
print(f"Total books: {total_books}")

# Count by state
available_count = Book.search_count([('state', '=', 'available')])
borrowed_count = Book.search_count([('state', '=', 'borrowed')])
print(f"Available: {available_count}, Borrowed: {borrowed_count}")

# Count active vs archived
active_count = Book.search_count([('active', '=', True)])
archived_count = Book.search_count([('active', '=', False)])
print(f"Active: {active_count}, Archived: {archived_count}")

# =============================================================================
# SEARCH_COUNT vs len(search()) Performance
# =============================================================================

import time

# search_count - just counts in SQL (fast!)
start = time.time()
count1 = Book.search_count([])
time1 = time.time() - start

# len(search) - loads all records then counts (slow!)
start = time.time()
count2 = len(Book.search([]))
time2 = time.time() - start

print(f"search_count: {count1} in {time1:.4f}s")
print(f"len(search): {count2} in {time2:.4f}s")

# =============================================================================
# SEARCH_COUNT - Dashboard Statistics
# =============================================================================

# Build dashboard data efficiently
stats = {
    'total_books': Book.search_count([]),
    'available_books': Book.search_count([('state', '=', 'available')]),
    'borrowed_books': Book.search_count([('state', '=', 'borrowed')]),
    'total_members': Member.search_count([]),
    'active_borrowings': Borrowing.search_count([('state', '=', 'borrowed')]),
    'total_borrowings': Borrowing.search_count([]),
    'total_categories': Category.search_count([]),
}
print("Library Dashboard:")
for key, value in stats.items():
    print(f"  {key}: {value}")
```

### Key Points

| Aspect | Details |
|--------|---------|
| Return Value | Integer count |
| Performance | Much faster than `len(search([]))` |
| SQL | Generates `SELECT COUNT(*)` query |
| Usage | Statistics, dashboards, pagination totals |

---

## 8. browse() - Loading by ID

### Definition

`browse(ids)` returns a recordset for the given database ID(s).

### Syntax

```python
# Single ID
record = Model.browse(id)

# Multiple IDs
records = Model.browse([id1, id2, id3])

# Empty recordset
empty = Model.browse([])
```

### Shell Examples

```python
# =============================================================================
# BROWSE - Load Records by ID
# =============================================================================

# Get first book's ID
first_book_id = Book.search([], limit=1).id
print(f"First book ID: {first_book_id}")

# Browse by ID
book = Book.browse(first_book_id)
print(f"Browsed book: {book.name} by {book.author}")

# =============================================================================
# BROWSE - Multiple IDs
# =============================================================================

# Get some IDs
all_book_ids = Book.search([], limit=5).ids
print(f"Book IDs: {all_book_ids}")

# Browse multiple
books = Book.browse(all_book_ids)
print(f"Browsed {len(books)} books:")
for b in books:
    print(f"  - {b.name}")

# =============================================================================
# BROWSE - Empty and Non-existent IDs
# =============================================================================

# Empty recordset
empty = Book.browse([])
print(f"Empty recordset: {empty}, length: {len(empty)}")

# Non-existent ID (returns record but exists() is False)
fake = Book.browse(999999)
print(f"Fake record: {fake}")
print(f"Exists? {bool(fake.exists())}")

# =============================================================================
# BROWSE vs SEARCH
# =============================================================================

# When to use browse():
# - You already have the ID (from context, URL, etc.)
# - Loading related records by ID

# When to use search():
# - Finding records by criteria
# - You don't know the ID

# Example: Get book from borrowing record
borrowing = Borrowing.search([], limit=1)
if borrowing:
    # BAD: search for the same book (unnecessary query)
    # book = Book.search([('id', '=', borrowing.book_id.id)])

    # GOOD: browse by ID (or just use borrowing.book_id directly!)
    book = Book.browse(borrowing.book_id.id)
    print(f"Borrowing for: {book.name}")
```

### Key Points

| Aspect | Details |
|--------|---------|
| Return Value | Recordset (may be empty) |
| Non-existent IDs | Returns record object but `exists()` returns False |
| Performance | No SQL query until fields are accessed (lazy loading) |
| Usage | When you already have the ID |

---

## 9. read() - Reading Field Values

### Definition

`read(fields)` returns a list of dictionaries containing the requested field values.

### Syntax

```python
# Read specific fields
data = recordset.read(['field1', 'field2'])

# Read all fields
data = recordset.read()
```

### Shell Examples

```python
# =============================================================================
# READ - Basic Usage
# =============================================================================

# Find some books
books = Book.search([], limit=3)

# Read specific fields
data = books.read(['name', 'author', 'state'])
print("Book data:")
for item in data:
    print(f"  ID {item['id']}: {item['name']} by {item['author']} ({item['state']})")

# =============================================================================
# READ - All Fields
# =============================================================================

# Read all fields (can be expensive!)
book = Book.search([], limit=1)
all_data = book.read()
print(f"All fields for {book.name}:")
for key, value in all_data[0].items():
    print(f"  {key}: {value}")

# =============================================================================
# READ - Relational Fields
# =============================================================================

# Read with relational field
book = Book.search([('category_ids', '!=', False)], limit=1)
if book:
    data = book.read(['name', 'category_ids'])
    print(f"Book categories: {data}")
    # Note: category_ids returns list of IDs

# =============================================================================
# READ vs Direct Access
# =============================================================================

book = Book.search([], limit=1)

# Direct access (Pythonic, lazy loading)
print(f"Direct: {book.name} by {book.author}")

# read() returns dictionaries (useful for JSON export, reports)
data = book.read(['name', 'author'])[0]
print(f"Read: {data['name']} by {data['author']}")

# When to use read():
# - Exporting data to JSON/API
# - Building reports
# - Need dictionary format
# - Specifying exact fields for performance

# When to use direct access:
# - Normal Python code
# - Simpler and more readable
# - Triggering computed fields
```

### Key Points

| Aspect | Details |
|--------|---------|
| Return Value | List of dictionaries `[{field: value}, ...]` |
| Many2one | Returns `(id, name)` tuple or `False` |
| One2many/Many2many | Returns list of IDs |
| Performance | Can specify exact fields to reduce data transfer |

---

## 10. read_group() - Grouped Aggregations

### Definition

`read_group(domain, fields, groupby, offset=0, limit=None, orderby=False, lazy=True)` performs grouped aggregations like SQL GROUP BY.

### Syntax

```python
result = Model.read_group(
    domain=[],                    # Filter records
    fields=['field1', 'field2:sum'],  # Fields to read/aggregate
    groupby=['group_field'],      # Group by this field
    offset=0,                     # Skip records
    limit=None,                   # Limit groups
    orderby='field desc',         # Order results
    lazy=True                     # Lazy load sub-groups
)
```

### Shell Examples

```python
# =============================================================================
# READ_GROUP - Basic Grouping
# =============================================================================

# Count books by state
by_state = Book.read_group(
    domain=[],
    fields=['state'],
    groupby=['state']
)
print("Books by state:")
for group in by_state:
    print(f"  {group['state']}: {group['state_count']} books")

# =============================================================================
# READ_GROUP - Aggregations
# =============================================================================

# Count borrowings by state with days borrowed sum
by_state = Borrowing.read_group(
    domain=[],
    fields=['state', 'days_borrowed:sum'],
    groupby=['state']
)
print("Borrowings by state:")
for group in by_state:
    print(f"  {group['state']}: {group['state_count']} records, {group['days_borrowed']} total days")

# =============================================================================
# READ_GROUP - Multiple Group Levels
# =============================================================================

# Group borrowings by book and then by state
by_book_state = Borrowing.read_group(
    domain=[],
    fields=['book_id', 'state'],
    groupby=['book_id', 'state'],
    lazy=False  # Load all levels at once
)
print("Borrowings by book and state:")
for group in by_book_state:
    book_name = group['book_id'][1] if group['book_id'] else 'Unknown'
    print(f"  {book_name} - {group['state']}: {group['__count']} records")

# =============================================================================
# READ_GROUP - Date Grouping
# =============================================================================

# Group borrowings by month
by_month = Borrowing.read_group(
    domain=[],
    fields=['borrow_date'],
    groupby=['borrow_date:month']
)
print("Borrowings by month:")
for group in by_month:
    print(f"  {group['borrow_date:month']}: {group['borrow_date_count']} borrowings")

# Group by year
by_year = Borrowing.read_group(
    domain=[],
    fields=['borrow_date'],
    groupby=['borrow_date:year']
)

# =============================================================================
# READ_GROUP - With Domain Filter
# =============================================================================

# Only count overdue borrowings by member
overdue_by_member = Borrowing.read_group(
    domain=[('is_overdue', '=', True)],
    fields=['member_id'],
    groupby=['member_id']
)
print("Overdue borrowings by member:")
for group in overdue_by_member:
    member = group['member_id'][1] if group['member_id'] else 'Walk-in'
    print(f"  {member}: {group['member_id_count']} overdue")

# =============================================================================
# READ_GROUP - Statistics Dashboard
# =============================================================================

# Build comprehensive statistics
print("\n=== LIBRARY STATISTICS ===")

# Books by state
print("\nBooks by Status:")
for g in Book.read_group([], ['state'], ['state']):
    print(f"  {g['state']}: {g['state_count']}")

# Categories with book counts
print("\nCategories with Most Books:")
cat_stats = Category.read_group(
    domain=[],
    fields=['name', 'book_count:sum'],
    groupby=['name'],
    orderby='book_count desc',
    limit=5
)
for g in cat_stats:
    print(f"  {g['name']}: {g.get('book_count', 0)} books")
```

### Aggregation Functions

| Function | Example | Description |
|----------|---------|-------------|
| `count` | `field_name_count` (automatic) | Count records |
| `sum` | `'amount:sum'` | Sum values |
| `avg` | `'price:avg'` | Average value |
| `min` | `'date:min'` | Minimum value |
| `max` | `'date:max'` | Maximum value |

### Date Grouping Options

| Groupby | Description |
|---------|-------------|
| `'date_field:day'` | Group by day |
| `'date_field:week'` | Group by week |
| `'date_field:month'` | Group by month |
| `'date_field:quarter'` | Group by quarter |
| `'date_field:year'` | Group by year |

---

## 11. mapped() - Extracting Values

### Definition

`mapped(field_name)` extracts field values from all records in the recordset.

### Syntax

```python
# Get list of field values
values = recordset.mapped('field_name')

# Traverse relations
values = recordset.mapped('relation_field.nested_field')

# Apply function
values = recordset.mapped(lambda r: r.field1 + r.field2)
```

### Shell Examples

```python
# =============================================================================
# MAPPED - Extract Field Values
# =============================================================================

# Get all book titles
books = Book.search([], limit=10)
titles = books.mapped('name')
print(f"Book titles: {titles}")

# Get all authors (unique values with set)
authors = list(set(books.mapped('author')))
print(f"Authors: {authors}")

# Get all book IDs
ids = books.mapped('id')
print(f"IDs: {ids}")
# Note: Same as books.ids

# =============================================================================
# MAPPED - Relational Fields
# =============================================================================

# Get borrowers from borrowings
borrowings = Borrowing.search([], limit=5)
borrower_names = borrowings.mapped('borrower_name')
print(f"Borrowers: {borrower_names}")

# Get book names from borrowings (traversing relation)
book_titles = borrowings.mapped('book_id.name')
print(f"Borrowed books: {book_titles}")

# Get all authors of borrowed books
borrowed_authors = borrowings.mapped('book_id.author')
print(f"Authors of borrowed books: {borrowed_authors}")

# =============================================================================
# MAPPED - One2many/Many2many (Flattening)
# =============================================================================

# Get all borrowings for multiple books (flattens!)
books = Book.search([], limit=3)
all_borrowings = books.mapped('borrowing_ids')
print(f"All borrowings for {len(books)} books: {len(all_borrowings)} records")

# Get all categories for multiple books
all_categories = books.mapped('category_ids')
print(f"All categories: {all_categories.mapped('name')}")

# =============================================================================
# MAPPED - Lambda Functions
# =============================================================================

# Calculate custom values
books = Book.search([], limit=5)

# Create display strings
display_names = books.mapped(lambda b: f"{b.name} by {b.author}")
print("Display names:")
for name in display_names:
    print(f"  - {name}")

# Calculate borrowing stats
borrowings = Borrowing.search([('state', '=', 'borrowed')])
overdue_flags = borrowings.mapped(lambda b: 'OVERDUE' if b.is_overdue else 'OK')
print(f"Overdue status: {overdue_flags}")

# =============================================================================
# MAPPED - Nested Traversal
# =============================================================================

# Get category names from borrowings (3 levels deep!)
borrowings = Borrowing.search([], limit=5)
# borrowing -> book_id -> category_ids -> name
category_names = borrowings.mapped('book_id.category_ids.name')
print(f"Categories of borrowed books: {category_names}")
```

### Key Points

| Aspect | Details |
|--------|---------|
| Return Value | List (or recordset for relational fields) |
| Empty Records | Skipped (no None values) |
| Traversal | Dot notation for nested fields |
| Lambda | Custom transformations supported |

---

## 12. filtered() - Filtering Recordsets

### Definition

`filtered(func)` returns a new recordset containing only records where the function returns True.

### Syntax

```python
# Filter with lambda
filtered_records = recordset.filtered(lambda r: r.field == value)

# Filter by field name (shortcut for boolean fields)
active_records = recordset.filtered('active')
```

### Shell Examples

```python
# =============================================================================
# FILTERED - Basic Filtering
# =============================================================================

# Get all books
books = Book.search([])
print(f"Total books: {len(books)}")

# Filter available books (in-memory, no SQL)
available = books.filtered(lambda b: b.state == 'available')
print(f"Available: {len(available)}")

# Filter borrowed books
borrowed = books.filtered(lambda b: b.state == 'borrowed')
print(f"Borrowed: {len(borrowed)}")

# =============================================================================
# FILTERED - Boolean Shortcut
# =============================================================================

# Filter by boolean field (shortcut)
active_books = books.filtered('active')
print(f"Active books: {len(active_books)}")

# Equivalent to:
active_books2 = books.filtered(lambda b: b.active)
print(f"Active (lambda): {len(active_books2)}")

# =============================================================================
# FILTERED - Complex Conditions
# =============================================================================

# Multiple conditions
adams_available = books.filtered(
    lambda b: b.author and 'adams' in b.author.lower() and b.state == 'available'
)
print(f"Available Adams books: {len(adams_available)}")

# Filter by related field
borrowings = Borrowing.search([])
overdue_borrowings = borrowings.filtered(lambda b: b.is_overdue)
print(f"Overdue borrowings: {len(overdue_borrowings)}")

# Filter borrowings by book author
adams_borrowings = borrowings.filtered(
    lambda b: b.book_id and b.book_id.author and 'adams' in b.book_id.author.lower()
)
print(f"Borrowings of Adams books: {len(adams_borrowings)}")

# =============================================================================
# FILTERED - With One2many
# =============================================================================

# Books with borrowing history
books_with_history = books.filtered(lambda b: b.borrowing_ids)
print(f"Books with borrowing history: {len(books_with_history)}")

# Books with many categories
multi_category = books.filtered(lambda b: len(b.category_ids) > 1)
print(f"Books with multiple categories: {len(multi_category)}")

# =============================================================================
# FILTERED - Chaining
# =============================================================================

# Chain multiple filters
result = books \
    .filtered(lambda b: b.state == 'available') \
    .filtered(lambda b: b.borrowing_count > 0) \
    .filtered('active')
print(f"Available, previously borrowed, active: {len(result)}")

# =============================================================================
# FILTERED vs SEARCH
# =============================================================================

# FILTERED: Works on already-loaded recordset (in-memory)
# Best when: Data already loaded, complex Python conditions

# SEARCH: SQL query to database
# Best when: Need to fetch filtered data from scratch

# Example comparison:
all_books = Book.search([])  # SQL: SELECT * FROM library_book

# filtered() - In memory, no SQL
available1 = all_books.filtered(lambda b: b.state == 'available')

# search() - SQL: SELECT * FROM library_book WHERE state = 'available'
available2 = Book.search([('state', '=', 'available')])

# Both give same result, but:
# - Use search() when you haven't loaded records yet
# - Use filtered() when you have records and need Python logic
```

### Key Points

| Aspect | Details |
|--------|---------|
| Return Value | New recordset (filtered subset) |
| Execution | In-memory (no SQL query) |
| Performance | Fast if data already loaded, otherwise use search() |
| Chaining | Can chain multiple filtered() calls |

---

## 13. filtered_domain() - Domain-based Filtering

### Definition

`filtered_domain(domain)` filters the recordset using a domain expression, evaluated in-memory.

### Syntax

```python
# Filter using domain
filtered_records = recordset.filtered_domain([('field', 'operator', value)])
```

### Shell Examples

```python
# =============================================================================
# FILTERED_DOMAIN - Domain-style In-Memory Filtering
# =============================================================================

# Get all books
books = Book.search([])
print(f"Total books: {len(books)}")

# Filter using domain syntax
available = books.filtered_domain([('state', '=', 'available')])
print(f"Available: {len(available)}")

# Multiple conditions (AND)
adams_available = books.filtered_domain([
    ('state', '=', 'available'),
    ('author', 'ilike', 'adams')
])
print(f"Available Adams books: {len(adams_available)}")

# =============================================================================
# FILTERED_DOMAIN - Complex Domains
# =============================================================================

# OR condition
available_or_borrowed = books.filtered_domain([
    '|',
    ('state', '=', 'available'),
    ('state', '=', 'borrowed')
])

# Comparison operators
borrowings = Borrowing.search([])
long_borrowings = borrowings.filtered_domain([
    ('days_borrowed', '>', 14)
])
print(f"Borrowings over 14 days: {len(long_borrowings)}")

# =============================================================================
# FILTERED_DOMAIN vs FILTERED
# =============================================================================

# filtered_domain: Uses domain syntax (like search())
# filtered: Uses Python lambda

# Same result, different syntax:
available1 = books.filtered_domain([('state', '=', 'available')])
available2 = books.filtered(lambda b: b.state == 'available')
print(f"Same result? {available1 == available2}")

# Use filtered_domain when:
# - Domain is already available (from view, user input)
# - Prefer declarative style
# - Conditions are simple equality/comparison

# Use filtered when:
# - Complex Python logic needed
# - Need to access methods
# - Conditions can't be expressed as domain

# =============================================================================
# FILTERED_DOMAIN - Dynamic Domains
# =============================================================================

# Useful when domain comes from configuration or user input
user_filter = [('state', '=', 'borrowed')]  # Could come from UI
result = books.filtered_domain(user_filter)
print(f"User filter result: {len(result)}")

# Apply saved search filters
saved_domain = [
    ('active', '=', True),
    ('borrowing_count', '>', 0)
]
popular_active = books.filtered_domain(saved_domain)
print(f"Popular active books: {len(popular_active)}")
```

### Key Points

| Aspect | Details |
|--------|---------|
| Return Value | New recordset (filtered subset) |
| Execution | In-memory using domain expression |
| Advantage | Use when domain is already constructed |
| Operators | Supports standard domain operators |

---

## 14. ensure_one() - Single Record Validation

### Definition

`ensure_one()` verifies the recordset contains exactly one record. Raises an error otherwise.

### Syntax

```python
record.ensure_one()  # Raises ValueError if not exactly 1 record
```

### Shell Examples

```python
# =============================================================================
# ENSURE_ONE - Validate Single Record
# =============================================================================

# Get exactly one book
book = Book.search([], limit=1)
book.ensure_one()  # OK - exactly one record
print(f"Single book: {book.name}")

# =============================================================================
# ENSURE_ONE - Error Cases
# =============================================================================

# Empty recordset - raises error
empty = Book.browse([])
try:
    empty.ensure_one()
except ValueError as e:
    print(f"Empty error: {e}")

# Multiple records - raises error
multiple = Book.search([], limit=3)
try:
    multiple.ensure_one()
except ValueError as e:
    print(f"Multiple error: {e}")

# =============================================================================
# ENSURE_ONE - Practical Usage
# =============================================================================

def get_book_details(book_id):
    """Example function that requires exactly one book."""
    book = Book.browse(book_id)
    book.ensure_one()  # Validates before proceeding
    return {
        'name': book.name,
        'author': book.author,
        'state': book.state,
    }

# Test with valid ID
first_id = Book.search([], limit=1).id
details = get_book_details(first_id)
print(f"Details: {details}")

# =============================================================================
# ENSURE_ONE - In Method Definitions
# =============================================================================

# Common pattern in model methods:
# def action_something(self):
#     self.ensure_one()  # Ensure called on single record
#     # ... do something with self ...

# Example from library_management/models/book.py:
book = Book.search([], limit=1)
book.ensure_one()
result = book.action_view_borrowings()
print(f"Action returned: {result['name']}")
```

### Key Points

| Aspect | Details |
|--------|---------|
| Return Value | None (or raises ValueError) |
| Empty | Raises `ValueError: Expected singleton...` |
| Multiple | Raises `ValueError: Expected singleton...` |
| Usage | Button actions, methods expecting single record |

---

## 15. name_get() - Display Names

### Definition

`name_get()` returns a list of `(id, display_name)` tuples for the records in the recordset.

### Syntax

```python
# Get display names
names = recordset.name_get()
# Returns: [(id1, 'Name 1'), (id2, 'Name 2'), ...]
```

### Shell Examples

```python
# =============================================================================
# NAME_GET - Basic Usage
# =============================================================================

# Get display names for books
books = Book.search([], limit=5)
names = books.name_get()
print("Book names:")
for id, name in names:
    print(f"  ID {id}: {name}")

# =============================================================================
# NAME_GET - Different Models
# =============================================================================

# Categories
categories = Category.search([], limit=5)
cat_names = categories.name_get()
print("\nCategory names:")
for id, name in cat_names:
    print(f"  ID {id}: {name}")

# Borrowings (often have custom display name)
borrowings = Borrowing.search([], limit=5)
borrow_names = borrowings.name_get()
print("\nBorrowing references:")
for id, name in borrow_names:
    print(f"  ID {id}: {name}")

# =============================================================================
# NAME_GET vs display_name
# =============================================================================

book = Book.search([], limit=1)

# name_get() returns list of tuples
name_get_result = book.name_get()
print(f"name_get(): {name_get_result}")

# display_name is a computed field (simpler to use)
print(f"display_name: {book.display_name}")

# For single record, display_name is easier
# For multiple records, name_get() is efficient

# =============================================================================
# NAME_GET - Custom Display Names
# =============================================================================

# Models can override name_get() for custom display
# Example: Member might show "Code - Name"

members = Member.search([], limit=3)
member_names = members.name_get()
print("\nMember display names:")
for id, name in member_names:
    print(f"  ID {id}: {name}")

# Compare with raw name field
for member in members:
    print(f"  {member.member_code}: {member.name}")
```

### Key Points

| Aspect | Details |
|--------|---------|
| Return Value | List of `(id, name)` tuples |
| Default | Returns `(id, record.name)` or `(id, record.display_name)` |
| Override | Models can override for custom display |
| Usage | Dropdowns, references, Many2one displays |

---

## 16. Method Comparison Table

| Method | Input | Output | Purpose |
|--------|-------|--------|---------|
| `create(vals)` | Dict or list | Recordset | Create new records |
| `write(vals)` | Dict | Boolean | Update existing records |
| `unlink()` | - | Boolean | Delete records |
| `default_get(fields)` | Field list | Dict | Get default values |
| `search(domain)` | Domain | Recordset | Find records by criteria |
| `search_count(domain)` | Domain | Integer | Count matching records |
| `browse(ids)` | ID(s) | Recordset | Load records by ID |
| `read(fields)` | Field list | List[Dict] | Get field values as dicts |
| `read_group(...)` | Domain, fields, groupby | List[Dict] | Grouped aggregations |
| `mapped(func)` | Field name or lambda | List | Extract/transform values |
| `filtered(func)` | Lambda or field | Recordset | Filter in-memory |
| `filtered_domain(domain)` | Domain | Recordset | Filter using domain |
| `ensure_one()` | - | None | Validate single record |
| `name_get()` | - | List[Tuple] | Get display names |

---

## 17. Shell Practice Exercises

### Exercise 1: CRUD Operations

```python
# 1. Create a new category called "Programming"
# 2. Create a new book in that category
# 3. Update the book's state to "borrowed"
# 4. Delete the category (should work if no books linked)

# Your solution:
# ...
```

### Exercise 2: Search and Statistics

```python
# 1. Count total books, available books, borrowed books
# 2. Find all books by a specific author
# 3. Find all overdue borrowings
# 4. Get the top 5 most borrowed books

# Your solution:
# ...
```

### Exercise 3: Read and Group

```python
# 1. Read name, author, state for all books
# 2. Group borrowings by month
# 3. Group books by state and count each
# 4. Get average days borrowed per member

# Your solution:
# ...
```

### Exercise 4: Recordset Operations

```python
# 1. Get all books, then filter only available ones
# 2. Map all book titles to a list
# 3. Get all category names from a book's categories
# 4. Chain filtered() to find available books with borrowing history

# Your solution:
# ...
```

### Exercise 5: Complete Workflow

```python
# Simulate a complete borrowing workflow:
# 1. Create a new member
# 2. Find an available book
# 3. Create a borrowing record
# 4. Verify the book state changed to "borrowed"
# 5. Return the book (update borrowing state)
# 6. Verify the book is available again

# Your solution:
# ...
```

---

## Solutions to Exercises

<details>
<summary>Click to reveal solutions</summary>

### Exercise 1 Solution

```python
# Create category
prog_cat = Category.create({'name': 'Programming', 'color': 6})
print(f"Created: {prog_cat.name}")

# Create book with category
from odoo import Command
book = Book.create({
    'name': 'Clean Code',
    'author': 'Robert C. Martin',
    'isbn': '978-0132350884',
    'state': 'available',
    'category_ids': [Command.link(prog_cat.id)]
})
print(f"Created: {book.name}")

# Update book
book.write({'state': 'borrowed'})
print(f"Updated state: {book.state}")

# Remove category link first, then delete
book.write({'category_ids': [Command.clear()]})
prog_cat.unlink()
print("Category deleted")

env.cr.commit()
```

### Exercise 2 Solution

```python
# Count books
total = Book.search_count([])
available = Book.search_count([('state', '=', 'available')])
borrowed = Book.search_count([('state', '=', 'borrowed')])
print(f"Total: {total}, Available: {available}, Borrowed: {borrowed}")

# Find by author
author_books = Book.search([('author', 'ilike', 'adams')])
print(f"Adams books: {author_books.mapped('name')}")

# Overdue borrowings
overdue = Borrowing.search([('is_overdue', '=', True)])
print(f"Overdue: {len(overdue)}")

# Top borrowed
popular = Book.search([], order='borrowing_count desc', limit=5)
for b in popular:
    print(f"  {b.name}: {b.borrowing_count} times")
```

### Exercise 3 Solution

```python
# Read specific fields
data = Book.search([]).read(['name', 'author', 'state'])
for d in data[:5]:
    print(f"  {d['name']} - {d['state']}")

# Group by month
monthly = Borrowing.read_group([], ['borrow_date'], ['borrow_date:month'])
for g in monthly:
    print(f"  {g['borrow_date:month']}: {g['borrow_date_count']}")

# Group by state
by_state = Book.read_group([], ['state'], ['state'])
for g in by_state:
    print(f"  {g['state']}: {g['state_count']}")
```

### Exercise 4 Solution

```python
# Filter available
books = Book.search([])
available = books.filtered(lambda b: b.state == 'available')
print(f"Available: {len(available)}")

# Map titles
titles = books.mapped('name')
print(f"Titles: {titles[:5]}")

# Categories from book
book = Book.search([('category_ids', '!=', False)], limit=1)
if book:
    cats = book.category_ids.mapped('name')
    print(f"Categories: {cats}")

# Chain filters
with_history = books \
    .filtered(lambda b: b.state == 'available') \
    .filtered(lambda b: b.borrowing_ids)
print(f"Available with history: {len(with_history)}")
```

### Exercise 5 Solution

```python
# Create member
member = Member.create({
    'name': 'John Test',
    'email': 'john@test.com',
})
print(f"Created member: {member.name} ({member.member_code})")

# Find available book
book = Book.search([('state', '=', 'available')], limit=1)
if book:
    print(f"Found book: {book.name}")

    # Create borrowing
    borrowing = Borrowing.create({
        'book_id': book.id,
        'member_id': member.id,
        'borrower_name': member.name,
        'state': 'borrowed',
    })
    print(f"Created borrowing: {borrowing.name}")
    print(f"Book state: {book.state}")  # Should be 'borrowed'

    # Return book
    borrowing.action_return_book()
    print(f"Book returned!")
    print(f"Book state: {book.state}")  # Should be 'available'

env.cr.commit()
```

</details>

---

## Quick Reference Card

```python
# =============================================================================
# ODOO ORM METHODS - QUICK REFERENCE
# =============================================================================

# ACCESS MODEL
Book = env['library.book']

# CREATE
record = Model.create({'field': value})
records = Model.create([{...}, {...}])

# READ
data = records.read(['field1', 'field2'])
defaults = Model.default_get(['field1'])

# UPDATE
record.write({'field': value})
record.field = value  # single field

# DELETE
record.unlink()

# SEARCH
records = Model.search([('field', '=', value)])
count = Model.search_count([('field', '=', value)])
record = Model.browse(id)

# AGGREGATE
groups = Model.read_group([], ['field:sum'], ['group_field'])

# RECORDSET OPS
values = records.mapped('field')
filtered = records.filtered(lambda r: r.field == value)
filtered = records.filtered_domain([('field', '=', value)])

# VALIDATION
record.ensure_one()
names = records.name_get()

# COMMIT (in shell only!)
env.cr.commit()
# =============================================================================
```
