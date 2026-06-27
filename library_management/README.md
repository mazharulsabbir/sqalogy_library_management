# Library Management System

A comprehensive Odoo 19 module for managing library book inventory and borrowing operations.

## Features

### 1. Book Management
- **Book Model** (`library.book`) with fields:
  - Title (name)
  - Author
  - Publication Date
  - ISBN (with validation for 10 or 13 digits)
  - Status (Available/Borrowed)
  - Borrowing count (computed)
  - Current borrowing record (computed)
  - Categories (Many2many tags via `library.category`)
  - Borrowing history (One2many)

- **Views:**
  - Kanban view for visual book browsing
  - Tree/List view for quick scanning
  - Detailed form view with chatter integration
  - Advanced search with filters and grouping

### 2. Borrowing System
- **Borrowing Model** (`library.borrowing`) with fields:
  - Unique reference number (auto-generated: BRW00001, BRW00002, etc.)
  - Borrower information (name, email, phone)
  - Book (many2one relationship)
  - Borrow date
  - Expected return date
  - Actual return date
  - Status (Borrowed/Returned)
  - Overdue indicator (computed)
  - Days borrowed (computed)

- **Smart Features:**
  - Automatic book availability update on borrow/return
  - Validation to prevent borrowing already-borrowed books
  - Date validation (return date must be after borrow date)
  - Overdue detection and visual alerts
  - "Borrow Again" action for repeat borrowers

### 3. Members & Categories (Week 7: Inheritance & Relations)
- **Member Model** (`library.member`) using **delegation inheritance**
  (`_inherits = {'res.partner': 'partner_id'}`) — a member *is a* contact and
  exposes `name`/`email`/`phone` straight from `res.partner`.
- **res.partner extension** (`_inherit = 'res.partner'`) adds `is_library_member`
  and a `member_ids` One2many — an example of **extension inheritance**.
- **Category Model** (`library.category`) used as **Many2many** tags on books.
- Borrowings can be linked to a member via the `member_id` Many2one, the inverse
  of the member's `borrowing_ids` One2many.

### 4. Availability Management
- Automatic status updates when books are borrowed or returned
- Real-time availability tracking
- Validation to ensure data integrity
- Manual override capability for librarians

### 5. User Interface
- Modern, intuitive Odoo interface
- Color-coded status indicators
- Smart buttons for quick navigation
- Kanban boards for visual management
- Chatter integration for activity tracking
- Advanced filtering and search capabilities

### 6. Access Control
Three-tier security model:

#### Member
- View all books
- View own borrowings only
- Read-only access

#### Librarian
- Full access to books (create, read, update, delete)
- Full access to borrowings (create, read, update, delete)
- Manage all library operations

#### Manager
- All librarian permissions
- Access to configuration settings
- Full administrative control

### 7. Reporting

#### Book Inventory Report
- Current inventory status
- Availability breakdown
- Pivot table analysis by status and author
- Graph visualization
- PDF export with summary statistics

#### Borrowing History Report
- Complete borrowing records
- Overdue highlighting
- Trend analysis by time period
- Pivot table analysis by book and status
- Graph visualization
- PDF export with detailed statistics

## Installation

1. Copy the `library_management` folder to your Odoo addons directory:
   ```
   E:\Odoo\Odoo19\class-addons\library_management\
   ```

2. Update your `odoo.conf` to include the addons path (if not already included):
   ```
   addons_path = ...,class-addons
   ```

3. Restart the Odoo server:
   ```bash
   python odoo-bin -c odoo.conf
   ```

4. Go to Apps menu, update the apps list, and search for "Library Management"

5. Click Install

## Configuration

1. After installation, go to Settings > Users & Companies > Groups
2. Assign users to appropriate library groups:
   - Library / Member
   - Library / Librarian
   - Library / Manager

## Usage

### Adding Books
1. Go to Library > Operations > Books
2. Click "Create"
3. Fill in book details (Title, Author, ISBN, etc.)
4. Save

### Recording a Borrowing
1. Go to Library > Operations > Borrowings
2. Click "Create"
3. Select the book (only available books are shown)
4. Enter borrower information
5. Set borrow date and expected return date
6. Save (book status automatically changes to "Borrowed")

### Returning a Book
1. Open the borrowing record
2. Click "Return Book" button
3. Return date is automatically set to today
4. Book status automatically changes back to "Available"

### Viewing Reports
1. Go to Library > Reporting
2. Choose either:
   - Book Inventory (for current stock status)
   - Borrowing History (for borrowing patterns)
3. Use pivot tables and graphs for analysis
4. Print PDF reports as needed

## Module Structure

```
library_management/
├── __init__.py
├── __manifest__.py
├── README.md
├── models/
│   ├── __init__.py
│   ├── book.py              # Book model
│   └── borrowing.py         # Borrowing model
├── views/
│   ├── book_views.xml       # Book views and actions
│   ├── borrowing_views.xml  # Borrowing views and actions
│   └── menu_views.xml       # Menu structure
├── security/
│   ├── library_security.xml # Security groups and rules
│   └── ir.model.access.csv  # Access rights
├── reports/
│   ├── book_inventory_report.xml      # Inventory report
│   └── borrowing_history_report.xml   # Borrowing history report
└── static/
    └── description/
        ├── index.html       # Module description
        └── icon.png         # Module icon (needs to be created)
```

## Technical Details

- **Version:** 19.0.1.0.0
- **License:** LGPL-3
- **Dependencies:** base, mail
- **Database Models:**
  - `library.book`
  - `library.borrowing`
  - `library.category`
  - `library.member` (delegation inheritance of `res.partner`)
  - `res.partner` (extension inheritance)
- **Sequences:** `library.borrowing` (BRW prefix), `library.member` (MEM prefix)

## Data Validation

- **ISBN:** Must be 10 or 13 digits (hyphens and spaces allowed)
- **Unique ISBN:** Each book must have a unique ISBN
- **Date Validation:** Return dates must be after borrow dates
- **Availability Check:** Cannot borrow a book that's already borrowed
- **State Management:** Automatic state transitions with validation

## Future Enhancements

Potential features for future versions:
- Fine calculation for overdue books
- Reservation system for borrowed books
- Email notifications for due dates
- Barcode scanning integration
- Multi-language support
- Advanced analytics dashboard

## Support

For issues or questions, please contact your system administrator.

## Credits

Developed as part of Odoo 19 technical training.
