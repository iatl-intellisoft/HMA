# -*- coding: utf-8 -*-
{
    'name': 'Product Foreign Cost and Margin Pricing',
    'version': '18.0.1.0.0',
    'summary': 'Automatically calculate sales price using margin percentage.',
    'description': """
 Margin Pricing
======================================

This module extends product pricing features in Odoo by adding:

* Margin percentage on products


Ideal for businesses purchasing in one currency and selling with controlled margins.
    """,
    'category': 'Inventory/Purchase',
    'license': 'LGPL-3',
    'depends': [
        'product',
        'purchase',
        'stock',
    ],
    'data': [
        'views/product_template_view.xml',
    ],
}