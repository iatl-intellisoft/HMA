# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class StockPicking(models.Model):
    _inherit = 'stock.picking'
    
    state = fields.Selection(
        selection_add=[
            ('under_manufacturing', 'تحت التصنيع'),
            ('under_shipping', 'تحت الشحن'),
        ],
        ondelete={
            'under_manufacturing': 'set default',
            'under_shipping': 'set default',
        },
    )

    state_display = fields.Char(
        string='State Label',
        compute='_compute_state_display',
        store=False,
    )

    @api.depends('state', 'picking_type_code')
    def _compute_state_display(self):
        state_labels = {
            'draft': _('Draft'),
            'waiting': _('Waiting Another Operation'),
            'confirmed': _('Waiting'),
            'assigned': _('Ready'),
            'done': _('Done'),
            'cancel': _('Cancelled'),
        }
        for picking in self:
            label = state_labels.get(picking.state, picking.state)
            if picking.picking_type_code == 'incoming' and picking.state == 'done':
                label = 'تم الاستلام'
            picking.state_display = label

    # Custom state field — extends the standard selection
    custom_state = fields.Selection(
        selection=[
            ('under_manufacturing', 'تحت التصنيع'),
            ('under_shipping', 'تحت الشحن'),
        ],
        string='Custom State',
        copy=False,
        index=True,
        tracking=True,
    )

    # New fields on picking
    bill_of_lading_number = fields.Char(
        string='رقم بوليصة الشحن',
        copy=False,
        tracking=True,
    )
    number_of_containers = fields.Integer(
        string='عدد الحاويات',
        copy=False,
        tracking=True,
    )

    # Helper computed field to know if this picking is a receipt
    is_receipt = fields.Boolean(
        string='Is Receipt',
        compute='_compute_is_receipt',
        store=False,
    )

    @api.depends('picking_type_code')
    def _compute_is_receipt(self):
        for picking in self:
            picking.is_receipt = picking.picking_type_code == 'incoming'

    def action_set_under_manufacturing(self):
        for picking in self:
            if picking.picking_type_code != 'incoming':
                raise UserError('يمكن تطبيق الحالة على عمليات الاستلام فقط.')
            if picking.state == 'cancel':
                raise UserError('لا يمكن تغيير حالة عملية ملغاة.')
    
            picking.state = 'under_manufacturing'


    def action_set_under_shipping(self):
        for picking in self:
            if picking.picking_type_code != 'incoming':
                raise UserError('يمكن تطبيق الحالة على عمليات الاستلام فقط.')
            if picking.state == 'cancel':
                raise UserError('لا يمكن تغيير حالة عملية ملغاة.')
    
            picking.state = 'under_shipping'

    def action_set_under_shipping(self):
        """Set custom state to Under Shipping (Receipt operations only)."""
        for picking in self:
            if picking.picking_type_code != 'incoming':
                raise UserError(
                    _('يمكن تطبيق حالة "تحت الشحن" على عمليات الاستلام فقط.')
                )
            if picking.state == 'cancel':
                raise UserError(
                    _('لا يمكن تغيير حالة عملية ملغاة.')
                )
            picking.custom_state = 'under_shipping'

    def action_reset_custom_state(self):
        """Reset custom state."""
        for picking in self:
            picking.custom_state = False

    def _get_custom_state_label(self):
        """Return display label for the current custom_state."""
        self.ensure_one()
        labels = {
            'under_manufacturing': 'تحت التصنيع',
            'under_shipping': 'تحت الشحن',
        }
        return labels.get(self.custom_state, '')
