# -*- coding: utf-8 -*-
{
    'name': 'تقرير المبيعات مع الدفعات المرتبطة - Sales Payments Report',
    'version': '18.0.1.0.0',
    'summary': 'عرض فواتير المبيعات خلال فترة معينة مع كل الدفعات المرتبطة '
               'بكل فاتورة (نوع الدفعية، قيمة السداد، رقم الإشعار، '
               'رقم أمر البيع)',
    'description': """
تقرير المبيعات مع الدفعات المرتبطة
====================================
موديول مستقل بالكامل لعرض فواتير المبيعات خلال فترة زمنية محددة، مع عرض
تفاصيل كل دفعة مرتبطة بكل فاتورة:

- رقم الفاتورة وتاريخها والعميل
- رقم أمر البيع المصدر للفاتورة
- إجمالي الفاتورة وحالة السداد (مدفوعة / جزئياً / غير مدفوعة)
- لكل دفعة: نوع الدفعية (كاش / بنك)، قيمة السداد، تاريخ السداد،
  ورقم الإشعار (رقم سند الدفع)

لو الفاتورة اتسددت بأكتر من دفعة (مثلاً جزء كاش وجزء بنك)، هيظهر سطر
منفصل لكل دفعة تحت نفس الفاتورة.
    """,
    'category': 'Accounting/Accounting',
    'author': 'Custom Development',
    'license': 'LGPL-3',
    'depends': ['account', 'sale'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/sales_payments_report_wizard_view.xml',
        'views/sales_payments_report_view.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'auto_install': False,
}
