{
    'name': 'Payments Internal Transfer',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Restore Internal Transfer functionality for Payments in Odoo 18',
    'description': """
Payments Internal Transfer
==========================
Restores the internal payment transfer functionality that was removed in Odoo 18.
Enables fund transfers between different bank/cash journals within a single company.

Features:
- Internal Transfer flag on payments
- Destination Journal selection
- Automatic paired payment creation on confirmation
- Dedicated menu under Accounting
- Quick-create from Journal Kanban
- Internal Transfers filter in payment list
    """,
    'author': 'IATL Intellisoft',
    'depends': ['account'],
    'data': [
        'views/account_payment_views.xml',
        'views/menu_items.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
