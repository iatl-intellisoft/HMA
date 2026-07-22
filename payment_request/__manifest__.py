# -*- coding: utf-8 -*-
{
    'name': "Payment Request",

    'summary': """
        """,

    'description': """
        
    """,

    'author': "IATL International",
    'website': "http://www.iatl-sd.com",
    'category': 'Accounting',
    'depends': ['account_custom', 'hr', 'invoice_draft_payment', 'analytic', 'hr_department_custom'],
    'data': [
        'security/payment_security.xml',
        'security/ir.model.access.csv',
        'data/sequence.xml',
        'data/payment_request_data.xml',
        'wizards/clearnce_report_views.xml', 
        'views/res_config_settings.xml',
        'views/account_payment_views.xml',   
        'views/payment_request_views.xml',
        'views/payment_clearance_views.xml',
        'views/payment_menuitem.xml',
        'views/payment_request_report_view.xml',
        'views/custody_clearance_report_view.xml', 
    ],
    'license': 'LGPL-3',
}
