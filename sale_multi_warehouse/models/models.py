# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from itertools import groupby


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    warehouse_id = fields.Many2one('stock.warehouse', readonly=False)

    def _prepare_procurement_values(self, group_id):
        res = super()._prepare_procurement_values(group_id=group_id)
        res.update({"warehouse_id": self.warehouse_id})

        return res