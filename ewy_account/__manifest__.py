# -*- coding: utf-8 -*-
{
    'name': 'Account Customisations',
    'summary': 'Custom accounting enhancements and modifications',
    'description': """
        Account Customisations
        ======================
        
        This module contains custom accounting features and enhancements, including:
        - Budget warnings and validations
        - Accounting dashboard customisations
        - Journal and account view modifications
        - Additional accounting reports and business requirements
    """,
    'author': 'IATL International',
    'website': 'http://www.iatl-sd.com',
    'category': 'Accounting/Accounting',
    'version': '18.0.1.0.0',
    'license': 'LGPL-3',
    'depends': [
        'account',
        'analytic',
        'account_budget',
        'account_reports',
    ],
    'data': [
        'views/account_journal_dashboard_view.xml',
        'views/account_views.xml',
        # 'views/account_payment_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
