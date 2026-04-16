# -*- coding: utf-8 -*-

{
    'name': 'HR Loan',
    'author': "IATL International",
    'website': "http://www.iatl-sd.com",
    'category': 'Human Resource',
    'description': """
	""",

    'depends': ['account','hr_custom', 'hr_payroll_custom','hr_holidays'],
    'data': [
        'security/ir.model.access.csv',
        'security/Loan_security.xml',
        'sequences/hr_loan_sequence.xml',
        'report/loan_report.xml',
        'report/reports.xml',
        'report/salary_advance.xml',
        'report/salary_reports.xml',
        'views/hr_loan_view.xml',
        'views/hr_payroll_view.xml',
        'views/res_config_settings.xml',
        'views/loan_payment_view.xml',
        'views/loan_postpone_views.xml',
        'views/account_move_views.xml',
        'data/loan_payroll.xml',
        'data/loan_template.xml',
        'data/salary_advance_template.xml'
     

    ],

    'installable': True,
    'application': True,
    'auto_install': False,
}