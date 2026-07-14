# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    approval_state = fields.Selection([
        ('no', 'لا يتطلب اعتماد'),
        ('to_approve', 'بانتظار الاعتماد'),
        ('approved', 'معتمد'),
    ], string='حالة الاعتماد', default='no', copy=False, tracking=True,
        help='تُستخدم فقط مع العملاء المباشرين الذين يتطلبون اعتماد مسؤول المبيعات '
             'قبل تحويل الطلب إلى أمر بيع.')

    approval_user_id = fields.Many2one(
        'res.users', string='تم الاعتماد بواسطة', copy=False, readonly=True)
    approval_date = fields.Datetime(
        string='تاريخ الاعتماد', copy=False, readonly=True)

    # ---------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------
    def _needs_sale_approval(self):
        """يرجع True إذا كان الطلب يخص عميل مباشر ولم يُعتمد بعد."""
        self.ensure_one()
        return bool(self.partner_id.requires_sale_approval) and self.approval_state != 'approved'

    # ---------------------------------------------------------
    # Create: وسم الطلب تلقائياً منذ إنشائه
    # ---------------------------------------------------------
    @api.model_create_multi
    def create(self, vals_list):
        orders = super().create(vals_list)
        for order in orders:
            if order.partner_id.requires_sale_approval and order.approval_state == 'no':
                order.approval_state = 'to_approve'
        return orders

    # ---------------------------------------------------------
    # عند تغيير العميل يدوياً على الطلب (مثلاً في حالة Draft)
    # ---------------------------------------------------------
    @api.onchange('partner_id')
    def _onchange_partner_id_sale_approval(self):
        for order in self:
            if order.partner_id and order.partner_id.requires_sale_approval:
                if order.approval_state == 'no':
                    order.approval_state = 'to_approve'
            elif order.partner_id:
                order.approval_state = 'no'

    # ---------------------------------------------------------
    # التأكيد: هنا التعديل الأساسي
    # ---------------------------------------------------------
    def action_confirm(self):
        """
        - العملاء العاديون: يمرون بنفس سلوك أودو الأصلي بدون أي تغيير.
        - العملاء المباشرون (requires_sale_approval) وغير معتمدين بعد:
          لا يتم استدعاء super() عليهم إطلاقاً (تجنباً لأي خطأ Invalid Operation
          ناتج عن تغيير حالة الطلب وهو غير مؤهل للتأكيد)، بل توضع حالتهم
          "بانتظار الاعتماد" ويظهر إشعار للمستخدم بدلاً من رسالة خطأ.
        """
        pending_orders = self.filtered(lambda o: o._needs_sale_approval())
        ready_orders = self - pending_orders

        for order in pending_orders:
            if order.approval_state != 'to_approve':
                order.approval_state = 'to_approve'
            order.message_post(
                body=_('تم إرسال الطلب لانتظار اعتماد مسؤول المبيعات قبل التأكيد.')
            )

        result = True
        if ready_orders:
            # نستدعي منطق أودو الأصلي فقط على الطلبات المؤهلة فعلاً للتأكيد
            result = super(SaleOrder, ready_orders).action_confirm()

        if pending_orders and not ready_orders:
            # كل الطلبات المحددة كانت بانتظار الاعتماد: نرجع إشعار بدل استثناء
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'title': _('بانتظار الاعتماد'),
                    'message': _('تم إرسال الطلب إلى مسؤول المبيعات لاعتماده. '
                                  'سيتحول تلقائياً إلى أمر بيع بعد الاعتماد.'),
                    'type': 'warning',
                    'sticky': False,
                }
            }
        return result

    # ---------------------------------------------------------
    # زر / أكشن الاعتماد الذي يستخدمه مسؤول المبيعات
    # ---------------------------------------------------------
    def action_approve_sale_order(self):
        approval_group = 'custom_sale_approval.group_sales_approval_manager'
        for order in self:
            if not order.env.user.has_group(approval_group):
                raise UserError(_('ليس لديك صلاحية اعتماد هذا الطلب. '
                                   'يرجى التواصل مع مسؤول المبيعات.'))
            if not order.partner_id.requires_sale_approval:
                raise UserError(_('هذا الطلب لا يخص عميلاً يتطلب اعتماداً.'))
            if order.approval_state == 'approved':
                continue

            order.write({
                'approval_state': 'approved',
                'approval_user_id': self.env.user.id,
                'approval_date': fields.Datetime.now(),
            })
            order.message_post(
                body=_('تم اعتماد الطلب بواسطة %s') % self.env.user.name
            )

        # بعد الاعتماد، نستدعي action_confirm من جديد
        # وبما أن approval_state أصبحت 'approved'، فإن _needs_sale_approval()
        # سترجع False وسيتم استدعاء super().action_confirm() بشكل طبيعي
        # مما يؤدي تلقائياً لإنشاء التسليم والفاتورة حسب إعدادات أودو القياسية.
        return self.action_confirm()

    # ---------------------------------------------------------
    # رفض الاعتماد (اختياري - إعادة الطلب لمسودة)
    # ---------------------------------------------------------
    def action_reject_sale_order(self):
        approval_group = 'custom_sale_approval.group_sales_approval_manager'
        for order in self:
            if not order.env.user.has_group(approval_group):
                raise UserError(_('ليس لديك صلاحية رفض هذا الطلب.'))
            order.write({'approval_state': 'to_approve'})
            order.message_post(body=_('تم رفض اعتماد الطلب وإعادته للمراجعة.'))
