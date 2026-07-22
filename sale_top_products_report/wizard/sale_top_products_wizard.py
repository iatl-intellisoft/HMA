from odoo import models, fields, api
from odoo.exceptions import UserError


class SaleTopProductsWizard(models.TransientModel):
    _name = 'sale.top.products.wizard'
    _description = 'Top Selling Products Report Wizard'

    date_from = fields.Date(string='من تاريخ', required=True,
                             default=fields.Date.context_today)
    date_to = fields.Date(string='إلى تاريخ', required=True,
                           default=fields.Date.context_today)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        for rec in self:
            if rec.date_from and rec.date_to and rec.date_from > rec.date_to:
                raise UserError('تاريخ البداية لازم يكون قبل تاريخ النهاية.')

    def action_print_report(self):
        self.ensure_one()
        data = {
            'date_from': fields.Date.to_string(self.date_from),
            'date_to': fields.Date.to_string(self.date_to),
        }
        return self.env.ref(
            'sale_top_products_report.action_report_top_products'
        ).report_action(self, data=data)
