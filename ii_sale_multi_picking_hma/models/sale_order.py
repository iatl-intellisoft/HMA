from odoo import _, api, fields, models

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    @api.onchange('order_id.warehouse_id', 'product_id', 'product_uom_qty')
    def _onchange_warehouse_id(self):
        if self.product_id.is_storable and self.product_id.tracking == 'lot':
            quantity = self.product_uom._compute_quantity(self.product_uom_qty, self.product_id.uom_id)
            lots = self.env['stock.quant'].search([('product_id', '=', self.product_id.id), ('quantity', '>=', quantity)], order='inventory_date asc')
            if lots:
                warehouse_id = lots[0].location_id.warehouse_id
                self.warehouse_id = warehouse_id

