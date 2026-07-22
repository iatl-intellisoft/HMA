{
    'name': 'Sale Top Products Report',
    'version': '18.0.1.0.0',
    'summary': 'تقرير أكثر المنتجات مبيعًا حسب الكمية المسلمة خلال فترة تاريخ محددة',
    'description': """
تقرير PDF يعرض أكثر المنتجات مبيعًا (حسب Qty Delivered) خلال فترة تاريخ يحددها المستخدم،
مرتبة تنازليًا مع رقم ترتيب لكل منتج.
    """,
    'category': 'Sales',
    'author': 'Custom',
    'depends': ['sale', 'sale_management', 'stock'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/wizard_view.xml',
        'report/report_action.xml',
        'report/report_template.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
