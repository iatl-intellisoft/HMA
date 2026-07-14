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

    def _get_ops_report_groups(self):
        """Return ordered list of group dicts for the PDF template.

        Each group represents one table in the report:
        - pickings linked to the same SO **and** the same warehouse proximity
          → merged into one group
        - pickings with no SO → one group each

        Each group also carries 'proximity_type' ('near'/'far') taken from
        the warehouse of its picking type, so the template can split the
        report into a "Near Warehouses" section and a "Far Warehouses"
        section.
        """
        groups = []
        group_index = {}

        for p in self.picking_ids.sorted(lambda p: (p.sale_id.id or 0, p.name)):
            warehouse = p.picking_type_id.warehouse_id
            proximity = warehouse.proximity_type or 'near'

            group_data = {
                'partner_name': p.partner_id.name or '',
                'shipping_office': p.shipping_office_name or '',
                'shipping_office_no': p.shipping_office_number or '',
                'shipping_destination': p.shipping_destination.name or '',
                'stock_location': p.location_id.display_name or '',
                'proximity_type': proximity,
                'pickings': p,
            }

            if p.sale_id:
                # Same SO can still ship from both a near and a far warehouse,
                # so the group key includes proximity, not just the SO id.
                key = (p.sale_id.id, proximity)
                if key in group_index:
                    groups[group_index[key]]['pickings'] |= p
                    continue
                group_index[key] = len(groups)
                group_data['so_name'] = p.sale_id.name
            else:
                group_data['so_name'] = ''

            groups.append(group_data)

        return groups

    def _get_ops_report_sections(self):
        """Split the groups from _get_ops_report_groups() into two lists,
        ready for the template to render as two separate sections.
        """
        groups = self._get_ops_report_groups()
        return {
            'near': [g for g in groups if g['proximity_type'] == 'near'],
            'far': [g for g in groups if g['proximity_type'] == 'far'],
        }

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
