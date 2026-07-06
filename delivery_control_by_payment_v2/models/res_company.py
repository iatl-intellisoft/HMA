# -*- coding: utf-8 -*-
from odoo import models, fields


class ResCompany(models.Model):
    _inherit = 'res.company'

    sale_approval_user_id = fields.Many2one(
        'res.users',
        string='مسؤول اعتماد المبيعات'
    )
