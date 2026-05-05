# -*- coding: utf-8 -*-
{
    'name': "Check Management",

    'summary': """
        Simple Check Management""",

    'description': """
        Simple Check Management
    """,
    'author': "Iatl-intellisoft",
    'category': 'Accounting',
    'version': '0.1',
    'depends': ['account', 'account_check_printing', 'mail'],
    'data': [

        'security/check_security.xml',
        'security/ir.model.access.csv',
        'data/data.xml',
        #'data/sequence.xml',
        'data/schedule_action.xml',
        'wizard/check_replacement_wizard.xml',
        'wizard/print_check_wizard.xml',
        'views/check_view.xml',
        'views/payment.xml',
        # Check print report
        'report/check_bank_template.xml',
        'report/reports.xml',
        'wizard/print_check_wizard.xml',
        #'views/account_journal_views.xml',
        'views/res_config_settings_view.xml',

    ],
}
