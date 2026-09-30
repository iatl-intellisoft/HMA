# -*- coding: utf-8 -*-
{
    'name': 'Partner Ledger – Display Foreign Currencies',
    'version': '18.0.1.1.0',
    'summary': 'Show partner ledger balances grouped by original transaction currency',
    'category': 'Accounting/Accounting',
    'description': """
Partner Ledger – Display Foreign Currencies
============================================
Adds a **Display Foreign Currencies** toggle to the Partner Ledger Options
dropdown.

When enabled the report groups each partner's journal items by their
transaction currency and displays the Debit / Credit / Balance columns in
that currency instead of the company currency.

Example: if your base currency is USD but you have invoices posted in EUR,
enabling this option shows a separate row for that partner in EUR with the
original EUR amounts.
    """,
    'author': 'Custom',
    'depends': ['account_reports'],
    'data': [],
    'assets': {
        'web.assets_backend': [
            'partner_ledger_foreign_currency/static/src/components/**/*',
        ],
    },
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
