# -*- coding: utf-8 -*-
###############################################################################
#
#    IATL-Intellisoft International Pvt. Ltd.
#    Copyright (C) 2021 Tech-Receptives(<http://www.iatl-intellisoft.com>).
#
###############################################################################

from odoo import models, fields, api, _
from odoo.addons import decimal_precision as dp
from odoo.exceptions import UserError
from odoo.tools.float_utils import float_is_zero

class StockQuant(models.Model):
    _inherit = 'stock.quant'

    force_currency_id = fields.Many2one(
        'res.currency', 'Force Currency', related='product_id.force_currency_id')
    foreign_value = fields.Monetary('Value', compute='_compute_value',
                                    groups='stock.group_stock_manager', currency_field='force_currency_id')

    @api.depends('company_id', 'location_id', 'owner_id', 'product_id', 'quantity')
    def _compute_value(self):
        """ For standard and AVCO valuation, compute the current accounting
        valuation of the quants by multiplying the quantity by
        the standard price. Instead for FIFO, use the quantity times the
        average cost (valuation layers are not manage by location so the
        average cost is the same for all location and the valuation field is
        a estimation more than a real value).
        """
        for quant in self:
            quant.currency_id = quant.company_id.currency_id
            # If the user didn't enter a location yet while enconding a quant.
            if not quant.location_id:
                quant.value = 0
                quant.foreign_value = 0
                return

            if not quant.location_id._should_be_valued() or\
                    (quant.owner_id and quant.owner_id != quant.company_id.partner_id):
                quant.value = 0
                quant.foreign_value = 0
                continue
            if quant.product_id.cost_method == 'fifo':
                quantity = quant.product_id.quantity_svl
                if float_is_zero(quantity, precision_rounding=quant.product_id.uom_id.rounding):
                    quant.value = 0.0
                    quant.foreign_value = 0.0
                    continue
                average_cost = quant.product_id.with_company(quant.company_id).value_svl / quantity
                quant.value = quant.quantity * average_cost
                foreing_average_cost = quant.product_id.with_company(quant.company_id).foreign_value_svl / quantity
                quant.foreign_value = quant.quantity * foreing_average_cost
            else:
                quant.value = quant.quantity * quant.product_id.with_company(quant.company_id).standard_price
                quant.foreign_value = quant.quantity * quant.product_id.with_company(quant.company_id).foreign_standard_price
