from odoo import models, fields, api

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    old_exchange_rate = fields.Float(string='Old Exchange Rate')
    new_exchange_rate = fields.Float(string='New Exchange Rate')
    exchange_change_percent = fields.Float(
        string='Exchange Change %',
        compute='_compute_exchange_change',
        store=True
    )
    previous_cost = fields.Float(
            string='Previous Cost', 
            store=True
        )
    profit_margin = fields.Float(
        string='Profit Margin (%)',
        default=20
    )

    new_cost = fields.Float(
        string='New Cost',
        compute='_compute_new_cost',
        store=True
    )

    new_sale_price = fields.Float(
        string='New Sale Price',
        compute='_compute_new_sale_price',
        store=True
    )

    @api.depends('old_exchange_rate', 'new_exchange_rate')
    def _compute_exchange_change(self):
        for rec in self:
            if rec.old_exchange_rate:
                rec.exchange_change_percent = (
                    (rec.new_exchange_rate - rec.old_exchange_rate)
                    / rec.old_exchange_rate
                ) * 100
            else:
                rec.exchange_change_percent = 0

    @api.depends('previous_cost', 'exchange_change_percent')
    def _compute_new_cost(self):
        for rec in self:
            rec.new_cost = rec.previous_cost * (
                1 + rec.exchange_change_percent / 100
            )

    @api.depends('new_cost', 'profit_margin')
    def _compute_new_sale_price(self):
        for rec in self:
            rec.new_sale_price = rec.new_cost * (
                1 + rec.profit_margin / 100
            )
             
    def action_apply_exchange_update(self):
        for rec in self: 
            rec.list_price = rec.new_sale_price
            rec.standard_price = rec.new_cost

