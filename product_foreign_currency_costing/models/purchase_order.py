from odoo import models


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    def button_confirm(self):
        res = super().button_confirm()
        for order in self:
            for line in order.order_line:
                product_tmpl = line.product_id.product_tmpl_id
                cost = line.price_unit
                margin = product_tmpl.margin_percent
                sale_price = cost + (cost * margin / 100)
                product_tmpl.write({
                    'list_price': sale_price
                })
        return res