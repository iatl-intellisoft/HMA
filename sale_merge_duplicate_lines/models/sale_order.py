# -*- coding: utf-8 -*-

from odoo import models, api


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # ── Merge trigger: order-level write (new line added via form) ────────────

    def write(self, vals):
        result = super().write(vals)
        if 'order_line' in vals and not self.env.context.get('_merging_duplicate_lines'):
            self.with_context(_merging_duplicate_lines=True)._merge_duplicate_lines()
        return result

    # ── Core merge logic ──────────────────────────────────────────────────────

    def _merge_duplicate_lines(self):
        """Merge sale order lines that share the same product and unit of measure.

        When duplicates are found, the **first** line (lowest ID) is kept and
        the combined quantity of all subsequent duplicate lines is added to it.
        The duplicate lines are then deleted.

        Only operates on orders in ``draft`` or ``sent`` state so that
        confirmed orders (with linked stock moves) are never touched.
        """
        for order in self:
            if order.state not in ('draft', 'sent'):
                continue

            # Process lines in creation order (lowest id first)
            product_lines = order.order_line.filtered(
                lambda l: not l.display_type and l.product_id
            ).sorted('id')

            first_by_key = {}   # (product_id, uom_id) → first line record
            to_remove = self.env['sale.order.line']

            for line in product_lines:
                key = (line.product_id.id, line.product_uom.id)
                if key in first_by_key:
                    # Add this line's qty to the keeper and mark it for removal
                    first_by_key[key].with_context(
                        _merging_duplicate_lines=True
                    ).product_uom_qty += line.product_uom_qty
                    to_remove |= line
                else:
                    first_by_key[key] = line

            if to_remove:
                to_remove.unlink()


class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    # ── Merge trigger: line-level write (product changed on existing line) ────

    def write(self, vals):
        result = super().write(vals)
        if 'product_id' in vals and not self.env.context.get('_merging_duplicate_lines'):
            self.order_id.with_context(
                _merging_duplicate_lines=True
            )._merge_duplicate_lines()
        return result

    # ── Merge trigger: line created directly (programmatic or UI save) ────────

    @api.model_create_multi
    def create(self, vals_list):
        lines = super().create(vals_list)
        if not self.env.context.get('_merging_duplicate_lines'):
            lines.order_id.with_context(
                _merging_duplicate_lines=True
            )._merge_duplicate_lines()
        return lines
