from odoo import api, fields, models

class ProductTemplate(models.Model):
    _inherit = 'product.template'

    
    margin_percent = fields.Float(string='Margin %')

    
    @api.onchange('margin_percent')
    def _onchange_margin_percent(self):
        
        cost * margin_percent / 100
        
            