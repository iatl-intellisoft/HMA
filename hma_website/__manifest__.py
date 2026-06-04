# -*- coding: utf-8 -*-
{
    'name': 'HMA Developed Projects — Website',
    'version': '18.0.1.0.10',
    'summary': 'Full website for H.M.A Developed Projects CO.LTD, exclusive Chinbull agent in Sudan.',
    'description': '''
        Complete Odoo Website module for H.M.A Developed Projects CO.LTD.
        - Home, About, Products, Chinbull, Wholesale, Location, Contact, Sitemap pages
        - Bilingual Arabic / English with RTL support
        - Custom HMA Design System (brand red #C8102E + gold)
        - Chinbull exclusive agency showcase
        - Product catalogue with detail pages
        - WhatsApp CTA integration
        - Wholesale enquiry section
    ''',
    'author': 'H.M.A Developed Projects CO.LTD',
    'website': 'http://www.HMA.net',
    'category': 'Website',
    'license': 'LGPL-3',
    'depends': ['website', 'mail'],
    'data': [
        'security/ir.model.access.csv',
        'views/hma_layout.xml',
        'views/page_index.xml',
        'views/page_about.xml',
        'views/page_products.xml',
        'views/page_product_detail.xml',
        'views/page_chinbull.xml',
        'views/page_wholesale.xml',
        'views/page_location.xml',
        'views/page_contact.xml',
        'views/page_sitemap.xml',
        'data/hma_products.xml',
    ],
    'assets': {
        'web.assets_frontend': [
            'hma_website/static/src/css/hma_website.css',
            'hma_website/static/src/css/hma_website_home.css',
            'hma_website/static/src/js/hma_website.js',
        ],
    },
    'installable': True,
    'application': True,
    'auto_install': False,
    'sequence': 100,
}
