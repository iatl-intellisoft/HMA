# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class SaleOrder(models.Model):
    _inherit = 'sale.order' 
    state = fields.Selection(
        selection_add=[
            ('pending_approval', 'بانتظار اعتماد المبيعات'),
        ],
        ondelete={'pending_approval': 'set default'},
    )

    can_approve_order = fields.Boolean(
        string='يمكنه الاعتماد',
        compute='_compute_can_approve_order',
    )

    @api.depends('company_id.sale_approval_user_id')
    def _compute_can_approve_order(self):
        for order in self:
            approver = order.company_id.sale_approval_user_id
            order.can_approve_order = (
                bool(approver) and order.env.user.id == approver.id
            ) or order.env.user.has_group('base.group_system')

    def _requires_sales_approval(self):
        self.ensure_one()
        return self.partner_id.customer_type == 'approved'

    def action_confirm(self): 
        orders_on_hold = self.filtered(
            lambda o: o.state in ('draft', 'sent') and o._requires_sales_approval()
        )
        orders_to_confirm = self - orders_on_hold

        res = True
        if orders_to_confirm:
            res = super(SaleOrder, orders_to_confirm).action_confirm()

        if orders_on_hold:
            orders_on_hold.write({'state': 'pending_approval'})
            for order in orders_on_hold:
                order._notify_sales_approver()
        return res

    def _notify_sales_approver(self):
        self.ensure_one()
        approver = self.company_id.sale_approval_user_id
        if not approver:
            self.message_post(
                body=_(
                    'الأوردر بانتظار اعتماد المبيعات، لكن لم يتم تحديد '
                    '"مسؤول اعتماد المبيعات" في إعدادات المبيعات. يرجى '
                    'إعداده أولاً حتى يصل الإشعار للشخص المناسب.'
                )
            )
            return
 
        self.activity_schedule(
            'mail.mail_activity_data_todo',
            user_id=approver.id,
            summary=_('اعتماد أمر بيع لعميل معتمد'),
            note=_(
                'أمر البيع %(name)s للعميل "%(partner)s" بانتظار اعتمادك '
                'قبل إنشاء أمر التوصيل الخاص به.',
                name=self.name, partner=self.partner_id.display_name,
            ),
        )
 
        self.message_post(
            body=_(
                'أمر البيع بانتظار اعتماد المبيعات من %(user)s.',
                user=approver.display_name,
            ),
            partner_ids=[approver.partner_id.id],
        )

    def action_approve_sales_order(self): 
        return self._do_approve_sales_order()

    def _do_approve_sales_order(self):
        orders = self.filtered(lambda o: o.state == 'pending_approval')
        if not orders:
            return True
        for order in orders:
            if not order.can_approve_order:
                raise UserError(_(
                    'غير مصرح لك باعتماد هذا الأوردر. الاعتماد متاح فقط '
                    'لمسؤول اعتماد المبيعات المحدد في الإعدادات.'
                ))
        orders.write({'state': 'draft'})
        super(SaleOrder, orders).action_confirm()
        for order in orders:
            order.message_post(
                body=_('تم اعتماد أمر البيع بواسطة %s.', self.env.user.display_name)
            )
        return True

    def _create_invoices(self, grouped=False, final=False, date=None):
        for order in self:
            if order.partner_id.customer_type != 'approved':
                continue
            if not any(line.qty_delivered > 0 for line in order.order_line):
                raise UserError(_(
                    'لا يمكن إصدار فاتورة لهذا الأوردر الآن.\n\n'
                    'العميل "%(partner)s" من نوع "عميل معتمد"، وسياسة الفوترة '
                    'لديه تكون حسب الكميات التي تم توصيلها فعلياً وليس '
                    'الكميات المطلوبة.\n\n'
                    'يرجى أولاً تنفيذ وتأكيد أمر التوصيل (Delivery) الخاص '
                    'بالأوردر، ثم إصدار الفاتورة بعد ذلك.',
                    partner=order.partner_id.display_name,
                ))
        return super()._create_invoices(grouped=grouped, final=final, date=date)

    def action_reject_sales_order(self):
        for order in self:
            if order.state != 'pending_approval':
                continue
            if not order.can_approve_order:
                raise UserError(_(
                    'غير مصرح لك برفض هذا الأوردر. هذا الإجراء متاح فقط '
                    'لمسؤول اعتماد المبيعات المحدد في الإعدادات.'
                ))
        self.filtered(lambda o: o.state == 'pending_approval').write({'state': 'draft'})
        for order in self:
            order.message_post(
                body=_('تم رفض اعتماد أمر البيع بواسطة %s وإرجاعه لحالة مسودة.',
                       self.env.user.display_name)
            )
