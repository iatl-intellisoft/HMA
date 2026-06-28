# -*- coding: utf-8 -*-
from odoo import _, api, fields, models
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    so_qty = fields.Float(
        string='SO Qty',
        compute='_compute_so_qty',
        store=True,
        digits='Product Unit of Measure',
        help="Total quantity of all order lines.",
    )

    @api.depends('order_line.product_uom_qty')
    def _compute_so_qty(self):
        for order in self:
            order.so_qty = sum(order.order_line.mapped('product_uom_qty'))

    def action_confirm(self):
        if not self.env.context.get('skip_no_stock_check'):
            for order in self:
                lines_over_stock = order.order_line.filtered(
                    lambda l: l.product_id
                    and l.product_id.type == 'consu'
                    and l.product_uom_qty > l.product_id.qty_available
                )
                if not lines_over_stock:
                    continue
                product_names = '\n'.join(
                    '- %s (ordered: %g, available: %g)' % (
                        l.product_id.display_name,
                        l.product_uom_qty,
                        l.product_id.qty_available,
                    )
                    for l in lines_over_stock
                )
                is_admin = (
                    self.env.user.has_group('sales_team.group_sale_manager')
                    or self.env.user.has_group('base.group_system')
                )
                if is_admin:
                    return {
                        'type': 'ir.actions.act_window',
                        'name': _('Confirm Sale Order'),
                        'res_model': 'sale.confirm.no.stock.wizard',
                        'view_mode': 'form',
                        'target': 'new',
                        'context': {
                            'default_sale_order_id': order.id,
                            'default_message': _(
                                "The ordered quantity exceeds available stock "
                                "for the following product(s):\n\n%s\n\n"
                                "Do you want to confirm this sale order anyway?",
                                product_names,
                            ),
                        },
                    }
                else:
                    raise UserError(_(
                        "You cannot confirm this order because the ordered "
                        "quantity exceeds available stock for the following "
                        "product(s):\n\n%s\n\nPlease contact your Sales Manager.",
                        product_names,
                    ))
        return super().action_confirm()
