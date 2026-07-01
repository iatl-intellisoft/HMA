# -*- coding: utf-8 -*-
from odoo import models, fields, api, _


class SaleOrder(models.Model):
    _inherit = 'sale.order'

    # نضيف حالة جديدة لدورة حياة أمر البيع: "بانتظار الدفع".
    # هذه الحالة وسيطة بين "مسودة" و "تم التأكيد (sale)"، وأودوو لا ينشئ
    # أمر توصيل إلا للأوردرات اللي وصلت فعلياً لحالة sale، فطالما الأوردر
    # واقف عند الحالة دي، من المستحيل يتعمل له توصيل.
    state = fields.Selection(
        selection_add=[
            ('pending_payment', 'بانتظار الدفع'),
        ],
        ondelete={'pending_payment': 'set default'},
    )

    def _has_received_payment(self):
        """يرجع True لو فيه أي فاتورة مرحّلة لأمر البيع عليها دفعية كاملة
        أو جزئية (بما فيها فاتورة دفعة مقدمة). بنقرا القيمة مباشرة من
        قاعدة البيانات (بعد invalidate) عشان نضمن إننا شايفين آخر قيمة
        محدّثة فعلياً، مش قيمة قديمة متخزنة في الكاش."""
        self.ensure_one()
        self.invoice_ids.invalidate_recordset(['payment_state'])
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
        """نقسّم الأوردرات: اللي محتاجة دفعة الأول (عميل مباشر بدون أي
        دفعية) بنوقفها عند حالة 'بانتظار الدفع' من غير ما ننادي تأكيد
        أودوو الحقيقي خالص. الباقي يتأكد بالطريقة الطبيعية 100% زي ما هي،
        فيتعمل له أمر توصيل بشكل طبيعي تماماً من غير أي تدخل من جانبنا."""
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
        """يُستدعى فور التأكد من وجود دفعية على فاتورة عميل مباشر وأوردره
        لسه في حالة 'بانتظار الدفع'. بنرجّع الأوردر لحالة 'مسودة' وبعدين
        بنادي دالة التأكيد الأصلية بتاعة أودوو (super) من غير أي تعديل،
        فيتأكد الأوردر وينشئ أمر التوصيل بشكل طبيعي 100% زي أي أوردر تاني."""
        orders = self.filtered(lambda o: o.state == 'pending_payment')
        if not orders:
            return
        orders.write({'state': 'draft'})
        super(SaleOrder, orders).action_confirm()

    def action_release_delivery_manually(self):
        """زر اختياري (لمستخدم صلاحية معينة) لتجاوز شرط الدفع وتأكيد
        الأوردر يدوياً حتى من غير دفعية."""
        self._release_blocked_delivery()

    def action_check_payment_now(self):
        """زر 'تحقق من الدفع الآن': يفحص فوراً لو الأوردر (وهو في حالة
        بانتظار الدفع) بقى عليه دفعية، ولو كده يطلق التوصيل على طول من
        غير انتظار الـ Cron. هذا الزر مستقل تماماً عن أي تفاصيل داخلية في
        أودوو، فهو أضمن وسيلة للتحقق الفوري."""
        for order in self:
            if order.state == 'pending_payment' and order._has_received_payment():
                order._release_blocked_delivery()
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }

    def action_open_down_payment_wizard(self):
        """يفتح المعالج القياسي بتاع أودوو لإنشاء فاتورة دفعة مقدمة،
        حتى لو الأوردر لسه في حالة 'بانتظار الدفع' (مش 'sale')."""
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

    @api.model
    def _cron_release_pending_payment_orders(self):
        """Scheduled Action: تجري بشكل دوري (كل دقيقة) وتفحص كل الأوردرات
        الواقفة في حالة 'بانتظار الدفع'، ولو لقت أي فاتورة عليها دفعية،
        تطلق التوصيل تلقائياً. هذه هي الوسيلة الضامنة 100%، لأنها لا
        تعتمد على أي hook أو override داخلي في أودوو ممكن يختلف بين نسخة
        وأخرى - هي بس بتقرا الحالة الحقيقية للفواتير من القاعدة."""
        pending_orders = self.search([('state', '=', 'pending_payment')])
        for order in pending_orders:
            if order._has_received_payment():
                order._release_blocked_delivery()
