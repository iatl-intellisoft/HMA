{
    'name': 'Account Journal Currency Conversion',
    'version': '1.1',
    'category': 'Accounting',
    'summary': 'Custom currency conversion rates for journal entry lines.',
    'description': """
        Allows users to configure custom currency conversion rates
        (e.g. AED → USD) under Accounting → Configuration → Custom Currency Rates.

        When a journal entry line's currency is changed, the Amount in Currency
        field is calculated using the custom rate if one is configured for that
        currency pair.  If no custom rate exists, the standard Odoo exchange
        rate is used as a fallback.
    """,
    'depends': ['account'],
    'data': [
        'security/ir.model.access.csv',
        'views/custom_currency_rate_views.xml',
    ],
    'installable': True,
    'application': False,
    'license': 'LGPL-3',
}