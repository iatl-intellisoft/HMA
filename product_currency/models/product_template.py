# For copyright and license notices, see __manifest__.py file in module root
# directory
from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = "product.template"

    force_currency_id = fields.Many2one(
        'res.currency',
        'Force Currency',
        help='Use this currency instead of the product company currency'
    )
    company_currency_id = fields.Many2one(related='company_id.currency_id',store=True,string="Company Currency")

class ProductProduct(models.Model):
    _inherit = "product.product"

    company_currency_id = fields.Many2one(
        'res.currency',
        string="Company Currency",
        related='company_id.currency_id',
        store=True,
        readonly=True
    )