# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'
 
    state = fields.Selection(
        selection_add=[
            ('pending_payment', 'بانتظار الدفع'),
        ],
        ondelete={'pending_payment': 'set default'},
    )

    def _has_received_payment(self):
 
        self.ensure_one()
        invoices = self.invoice_ids.filtered(
            lambda inv: inv.state == 'posted' and inv.move_type == 'out_invoice'
        )
        return any(
            inv.payment_state in ('partial', 'paid', 'in_payment')
            for inv in invoices
        )

    def _requires_payment_before_confirm(self):
        self.ensure_one()
        return self.partner_id.customer_type == 'direct' and not self._has_received_payment()

    def action_confirm(self): 
        orders_on_hold = self.filtered(
            lambda o: o.state in ('draft', 'sent') and o._requires_payment_before_confirm()
        )
        orders_to_confirm = self - orders_on_hold

        res = True
        if orders_to_confirm:
            res = super(SaleOrder, orders_to_confirm).action_confirm()

        if orders_on_hold:
            orders_on_hold.write({'state': 'pending_payment'})
            for order in orders_on_hold:
                order.message_post(
                    body=_(
                        'الأوردر في حالة "بانتظار الدفع": العميل "مباشر" ولم '
                        'يتم تسجيل أي دفعية على فاتورة بعد. لن يتم تأكيد '
                        'الأوردر فعلياً ولا إنشاء أمر توصيل له إلا بعد تسجيل '
                        'أول دفعية (عن طريق فاتورة دفعة مقدمة مثلاً).'
                    )
                )
        return res

    def _release_blocked_delivery(self): 
        orders = self.filtered(lambda o: o.state == 'pending_payment')
        if not orders:
            return
        orders.write({'state': 'draft'})
        super(SaleOrder, orders).action_confirm()

    def action_release_delivery_manually(self): 
        self._release_blocked_delivery()

    def action_open_down_payment_wizard(self): 
        self.ensure_one()
        action = self.env['ir.actions.act_window']._for_xml_id(
            'sale.action_view_sale_advance_payment_inv'
        )
        action['context'] = {
            'active_model': 'sale.order',
            'active_id': self.id,
            'active_ids': self.ids,
        }
        return action
