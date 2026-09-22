# -*- coding: utf-8 -*-

from collections import defaultdict

from odoo import models, fields, api
from odoo.addons import decimal_precision as dp
from odoo.tools.float_utils import float_compare, float_round, float_is_zero


class StockValuationLayer(models.Model):
    _inherit = "stock.valuation.layer"

    foreign_price_unit = fields.Monetary(
        'Foreign Unit Value', readonly=True, currency_field='force_currency_id')
    foreign_value = fields.Monetary(
        'Total Foreign Value', readonly=True, currency_field='force_currency_id')
    force_currency_id = fields.Many2one('res.currency', 'Force Currency',
                                        help='Use this currency instead of the product company currency'
                                        )  
    foreign_remaining_value = fields.Monetary(
        'Foreign Remaining Value', readonly=True, currency_field='force_currency_id')
    
    name = fields.Char()

    def update_data_layer(self):
        """
        TO call in server action to update old data before migration
        """
        for rec in self:
            if rec.stock_move_id:
                # rec.stock_move_id.write(
                #     {'price_unit': rec.unit_cost, 'foreign_price_unit': rec.foreign_price_unit, })
                foreign_price_unit = rec.stock_move_id.foreign_price_unit if rec.stock_move_id.foreign_price_unit else rec.foreign_price_unit
                foreign_value = foreign_price_unit * rec.quantity
                rec.write(
                    {'foreign_price_unit': foreign_price_unit, 'foreign_value': foreign_value})
            # if rec.foreign_price_unit:
            #     rec.foreign_value = rec.foreign_price_unit * rec.quantity
