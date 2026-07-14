# -*- coding: utf-8 -*-
{
    'name': 'تقرير الفواتير بالمنتجات - Invoice Products Report',
    'version': '18.0.1.0.0',
    'summary': 'عرض الفواتير في فترة معينة بالمنتجات وتفاصيلها والإجمالي',
    'description': """
تقرير الفواتير بالمنتجات
=========================
- اختيار فترة زمنية (من تاريخ - إلى تاريخ)
- عرض تفاصيل الفواتير مجمعة حسب المنتج في List View (Tree)
- عرض الكمية الإجمالية وإجمالي الأسعار لكل منتج ولكل الفواتير
    """,
    'category': 'Accounting/Accounting',
    'author': 'Custom Development',
    'license': 'LGPL-3',
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/invoice_report_wizard_view.xml',
        'views/invoice_report_tree_view.xml',
        'views/menu_views.xml',
        'reports/report.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
