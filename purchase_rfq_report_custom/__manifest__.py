# -*- coding: utf-8 -*-
{
    'name': 'Purchase RFQ Report Custom Columns',
    'version': '18.0.1.0.0',
    'category': 'Inventory/Purchase',
    'summary': 'Customize the RFQ report lines table columns',
    'description': """
        Adjusts the Request for Quotation (RFQ) printed report
        (purchase.report_purchasequotation_document):
        - New "Reference" column showing the product's internal reference.
        - "Description" column now shows only the product name (instead of
          the order line's free-text name/description).
        - "Expected Date" column moved to be the last column, after Qty.

        Final column order: Description | Reference | Qty | Expected Date
    """,
    'author': 'Custom Development',
    'depends': ['purchase'],
    'data': [
        'report/purchase_quotation_report_templates.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
