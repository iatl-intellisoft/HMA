# -*- coding: utf-8 -*-
from odoo import models, fields


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    sale_approval_user_id = fields.Many2one(
        'res.users',
        string='مسؤول اعتماد المبيعات',
        related='company_id.sale_approval_user_id',
        readonly=False
    )
