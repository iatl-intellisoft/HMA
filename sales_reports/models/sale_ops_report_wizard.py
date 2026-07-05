# -*- coding: utf-8 -*-

from datetime import timedelta
from odoo import models, fields, api, _


class SaleOpsReportWizard(models.TransientModel):
    _name = 'sale.ops.report.wizard'
    _description = 'Operations Report'

    date = fields.Date(string='Date')

    # ── Generation ────────────────────────────────────────────────────────────

    def action_generate(self):
        self.ensure_one()

        domain = [
            ('picking_type_code', '=', 'outgoing'),
            ('sale_id', '!=', False),
            ('state', 'not in', ['draft', 'cancel']),
        ]

        if self.date:
            # Filter to pickings whose scheduled date falls on the selected date
            date_start = fields.Datetime.to_datetime(self.date)
            date_end = date_start + timedelta(days=1)
            domain += [
                ('scheduled_date', '>=', date_start),
                ('scheduled_date', '<', date_end),
            ]

        pickings = self.env['stock.picking'].search(
            domain, order='scheduled_date asc, name asc'
        )

        # Clear any previously generated lines for this wizard session
        self.env['sale.ops.report.line'].search(
            [('wizard_id', '=', self.id)]
        ).unlink()

        line_vals = []
        for picking in pickings:
            valid_moves = picking.move_ids.filtered(
                lambda m: m.state != 'cancel' and m.product_id
            )
            if not valid_moves:
                continue

            demand = sum(valid_moves.mapped('product_uom_qty'))
            quantity = sum(valid_moves.mapped('quantity'))

            line_vals.append({
                'wizard_id': self.id,
                'picking_id': picking.id,
                'partner_id': picking.partner_id.id,
                'sale_order_ref': picking.sale_id.name or picking.origin or '',
                'shipping_office_name' : picking.shipping_office_name,
                'shipping_office_number' : picking.shipping_office_number,
                'shipping_distination' : picking.shipping_destination,
                'demand': demand,
                'quantity': quantity,
            })

        self.env['sale.ops.report.line'].create(line_vals)

        return {
            'type': 'ir.actions.act_window',
            'name': _('Operations Report'),
            'res_model': 'sale.ops.report.line',
            'view_mode': 'list',
            'views': [(False, 'list')],
            'domain': [('wizard_id', '=', self.id)],
            'target': 'current',
            'context': dict(
                self.env.context,
                create=False,
                edit=False,
                delete=False,
            ),
        }
