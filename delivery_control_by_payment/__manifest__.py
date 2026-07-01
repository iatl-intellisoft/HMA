{
    'name': 'التحكم في إنشاء أمر التوصيل حسب نوع العميل والدفع',
    'version': '18.0.1.0.0',
    'summary': 'منع الإنشاء التلقائي لأمر التوصيل للعميل المباشر إلا بعد تسجيل دفعية على الفاتورة',
    'description': """
يضيف هذا الموديول حقل "نوع العميل" (معتمد / مباشر) على جهة الاتصال.

- العميل المعتمد: يستمر العمل بالطريقة الافتراضية لأودوو (إنشاء أمر التوصيل تلقائياً عند تأكيد عرض السعر / أمر البيع).
- العميل المباشر: لا يتم إنشاء أمر التوصيل تلقائياً إلا بعد تسجيل دفعية (ولو جزئية) على فاتورة أمر البيع.
""",
    'category': 'Inventory/Sales',
    'author': 'Custom Development',
    'license': 'LGPL-3',
    'depends': ['sale_management', 'sale_stock', 'account'],
    'data': [
        'data/ir_cron_data.xml',
        'views/res_partner_views.xml',
        'views/sale_order_views.xml',
    ],
    'installable': True,
    'application': False,
}
