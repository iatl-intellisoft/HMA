from odoo import models, fields,api

class TruckOdometer(models.Model):
    _name = 'truck.odometer'
    _description = 'Truck Odometer'

    truck_id = fields.Many2one('fleet.vehicle', required=True)
    date = fields.Date(required=True)
    odometer = fields.Float(string="Odometer KM")
    source = fields.Selection([
        ('gps', 'GPS'),
        ('manual', 'Manual')
    ])
    distance = fields.Float(compute="_compute_distance")

    @api.depends('odometer','truck_id')
    def _compute_distance(self):
        for rec in self:
            prev = self.search([
                ('truck_id','=',rec.truck_id.id),
                ('date','<',rec.date)
            ], order="date desc", limit=1)

            if prev:
                rec.distance = rec.odometer - prev.odometer
            else:
                rec.distance = 0
    # fuel_efficiency = fields.Float(
    # string="KM/L",
    # compute="_compute_efficiency"
    # )

    # @api.depends('fuel_qty','distance')
    # def _compute_efficiency(self):
    #     for rec in self:
    #         if rec.fuel_qty and rec.distance:
    #             rec.fuel_efficiency = rec.distance / rec.fuel_qty
    #         else:
    #             rec.fuel_efficiency = 0