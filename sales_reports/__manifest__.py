# -*- coding: utf-8 -*-
{
    'name': 'Sales Reports',
    'version': '18.0.1.0.0',
    'summary': 'Detailed Sales Report — invoices, refunds, payments per sale order',
    'category': 'Sales',
    'depends': ['sale_management', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'views/sale_report_wizard_views.xml',
        'views/sale_report_line_views.xml',
        'views/sale_ops_report_wizard_views.xml',
        'views/sale_ops_report_line_views.xml',
        'views/sale_payment_report_wizard_views.xml',
        'report/sale_ops_report_template.xml',
        'report/sale_payment_report_template.xml',
    ],
    'installable': True,
    'application': False,
}
