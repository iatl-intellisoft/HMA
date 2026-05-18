# -*- coding: utf-8 -*-
{
    'name': "Check Printing Custom V18 BETA",

    'summary': """
        This module allows you to print cheques using a normal printer or a special cheque printer.
    """,

    'author': "IATL International",
    'website': "http://www.iatl-sd.com",
    'category': 'Human Resource',
    'version': '18.0',
    'depends': ['account','ii_simple_check_management'],
    'data': [
        'security/ir.model.access.csv',
        'data/report_paperformat.xml',
        'wizards/print_prenumbered_check.xml',
        'views/check_dimension.xml',
        'views/check_printing_reason.xml',
        'views/check_printing_log.xml',
        'views/check_payment.xml',
        'reports/sp_check_print_report.xml',
        'reports/a4_check_print_report.xml',
    ],
}
