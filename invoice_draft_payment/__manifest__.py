# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

{
    'name': 'Invoice Draft Payment ',
    'category': 'Accounting',
    'version': '18.1',
    'depends': ['account'],
    'description': """
Bridge module for mail and enterprise
=====================================

From invoice , bill or receipts when create payment in journal that have customized field Draft Payment = True create payment in draft state 
""",
    'data': [
   			 # 'views/account_move_view.xml',
   			 'views/account_journal.xml',

    ],
    'license': 'OEEL-1',
}
