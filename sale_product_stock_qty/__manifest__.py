# -*- coding: utf-8 -*-
{
    'name': 'Sale Product Stock Quantity',
    'version': '18.0.1.0.0',
    'summary': 'Display product on-hand quantity on sale order lines',
    'category': 'Sales/Sales',
    'depends': ['sale_stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_confirm_no_stock_wizard_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
