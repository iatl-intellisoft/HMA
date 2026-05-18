{
    'name': 'Tax Base Amount Customization',
    'version': '1.0',
    'summary': 'Use custom tax base amount from product in invoices',
    'description': 'Adds tax_base_amount to product and uses it in invoice tax calculation',
    'depends': [
        
        'account',
        'stock',
        'sale',
        'product',
        'account_accountant'
    ],
    'data': [
        'security/ir.model.access.csv', 
        'views/product_views.xml', 
        'views/account_move_views.xml',
        'views/tax_invoice_views.xml',  
    ],
    'installable': True,
    'application': False,
}