# -*- coding: utf-8 -*-
from collections import OrderedDict

from odoo import models


class ReportSalesSummary(models.AbstractModel):
    """يجهّز بيانات التقرير مجمعة حسب أمر البيع: كل أمر بيع وتحته فواتيره،
    وتحت كل فاتورة تفاصيل الأصناف الخاصة بيها."""

    _name = 'report.sales_report_by_period.report_sales_summary_document'
    _description = 'بيانات تقرير مبيعات الأصناف مجمعة حسب أمر البيع'

    def _get_report_values(self, docids, data=None):
        moves = self.env['account.move'].browse(docids)

        # نحافظ على ترتيب أول ظهور لأمر البيع زي ما جاي من البحث (بالتاريخ)
        orders_map = OrderedDict()
        NO_ORDER_KEY = '_no_order_'

        for move in moves:
            sale_orders = move.invoice_line_ids.sale_line_ids.order_id
            if sale_orders:
                for order in sale_orders:
                    entry = orders_map.setdefault(order.id, {
                        'order': order,
                        'moves': self.env['account.move'],
                    })
                    entry['moves'] |= move
            else:
                # فاتورة مش مرتبطة بأي أمر بيع (مثلاً فاتورة يدوية)
                entry = orders_map.setdefault(NO_ORDER_KEY, {
                    'order': False,
                    'moves': self.env['account.move'],
                })
                entry['moves'] |= move

        orders_data = []
        for entry in orders_map.values():
            entry_moves = entry['moves'].sorted(
                key=lambda m: (m.invoice_date or m.date, m.name)
            )
            orders_data.append({
                'order': entry['order'],
                'moves': entry_moves,
            })

        return {
            'doc_ids': docids,
            'doc_model': 'account.move',
            'docs': moves,
            'orders_data': orders_data,
            'data': data,
        }
