{
    'name': 'Sale Custom Workflow By Customer Type',
    'version': '18.0.1.0.0',
    'summary': 'منع الإنشاء التلقائي لأمر التوصيل للعميل المباشر إلا بعد تسجيل دفعية على الفاتورة',
    'category': 'Inventory/Sales',
    'author': 'Custom Development',
    'license': 'LGPL-3',
    'depends': ['sale_management', 'sale_stock', 'account'],
    'data': [
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
}
