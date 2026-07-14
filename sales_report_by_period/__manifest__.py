# -*- coding: utf-8 -*-
{
    'name': 'تقرير مبيعات للأصناف بالفترة',
    'version': '18.0.1.0.0',
    'category': 'Accounting/Reporting',
    'summary': 'تقرير تفصيلي لمبيعات الفواتير بالأصناف خلال فترة محددة، مع إمكانية الطباعة PDF',
    'description': """
تقرير مبيعات للأصناف
=====================
يعرض هذا التقرير كل فاتورة مبيعات خلال فترة محددة، مع تفاصيل الأصناف داخل كل فاتورة
(رقم الصنف، اسم الصنف، الوحدة، السعر، الكمية، المجموع)، بالإضافة إلى إجمالي المبلغ
والمدفوع والمردود والمتبقي لكل فاتورة، وإجمالي عام في نهاية التقرير.
    """,
    'author': 'Custom Development',
    'license': 'LGPL-3',
    'depends': ['account', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'report/report_paperformat.xml',
        'wizard/sale_report_wizard_view.xml',
        'report/report_sales_summary.xml',
        'report/report_sales_summary_templates.xml',
    ],
    'installable': True,
    'application': False,
}
