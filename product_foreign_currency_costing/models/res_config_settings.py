from odoo import fields, models

class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    foreign_cost_currency_id = fields.Many2one(
        related='company_id.foreign_cost_currency_id',
        string='Foreign Cost Currency',
        readonly=False
    )
