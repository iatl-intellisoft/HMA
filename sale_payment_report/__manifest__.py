{
    'name': 'تقرير المبيعات - السداد بالتفصيل',
    'version': '18.0.1.0.0',
    'summary': 'تقرير يعرض الدفعيات المرتبطة بأوامر البيع خلال فترة محددة',
    'category': 'Sales',
    'author': 'Custom',
    'depends': ['sale', 'account'],
    'data': [
        'security/ir.model.access.csv',
        'wizard/sale_payment_report_wizard_views.xml',
        'report/report_action.xml',
        'report/report_templates.xml',
        'views/menu_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}
