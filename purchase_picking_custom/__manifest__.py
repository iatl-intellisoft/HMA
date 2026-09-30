# -*- coding: utf-8 -*-
{
    'name': 'Purchase Picking Custom States',
    'version': '18.0.1.5.0',
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
          Shipment Date, ETD, ETA, Shipping Line
        - Fix: hide the native Validate button while a custom shipment
          state is active, so it no longer renders twice
        - Shipments Status report (Purchase > Reporting): one row per
          confirmed PO with invoice number(s), shipment dates, shipping
          line, status and free days vs ETA. List view + PDF export
          (native list Export also gives Excel).
        - Items Status report (Purchase > Reporting): one row per product
          with quantity Under Preparation / In Transit / Under Clearance
          / Stock (received), based on the state of related incoming
          receipts. List view + PDF export.
    """,
    'author': 'Custom Development',
    'depends': ['purchase', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'views/stock_picking_views.xml',
        'views/purchase_order_views.xml',
        'views/purchase_status_reports_views.xml',
        'report/purchase_status_reports_templates.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}