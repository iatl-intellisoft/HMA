# -*- coding: utf-8 -*-
from odoo import fields, models


class Banks(models.Model):
    _inherit = 'res.bank'

    check_dimension_id = fields.Many2one('check.dimension', string='Check Dimension', ondelete='set null')
