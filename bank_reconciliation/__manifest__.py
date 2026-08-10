# -*- coding: utf-8 -*-
{
    'name': 'Bank Reconciliation',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'Bank Statement Reconciliation for Odoo 18 Community',
    'description': """
Bank Reconciliation
===================
Allows users to create and manage bank statements and reconcile each
statement line via a wizard (match payment, match invoice/bill,
manual account entry, or write-off).

Menu: Accounting → Accounting → Bank Statements
    """,
    'author': 'IATL Intellisoft',
    'depends': ['account', 'base_import'],
    'data': [
        'security/ir.model.access.csv',
        'views/account_bank_statement_form.xml',
        'views/account_bank_reconciliation_wizard.xml',
        'views/menu_items.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
