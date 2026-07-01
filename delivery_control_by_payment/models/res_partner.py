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
        default='approved'
    )