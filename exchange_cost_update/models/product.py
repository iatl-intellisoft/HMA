from odoo import models, fields, api
from datetime import date

class ProducExchange(models.Model):
    _name = 'product.exchange' 
    
    old_exchange_rate = fields.Float(string='Old Exchange Rate')
    new_exchange_rate = fields.Float(string='New Exchange Rate')
    exchange_change_percent = fields.Float(
        string='Exchange Change %', 
        store=True
    )
    profit_margin = fields.Float(
        string='Profit Margin (%)',
        default=20
    )
    state = fields.Selection(
    [   ('draft','Draft'),
        ('conferm','Conferm'),
    ],default="draft"
        )
    date = fields.Date( string="Date", default = fields.Date.today ,readonly="1")
   
    def action_apply_exchange_update(self):
        self.state = "conferm"
        company = self.env.company
        products = self.env['product.template'].search([])

        for rec in self:

            if not rec.old_exchange_rate:
                return

            rec.exchange_change_percent = (
                (rec.new_exchange_rate - rec.old_exchange_rate)
                / rec.old_exchange_rate
            ) * 100

            for product in products:
                new_cost = product.standard_price * (
                    1 + rec.exchange_change_percent / 100
                )
                new_sale_price = new_cost * (
                    1 + (rec.profit_margin or 0.0) / 100
                )
                product.list_price = new_sale_price
                
