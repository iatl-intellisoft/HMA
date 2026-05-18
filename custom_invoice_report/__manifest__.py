# -*- coding: utf-8 -*-
{
    'name': 'Custom Invoice Report - Tax Base Amount',
    'version': '18.0.1.0.0',
    'category': 'Sales',
    'summary': 'Print invoice report from SO using tax_base_amount as price',
    'description': """
        Adds a button on Sale Order to print the invoice report
        where the unit price is replaced by the product's tax_base_amount field.
    """,
    'author': 'Custom',
    'depends': [
        'sale_management',
        'account',
    ],
    'data': [
        'security/ir.model.access.csv',
        'report/report_action.xml',
        'report/invoice_report_tax_base.xml',
        'views/sale_order_view.xml',
    ],
    'installable': True,
    'auto_install': False,
    'license': 'LGPL-3',
}
