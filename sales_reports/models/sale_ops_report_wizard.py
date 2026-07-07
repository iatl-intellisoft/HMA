# -*- coding: utf-8 -*-

from datetime import timedelta
from odoo import models, fields, api, _


class SaleOpsReportWizard(models.TransientModel):
    _name = 'sale.ops.report.wizard'
    _description = 'Operations Report'

    date = fields.Date(string='Date')

    # Pickings collected by action_print_pdf — stored in DB so the QWeb
    # template can read them directly (avoids JSON round-trip via client)
    picking_ids = fields.Many2many(
        'stock.picking',
        'sale_ops_wizard_picking_rel',
        'wizard_id', 'picking_id',
        string='Deliveries',
    )

    # ── PDF print ─────────────────────────────────────────────────────────────

    def action_print_pdf(self):
        self.ensure_one()

        domain = [
            ('picking_type_code', '=', 'outgoing'),
            ('state', '=', 'done'),
        ]

        if self.date:
            date_start = fields.Datetime.to_datetime(self.date)
            date_end = date_start + timedelta(days=1)
            domain += [
                ('date_done', '>=', date_start),
                ('date_done', '<', date_end),
            ]

        pickings = self.env['stock.picking'].search(domain, order='sale_id, name')

        # Store on the wizard record so the template can access them without
        # relying on client-side data passing
        self.picking_ids = pickings

        return self.env.ref('sales_reports.action_sale_ops_report_pdf').report_action(self)

    def _get_ops_report_groups(self):
        """Return ordered list of group dicts for the PDF template.

        Each group represents one table in the report:
        - pickings linked to the same SO → merged into one group
        - pickings with no SO → one group each
        """
        groups = []
        so_index = {}

        for p in self.picking_ids.sorted(lambda p: (p.sale_id.id or 0, p.name)):
            if p.sale_id:
                so_id = p.sale_id.id
                if so_id in so_index:
                    groups[so_index[so_id]]['pickings'] |= p
                else:
                    so_index[so_id] = len(groups)
                    groups.append({
                        'so_name': p.sale_id.name,
                        'partner_name': p.partner_id.name or '',
                        'shipping_office': p.shipping_office_name or '',
                        'shipping_office_no': p.shipping_office_number or '',
                        'shipping_destination': p.shipping_destination.name or '',
                        'stock_location': p.location_id.display_name or '',
                        'pickings': p,
                    })
            else:
                groups.append({
                    'so_name': '',
                    'partner_name': p.partner_id.name or '',
                    'shipping_office': p.shipping_office_name or '',
                    'shipping_office_no': p.shipping_office_number or '',
                    'shipping_destination': p.shipping_destination.name or '',
                    'stock_location': p.location_id.display_name or '',
                    'pickings': p,
                })

        return groups

    # ── List-view generation (kept for quick on-screen review) ───────────────

    def action_generate(self):
        self.ensure_one()

        domain = [
            ('picking_type_code', '=', 'outgoing'),
            ('state', '=', 'done'),
        ]

        if self.date:
            date_start = fields.Datetime.to_datetime(self.date)
            date_end = date_start + timedelta(days=1)
            domain += [
                ('date_done', '>=', date_start),
                ('date_done', '<', date_end),
            ]

        pickings = self.env['stock.picking'].search(
            domain, order='date_done asc, name asc'
        )

        self.env['sale.ops.report.line'].search(
            [('wizard_id', '=', self.id)]
        ).unlink()

        line_vals = []
        for picking in pickings:
            valid_moves = picking.move_ids.filtered(
                lambda m: m.state == 'done' and m.product_id
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
