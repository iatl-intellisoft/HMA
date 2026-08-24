# -*- coding: utf-8 -*-
###############################################################################
#
#    IATL-Intellisoft International Pvt. Ltd.
#    Copyright (C) 2021 Tech-Receptives(<http://www.iatl-intellisoft.com>).
#
###############################################################################

{
    'name': "HR Deduction",

    'summary': """
        Short (1 phrase/line) summary of the module's purpose, used as
        subtitle on modules listing or apps.openerp.com""",

    'description': """
        Long description of module's purpose
    """,
    'author': "IATL Intellisoft International",
    'website': "http://www.iatl-intellisoft.com",
    'category': 'Human Resource',
    'depends': ['hr_custom', 'hr_payroll_custom'],

    'data': [
        'security/ir.model.access.csv',
        'security/deduction_security.xml',
        'views/hr_deduction_views.xml',
        'views/dedcution_batch_view.xml',
        'views/hr_deduct_conf_views.xml',
        'views/hr_payroll_view.xml',
        # 'data/hr_deduction_data.xml',
        # 'data/deduction_tempate.xml',
        'report/hr_deduction_report.xml',

    ],

}
