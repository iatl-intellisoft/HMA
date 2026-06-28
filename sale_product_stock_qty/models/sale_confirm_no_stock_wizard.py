# -*- coding: utf-8 -*-
from odoo import fields, models


class SaleConfirmNoStockWizard(models.TransientModel):
    _name = 'sale.confirm.no.stock.wizard'
    _description = 'Confirm Sale Order with No Stock'

    sale_order_id = fields.Many2one('sale.order', required=True, readonly=True)
    message = fields.Text(readonly=True)

    def action_confirm(self):
        self.sale_order_id.with_context(skip_no_stock_check=True).action_confirm()
        return {'type': 'ir.actions.act_window_close'}
