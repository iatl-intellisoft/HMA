# -*- coding: utf-8 -*-

from odoo import api, fields, models


class AccountMove(models.Model):
    _inherit = "account.move"

    payment_request_id = fields.Many2one(
        'payment.request', string="Payment Request", copy=False, )


class AccountMoveLine(models.Model):
    _inherit = 'account.move.line'

    payment_request_id = fields.Many2one(
        'payment.request', string="Payment Request", copy=False, )
