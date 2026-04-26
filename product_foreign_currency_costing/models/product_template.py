from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    foreign_cost_currency_id = fields.Many2one('res.currency', string='Foreign Cost Currency', compute='_compute_foreign_cost')
    foreign_cost = fields.Float(
        string='Foreign Cost',
        compute='_compute_foreign_cost',
        digits='Product Price',
        help="Standard Cost converted to the company's Foreign Cost Currency"
    )
    margin_percent = fields.Float(string='Margin %')

    @api.depends('standard_price', 'company_id.foreign_cost_currency_id')
    def _compute_foreign_cost(self):
        for record in self:
            company = self.env.company
            foreign_currency = company.foreign_cost_currency_id
            record.foreign_cost_currency_id = foreign_currency.id
            if not foreign_currency:
                record.foreign_cost = 0.0
                continue
            record.foreign_cost = foreign_currency._convert(
                record.standard_price, 
                company.currency_id,
                company, 
                fields.Date.context_today(record)
            )


    @api.onchange('margin_percent')
    def _onchange_margin_percent(self):
        PurchaseLine = self.env['purchase.order.line']
        for rec in self:
            line = PurchaseLine.search(
                [
                    ('product_id', 'in', rec.product_variant_ids.ids),
                    ('order_id.state', 'in', ['purchase', 'done']),
                ],
                order='create_date desc, id desc',
                limit=1
            )
            cost = line.price_unit if line else 0.0
            rec.list_price = cost + (
                cost * rec.margin_percent / 100
            )
            