# -*- coding: utf-8 -*-
{
    'name': 'Bank Balance Report | تقرير أرصدة الحسابات البنكية',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Reporting',
    'summary': 'تقرير يعرض أرصدة جميع الحسابات البنكية خلال فترة محددة (افتتاحي، مقبوضات، مدفوعات، ختامي)',
    'description': """
Bank Balance Report
====================
موديول يضيف تقرير أرصدة البنوك (Bank Balance Report) لعرض:
    - الرصيد الافتتاحي لكل بنك (Journal من نوع Bank)
    - إجمالي المقبوضات (مدين) خلال الفترة
    - إجمالي المدفوعات (دائن) خلال الفترة
    - الرصيد الختامي
    - تفاصيل الحركات لكل بنك (اختياري)

يدعم:
    - اختيار فترة زمنية (من - إلى)
    - فلترة حسب الشركة/الشركات
    - فلترة حسب بنك معين أو أكثر
    - تصدير PDF عبر QWeb
    - تصدير Excel
    """,
    'author': 'Custom Development',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/bank_balance_wizard_views.xml',
        'report/bank_balance_templates.xml',
        'report/bank_balance_report_action.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
