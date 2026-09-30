# -*- coding: utf-8 -*-
{
    'name': 'Purchase Picking Custom States',
    'version': '18.0.1.4.0',
    'category': 'Inventory/Purchase',
    'summary': 'Add custom picking states and PO line quantity fields',
    'description': """
        This module adds:
        - Custom picking states: Under Manufacturing, Under Shipping, Under Clearance
        - Rename 'Done' to 'Received' for Receipt operations
        - PO line computed fields: Qty Under Manufacturing, Qty Under Shipping,
          Qty Under Clearance
        - New fields on picking: Bill of Lading Number, Number of Containers
        - "Shipment Details" tab on Purchase Order with:
          Shipment Status (Under Preparation, Loaded, In Transit,
          Arrived at Port, Under Clearance, Received), Loading Date,
          Shipment Date, ETD, ETA
        - Fix: hide the native Validate button while a custom shipment
          state is active, so it no longer renders twice
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