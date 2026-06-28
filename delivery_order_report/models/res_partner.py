from odoo import fields, models

class ResPartner(models.Model):
    _inherit = "res.partner"

    national_id = fields.Char(
        string="الرقم الوطني",
    )