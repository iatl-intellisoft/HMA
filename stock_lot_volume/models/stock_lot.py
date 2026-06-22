# -*- coding: utf-8 -*-
from odoo import api, fields, models


class StockLot(models.Model):
    _inherit = 'stock.lot'

    move_line_ids = fields.One2many(
        'stock.move.line', 'lot_id', 'Move Lines', readonly=True,
    )

    volume = fields.Float(
        'Volume (CBM)',
        compute='_compute_volume',
        store=True,
        digits='Volume',
        help="Volume in cubic meters (CBM), automatically read from the latest "
             "incoming receipt move line for this lot.",
    )

    @api.depends(
        'move_line_ids.volume',
        'move_line_ids.picking_id.picking_type_code',
    )
    def _compute_volume(self):
        for lot in self:
            # Take the volume from the latest incoming move line that has a value
            incoming_lines = lot.move_line_ids.filtered(
                lambda l: l.picking_id.picking_type_code == 'incoming' and l.volume > 0
            )
            lot.volume = incoming_lines[-1].volume if incoming_lines else 0.0
