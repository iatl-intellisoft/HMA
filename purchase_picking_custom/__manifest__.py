# -*- coding: utf-8 -*-
{
    'name': 'Purchase Picking Custom States',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Purchase',
    'summary': 'Add custom picking states and PO line quantity fields',
    'description': """
        This module adds:
        - Custom picking states: Under Manufacturing, Under Shipping
        - Rename 'Done' to 'Received' for Receipt operations
        - PO line computed fields: Qty Under Manufacturing, Qty Under Shipping
        - New fields on picking: Bill of Lading Number, Number of Containers
    """,
    'author': 'Custom Development',
    'depends': ['purchase', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_picking_views.xml',
        'views/purchase_order_views.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}