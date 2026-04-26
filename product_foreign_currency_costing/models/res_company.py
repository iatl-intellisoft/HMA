from odoo import fields, models

class ResCompany(models.Model):
    _inherit = 'res.company'

    foreign_cost_currency_id = fields.Many2one('res.currency', string='Foreign Cost Currency')
