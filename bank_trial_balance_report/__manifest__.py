{
    'name': 'Bank Trial Balance Report',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Accounting',
    'summary': 'تقرير أرصدة إجمالية للبنوك خلال فترة معينة بدون تفاصيل الحركات',
    'description': """
تقرير أرصدة البنوك (بدون تفاصيل)
=================================
هذا الموديول يضيف تقرير مخصص يعرض:
- رصيد أول المدة لكل حساب بنك
- إجمالي المدين خلال الفترة
- إجمالي الدائن خلال الفترة
- رصيد آخر المدة

بنفس القيم الظاهرة في دفتر الأستاذ العام لنفس الحسابات، لكن مجمّعة بدون سطور تفصيلية،
مع إمكانية طباعة التقرير كـ PDF.
""",
    'author': 'Custom Development',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/bank_balance_wizard_view.xml',
        'report/report_bank_balance.xml',
    ],
    'installable': True,
    'application': False,
}
