# -*- coding: utf-8 -*-

from datetime import timedelta
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class SaleOpsReportWizard(models.TransientModel):
    _name = 'sale.ops.report.wizard'
    _description = 'Operations Report'

    date_from = fields.Date(string='Start Date')
    date_to = fields.Date(string='End Date')

    # Pickings collected by action_print_pdf — stored in DB so the QWeb
    # template can read them directly (avoids JSON round-trip via client)
    picking_ids = fields.Many2many(
        'stock.picking',
        'sale_ops_wizard_picking_rel',
        'wizard_id', 'picking_id',
        string='Deliveries',
    )

    # ── Shared helpers ───────────────────────────────────────────────────────

    def _check_period(self):
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValidationError(_("Start Date cannot be after End Date."))

    def _get_pickings_domain(self):
        domain = [
            ('picking_type_code', '=', 'outgoing'),
            ('state', '=', 'done'),
        ]

        if self.date_from:
            date_start = fields.Datetime.to_datetime(self.date_from)
            domain.append(('date_done', '>=', date_start))
        if self.date_to:
            # date_to is inclusive of the whole day, so bound is start of next day
            date_end = fields.Datetime.to_datetime(self.date_to) + timedelta(days=1)
            domain.append(('date_done', '<', date_end))

        return domain

    # ── PDF print ─────────────────────────────────────────────────────────────

    def action_print_pdf(self):
        self.ensure_one()
        self._check_period()

        pickings = self.env['stock.picking'].search(
            self._get_pickings_domain(), order='sale_id, name'
        )

        # Store on the wizard record so the template can access them without
        # relying on client-side data passing
        self.picking_ids = pickings

        return self.env.ref('sales_reports.action_sale_ops_report_pdf').report_action(self)

    def _get_ops_report_order_groups(self):
        """Return ordered list of "order block" dicts for the PDF template.

        Each block represents one customer/sale-order:
        - pickings with no SO are treated as their own standalone block
        - inside each block, pickings are split into 'near_pickings' and
          'far_pickings' (recordsets) based on the proximity_type of their
          warehouse, so the template can print, per order:
              1) all near-warehouse deliveries together
              2) then all far-warehouse deliveries together
        """
        orders = []
        order_index = {}

        for p in self.picking_ids.sorted(lambda p: (p.sale_id.id or 0, p.name)):
            proximity = p.picking_type_id.warehouse_id.proximity_type or 'near'
            key = p.sale_id.id or ('picking', p.id)

            if key not in order_index:
                order_index[key] = len(orders)
                orders.append({
                    'so_name': p.sale_id.name or '',
                    'partner_name': p.partner_id.name or '',
                    'shipping_office': p.shipping_office_name or '',
                    'shipping_office_no': p.shipping_office_number or '',
                    'shipping_destination': p.shipping_destination.name or '',
                    'near_pickings': self.env['stock.picking'],
                    'far_pickings': self.env['stock.picking'],
                })

            order = orders[order_index[key]]
            if proximity == 'far':
                order['far_pickings'] |= p
            else:
                order['near_pickings'] |= p

        return orders

    # ── List-view generation (kept for quick on-screen review) ───────────────

    def action_generate(self):
        self.ensure_one()
        self._check_period()

        pickings = self.env['stock.picking'].search(
            self._get_pickings_domain(), order='date_done asc, name asc'
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
