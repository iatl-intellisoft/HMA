# -*- coding: utf-8 -*-
{
    'name': "HR Payroll Custom",

    'summary': """
        """,

    'description': """
        
    """,

    'author': "IATL International",
    'website': "http://www.iatl-sd.com",
    'category': 'Human Resource',
    'version': '0.1',
    'depends': ['hr_payroll_account','hr_contract_custom', 'hr_department_custom'],


    'data': [
        'views/hr_payslip_view.xml',
        'views/res_config_settings_views.xml',
        'data/data.xml',
        'views/salary_rule.xml',
        'views/account_move_view.xml',
        'views/hr_leave.xml',
        'views/hr_contract.xml',
	    'report/hr_voucher_report_template.xml',
	    'report/report_actions.xml',

    ],
}
