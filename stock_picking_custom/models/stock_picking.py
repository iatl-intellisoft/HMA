from odoo import models, fields, api

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    national_id = fields.Char(
        related="sale_id.partner_id.national_id",
        string="الرقم الوطني",
        store=True,
        readonly=True,
    )

    vat_id = fields.Char(
        related="sale_id.partner_id.vat",
        string="الرقم الضريبي",
        store=True,
        readonly=True,
    )
    phone = fields.Char(
        related="sale_id.partner_id.phone",
        string="رقم الهاتف",
        store=True,
        readonly=True,
    )
    
    delivery_amount = fields.Float(
        string='Delivery Amount',
        compute='_compute_delivery_amount',
        store=True, 
    )
 

    @api.depends(
        'move_ids_without_package.move_line_ids.quantity',
        'move_ids_without_package.sale_line_id.price_unit',
        'move_ids_without_package.sale_line_id.discount',
        'move_ids_without_package.sale_line_id.tax_id'
    )
    def _compute_delivery_amount(self):
        for picking in self:
            total = 0.0

            for move in picking.move_ids_without_package:
                sale_line = move.sale_line_id
                if not sale_line:
                    continue
 
                qty_done = sum(move.move_line_ids.mapped('quantity'))

                if not qty_done:
                    continue
 
                price = sale_line.price_unit * (1 - (sale_line.discount or 0.0) / 100.0)
 
                taxes = sale_line.tax_id.compute_all(
                    price, 
                    quantity=qty_done,
                    product=move.product_id,
                    partner=sale_line.order_id.partner_shipping_id
                )
 
                total += taxes['total_included']
 
                # total += taxes['total_excluded']

            picking.delivery_amount = total
 

    handling_price = fields.Float(
        string='سعر العتالة للكرتونة',
        default=400.0 
    )

    handling_amount = fields.Float(
        string='إجمالي العتالة',
        compute='_compute_handling_amount',
        store=True,
    )

    @api.depends(
        'move_ids_without_package.quantity',
        'move_ids_without_package.product_uom_qty',
        'handling_price',
        'state'
    )
    def _compute_handling_amount(self):
        for picking in self:
            total_cartons = 0

            for move in picking.move_ids_without_package:
                qty = move.quantity if picking.state == 'done' else move.product_uom_qty
                total_cartons += qty

            picking.handling_amount = total_cartons * picking.handling_price
