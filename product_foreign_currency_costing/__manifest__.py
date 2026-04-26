# -*- coding: utf-8 -*-
{
    'name': 'Product Foreign Cost and Margin Pricing',
    'version': '18.0.1.0.0',
    'summary': 'Manage foreign cost conversion and automatically calculate sales price using margin percentage.',
    'description': """
Product Foreign Cost and Margin Pricing
======================================

This module extends product pricing features in Odoo by adding:

* Foreign cost currency configuration in Settings
* Automatic foreign cost conversion based on selected currency
* Margin percentage on products
* Automatic sales price calculation from latest purchase cost
* Improved product pricing management

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
        'views/res_config_settings_views.xml',
        'views/product_template_view.xml',
    ],
}