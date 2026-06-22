# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    total_cbm = fields.Float(
        'Total CBM',
        compute='_compute_total_cbm',
        store=True,
        digits='Volume',
        help="Total volume in cubic meters (CBM), calculated from all move line volumes.",
    )

    @api.depends('move_line_ids.volume')
    def _compute_total_cbm(self):
        for picking in self:
            picking.total_cbm = sum(picking.move_line_ids.mapped('volume'))
