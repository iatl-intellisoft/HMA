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

    loading_date = fields.Date(
        string='Loading Date',
        copy=False,
        tracking=True,
        help='Date the goods were loaded for shipment.',
    )
    shipment_date = fields.Date(
        string='Shipment Date',
        copy=False,
        tracking=True,
        help='Date the shipment departed.',
    )
    etd = fields.Date(
        string='ETD',
        copy=False,
        tracking=True,
        help='Estimated Time of Departure.',
    )
    eta = fields.Date(
        string='ETA',
        copy=False,
        tracking=True,
        help='Estimated Time of Arrival.',
    )
    shipping_line = fields.Char(
        string='Shipping Line',
        copy=False,
        tracking=True,
        help='Name of the shipping line / carrier handling this shipment.',
    )
