# -*- coding: utf-8 -*-

from odoo import models, fields, api
from odoo.osv import expression
from odoo.tools import DEFAULT_SERVER_DATETIME_FORMAT, float_compare
from itertools import groupby


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_user_warehouse(env):
    """Return the default warehouse for the current user, or False.

    Only applies when the user is an Inventory User (not a manager).
    Superusers are always excluded so internal operations keep working.
    """
    user = env.user
    if (
        not env.su
        and user.has_group('stock.group_stock_user')
        and not user.has_group('stock.group_stock_manager')
        and user.property_warehouse_id
    ):
        return user.property_warehouse_id
    return False


# ---------------------------------------------------------------------------
# Sale order line — per-line warehouse
# ---------------------------------------------------------------------------

class SaleOrderLine(models.Model):
    _inherit = 'sale.order.line'

    warehouse_id = fields.Many2one(
        'stock.warehouse',
        compute='_compute_warehouse_id',
        store=True,
        readonly=False,
    )

    @api.depends('route_id', 'order_id.warehouse_id', 'product_packaging_id', 'product_id')
    def _compute_warehouse_id(self):
        """Override to preserve manually set warehouses on existing lines.

        The standard compute always overwrites warehouse_id from the order or route.
        This override skips recomputation for saved lines that already have a warehouse
        assigned, so that per-line warehouse selections survive dependency changes
        (e.g. product changes, order confirmation, etc.).
        """
        lines_to_compute = self.filtered(lambda l: not l.id or not l.warehouse_id)
        lines_to_preserve = self - lines_to_compute

        # Explicitly write the current DB value back into the cache so Odoo
        # does not treat the field as "unset" for these lines after the compute.
        for line in lines_to_preserve:
            line.warehouse_id = line.warehouse_id

        super(SaleOrderLine, lines_to_compute)._compute_warehouse_id()

    def _prepare_procurement_values(self, group_id):
        res = super()._prepare_procurement_values(group_id=group_id)
        res.update({"warehouse_id": self.warehouse_id})
        return res


# ---------------------------------------------------------------------------
# Stock picking — warehouse-scoped visibility
# ---------------------------------------------------------------------------

class StockPicking(models.Model):
    _inherit = 'stock.picking'

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        """Restrict visible pickings to the user's default warehouse.

        When an Inventory User (not a manager) has a default warehouse set on
        their profile, apply the following rules:
        - Receipts & deliveries: only show pickings whose operation type
          belongs to the user's warehouse.
        - Internal transfers: only show pickings where the source OR the
          destination location belongs to the user's warehouse.

        Inventory Managers, superusers, and users without a default warehouse
        are not affected and continue to see all pickings.
        """
        wh = _get_user_warehouse(self.env)
        if wh:
            warehouse_domain = [
                '|',
                # Receipts / deliveries — filter by the picking type's warehouse
                '&', ('picking_type_id.code', '!=', 'internal'),
                     ('picking_type_id.warehouse_id', '=', wh.id),
                # Internal transfers — source OR destination within this warehouse
                '&', ('picking_type_id.code', '=', 'internal'),
                     '|', ('location_id.warehouse_id', '=', wh.id),
                          ('location_dest_id.warehouse_id', '=', wh.id),
            ]
            domain = expression.AND([domain, warehouse_domain])
        return super()._search(domain, offset=offset, limit=limit, order=order)


# ---------------------------------------------------------------------------
# Stock picking type — warehouse-scoped visibility
# ---------------------------------------------------------------------------

class StockPickingType(models.Model):
    _inherit = 'stock.picking.type'

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        """Restrict visible operation types to the user's default warehouse.

        Inventory Users with a default warehouse only see operation types that
        belong to that warehouse. Managers and users without a warehouse see all.
        """
        wh = _get_user_warehouse(self.env)
        if wh:
            domain = expression.AND([domain, [('warehouse_id', '=', wh.id)]])
        return super()._search(domain, offset=offset, limit=limit, order=order)


# ---------------------------------------------------------------------------
# Stock location — warehouse-scoped visibility
# ---------------------------------------------------------------------------

class StockLocation(models.Model):
    _inherit = 'stock.location'

    @api.model
    def _search(self, domain, offset=0, limit=None, order=None):
        """Restrict visible internal locations to the user's default warehouse.

        Inventory Users with a default warehouse only see internal locations
        that belong to that warehouse. All other location types (customer,
        supplier, transit, view, virtual, etc.) remain fully visible so that
        receipts and deliveries can still reference partner/virtual locations.

        Managers and users without a default warehouse see all locations.
        """
        wh = _get_user_warehouse(self.env)
        if wh:
            warehouse_domain = [
                '|',
                # Non-internal locations are always visible (partner, virtual, …)
                ('usage', '!=', 'internal'),
                # Internal locations: restrict to the user's warehouse
                ('warehouse_id', '=', wh.id),
            ]
            domain = expression.AND([domain, warehouse_domain])
        return super()._search(domain, offset=offset, limit=limit, order=order)


# ---------------------------------------------------------------------------
# Stock warehouse — display name with on-hand qty
# ---------------------------------------------------------------------------

class StockWarehouse(models.Model):
    _inherit = 'stock.warehouse'

    @api.depends('name', 'code')
    def _compute_display_name(self):
        product_id = self.env.context.get('sale_line_product_id')
        if not product_id:
            return super()._compute_display_name()
        product = self.env['product.product'].browse(product_id)
        for wh in self:
            qty = product.with_context(location=wh.lot_stock_id.id).qty_available
            wh.display_name = '%s - %g qty' % (wh.name, qty)
