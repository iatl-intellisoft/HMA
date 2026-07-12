# -*- coding: utf-8 -*-
from odoo import fields, models, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'

    delivery_print_count = fields.Integer(
        string='عدد مرات طباعة إذن التوصيل',
        default=0,
        copy=False,
        readonly=True,
    )

    def action_print_delivery_once(self):
        """طباعة إذن التوصيل مرة واحدة فقط لكل عملية."""
        self.ensure_one()
        if self.delivery_print_count >= 1:
            raise UserError(_(
                'تم طباعة إذن التوصيل لهذه العملية من قبل، '
                'ولا يسمح بطباعته أكثر من مرة واحدة.'
            ))
        self.delivery_print_count += 1
        return self.env.ref('stock.action_report_delivery').report_action(self)
