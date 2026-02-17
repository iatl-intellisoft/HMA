from odoo import models, fields, api
from datetime import timedelta


class ProductTemplate(models.Model):
    _inherit = 'product.template'
 
    is_safety_equipment = fields.Boolean(string="Is Safety Equipment")
    safety_category = fields.Selection(
        [   ('a', 'A'),
            ('b', 'B'),
            ('c', 'C'),
        ],
        string="Safety Category"
    )
    
    extinguisher_type = fields.Selection(
        [
            ('co2', 'CO2'),
            ('powder', 'Powder'),
            ('foam', 'Foam'),
            ('water', 'Water'),
        ],
        string="Extinguisher Type"
    )

    country_id = fields.Many2one(
        'res.country',
        string="Country"
    )

    life_span = fields.Integer(
        string="Life Span (Days)"
    )

    validity_date = fields.Date(
        string="Validity Date"
    )

    purchase_date = fields.Date(
        string="Purchase Date"
    )

    last_inspection_date = fields.Date(
        string="Last Inspection Date"
    )

    expiry_date = fields.Date(
        string="Expiry Date",
        compute="_compute_expiry_date",
        store=True
    )

    remaining_days = fields.Integer(
        string="Remaining Days",
        compute="_compute_remaining_days",
        store=True
    )
    
    safety_state = fields.Selection(
        [
            ('valid', 'Valid'),
            ('near', 'Near'),
            ('expired', 'Expired'),
        ],
        string="State",
        compute="_compute_safety_state",
        store=True
    )
 
    @api.depends('validity_date', 'life_span')
    def _compute_expiry_date(self):
        for rec in self:
            if rec.validity_date and rec.life_span:
                rec.expiry_date = rec.validity_date + timedelta(days=rec.life_span)
            else:
                rec.expiry_date = False
 
    @api.depends('expiry_date')
    def _compute_remaining_days(self):
        today = fields.Date.today()
        for rec in self:
            if rec.expiry_date:
                rec.remaining_days = (rec.expiry_date - today).days
            else:
                rec.remaining_days = 0
 
    @api.depends('remaining_days')
    def _compute_safety_state(self):
        for rec in self:
            if rec.remaining_days > 30:
                rec.safety_state = 'valid'
            elif 0 <= rec.remaining_days <= 30:
                rec.safety_state = 'near'
            else:
                rec.safety_state = 'expired'
 