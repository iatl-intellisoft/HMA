from odoo import models, fields

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    vehicle_id = fields.Many2one(
        'fleet.vehicle',
        string="Vehicle"
    )
    driver_id = fields.Many2one(
        'res.partner',
        string="Driver",
        related="vehicle_id.driver_id",
        store=True,
        readonly=True
    )
    plate_number = fields.Char(
        string="Plate Number",
        related="vehicle_id.license_plate",
        store=True,
        readonly=True
    )
