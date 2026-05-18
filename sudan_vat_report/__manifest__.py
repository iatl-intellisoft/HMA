# -*- coding: utf-8 -*-
{
    'name': 'Sudan VAT Monthly Declaration | الإقرار الشهري للضريبة على القيمة المضافة',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Localizations/Reporting',
    'summary': 'Sudan VAT Monthly Declaration Report (Form 3)',
    'description': """
        Sudan VAT Monthly Declaration
        ==============================
        - Monthly VAT Declaration Report (Form 3)
        - Compliant with Sudan Tax Authority requirements
        - Matches official VAT declaration form
    """,
    'author': 'Sudan ERP',
    'depends': ['account', 'base_setup'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/sudan_vat_wizard_view.xml',
        'report/sudan_vat_report.xml',
        'report/sudan_vat_report_template.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
    'license': 'LGPL-3',
}
