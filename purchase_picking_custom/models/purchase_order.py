# -*- coding: utf-8 -*-
from odoo import models, fields


class PurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    shipment_status = fields.Selection(
        selection=[
            ('under_preparation', 'Under Preparation'),
            ('loaded', 'Loaded'),
            ('in_transit', 'In Transit'),
            ('arrived_at_port', 'Arrived at Port'),
            ('under_clearance', 'Under Clearance'),
            ('received', 'Received'),
        ],
        string='Shipment Status',
        copy=False,
        tracking=True,
        help='Tracks the shipment/import status of the goods for this purchase order.',
    )
