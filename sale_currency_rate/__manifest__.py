# -*- coding: utf-8 -*-
{
    'name': "Sale Currency Rate",

    'summary': """Add sale rate in currency configuration other than odoo currency rate to calculate sale price base on it
        """,
    'description': """ 
    """,
    'author': "IATL International",
    'website': "http://www.iatl-sd.com",
    'category': 'Sale',
    'version': '18.0.1.0.0',
    'depends': ['base', 'sale', 'mail', 'product'],
    'data': [
        'security/currency_security.xml',
        'security/ir.model.access.csv',
        'views/res_currency_views.xml',
        'views/sale_views.xml',
    ],
}
