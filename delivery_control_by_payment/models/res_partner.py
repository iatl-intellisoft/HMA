# -*- coding: utf-8 -*-
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    customer_type = fields.Selection(
        selection=[
            ('approved', 'عميل معتمد'),
            ('direct', 'عميل مباشر'),
        ],
        string='نوع العميل',
        default='approved',
        help=(
            'العميل المعتمد: يتم إنشاء أمر التوصيل تلقائياً عند تأكيد أمر البيع كالمعتاد.\n'
            'العميل المباشر: لا يتم إنشاء أمر التوصيل تلقائياً إلا بعد تسجيل دفعية '
            '(ولو جزئية) على فاتورة أمر البيع.'
        ),
    )
