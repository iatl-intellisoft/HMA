# -*- coding: utf-8 -*-
from odoo import models, fields


class ResPartner(models.Model):
    _inherit = 'res.partner'

    requires_sale_approval = fields.Boolean(
        string='عميل معتمد (يتطلب اعتماد المبيعات)',
        default=False
    )
