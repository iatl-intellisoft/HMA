# -*- coding: utf-8 -*-
from odoo import models, fields, api
from odoo.exceptions import UserError

from datetime import date 
import calendar 


class SudanVatReport(models.TransientModel):
    """
    Sudan Monthly VAT Declaration - Form 3
    الإقرار الشهري للضريبة على القيمة المضافة - أنموذج رقم (٣)
    """
    _name = 'sudan.vat.report'
    _description = 'Sudan Monthly VAT Declaration'

    # ── Declaration Period ──────────────────────────────────────────────────
    month = fields.Selection(
        selection=[
            ('1', 'يناير'), ('2', 'فبراير'), ('3', 'مارس'),
            ('4', 'أبريل'), ('5', 'مايو'), ('6', 'يونيو'),
            ('7', 'يوليو'), ('8', 'أغسطس'), ('9', 'سبتمبر'),
            ('10', 'أكتوبر'), ('11', 'نوفمبر'), ('12', 'ديسمبر'),
        ],
        string='الشهر',
        required=True,
        default=lambda self: str(fields.Date.today().month),
    )
    date_from=fields.Date(string="من تاريخ" , compute='_compute_dates',store=True)
    date_to=fields.Date(string="الى تاريخ" , compute='_compute_dates',store=True)
    year = fields.Char(
        string='السنة',
        required=True,
        default=lambda self: str(fields.Date.today().year),
    )
    @api.depends('year','month')
    def _compute_dates(self):
        for rec in self:
            if rec.month and rec.year:
                month_int = int(rec.month) 
                year_int = int(rec.year) 
                rec.date_from =date(year_int,month_int,1)
                last_day = calendar.monthrange(year_int,month_int)[1]
                rec.date_to =date(year_int,month_int,last_day)
            else :
                rec.date_from =False
                rec.date_to =False

    
    declaration_number = fields.Char(string='رقم الإقرار')

    # ── Taxpayer Information ────────────────────────────────────────────────
    company_id = fields.Many2one(
        'res.company',
        string='اسم المكلف',
        required=True,
        default=lambda self: self.env.company,
    )
    taxpayer_name = fields.Char(
        string='اسم المكلف',
        compute='_compute_company_info',
        store=True,
        readonly=False,
    )
    trade_name = fields.Char(
        string='الاسم التجاري',
        compute='_compute_company_info',
        store=True,
        readonly=False,
    )
    tax_registration_number = fields.Char(
        string='رقم التسجيل / الرقم التعريفي',
        compute='_compute_company_info',
        store=True,
        readonly=False,
    )
    activity_type = fields.Char(string='طبيعة النشاط')
    legal_entity = fields.Char(string='الكيان القانوني')
    address = fields.Char(
        string='العنوان',
        compute='_compute_company_info',
        store=True,
        readonly=False,
    )
    state_province = fields.Char(string='الولاية')
    locality = fields.Char(string='المحلية')
    admin_unit = fields.Char(string='الوحدة الإدارية')
    neighborhood = fields.Char(string='الحي')
    block = fields.Char(string='الفريع')
    quarter = fields.Char(string='الحارة')
    market = fields.Char(string='السوق')
    street = fields.Char(string='الشارع')
    floor = fields.Char(string='الطابق')
    building = fields.Char(string='المبنى')
    phone = fields.Char(string='الهواتف')
    mobile = fields.Char(string='الجوال')
    email = fields.Char(string='البريد الإلكتروني')
    specific_office = fields.Char(string='المكتب المختص')

    # ── Sales / Revenues Section ────────────────────────────────────────────
    # Row 1: Local goods & services (17%)
    sales_local_total = fields.Float(string='/١ السلع والخدمات والأعمال الخاصة - المبلغ الكلي', compute='_compute_sales_local_total', digits=(16, 2))
    sales_local_tax_rate = fields.Char(string='نسبة الضريبة', default='%17')
    sales_local_tax_amount = fields.Float(string='مقدار الضريبة', digits=(16, 2))
    sales_local_tax_total = fields.Float(string='جملة الضريبة', digits=(16, 2))

    @api.onchange('date_from','date_to')
    def _compute_sales_local_total(self):
        data = self.env['tax.invoice'].read_group(
                        domain=[
                            ('date', '>=', self.date_from),  
                            ('date', '<=', self.date_to)
                            ],
                        fields=['total_amount:sum'],
                        groupby=[]) 
        self.sales_local_total=data[0]['total_amount']
        
        data_purchase = self.env['purchase.order'].read_group(
                        domain=[
                            ('date', '>=', self.date_from),  
                            ('date', '<=', self.date_to)
                            ],
                        fields=['amount_total:sum'],
                        groupby=[]) 
        self.purchase_local_total=data_purchase[0]['amount_total']
    # Row 2: Telecommunications (30%)
    sales_telecom_total = fields.Float(string='/٢ الاتصالات - المبلغ الكلي', digits=(16, 2))
    sales_telecom_tax_rate = fields.Char(string='نسبة الضريبة', default='%٣٠')
    sales_telecom_tax_amount = fields.Float(string='مقدار الضريبة', digits=(16, 2))
    sales_telecom_tax_total = fields.Float(string='جملة الضريبة', digits=(16, 2))

    # Row 3: Fixed Assets (17%)
    sales_assets_total = fields.Float(string='/٣ الأصول الثابتة الخاصة - المبلغ الكلي', digits=(16, 2))
    sales_assets_tax_rate = fields.Char(string='نسبة الضريبة', default='%17')
    sales_assets_tax_amount = fields.Float(string='مقدار الضريبة', digits=(16, 2))
    sales_assets_tax_total = fields.Float(string='جملة الضريبة', digits=(16, 2))

    # Row 4: Local goods & special business (quantity/unit based)
    sales_special_basis_type = fields.Selection(
        [('percentage', 'نسبة / مبلغ'), ('quantity', 'مبلغ / كمية')],
        string='أساس التحاسب',
    )
    sales_special_tax_amount_unit = fields.Float(string='وعاء الضريبة مبلغ/كمية', digits=(16, 2))
    sales_special_tax_total = fields.Float(string='جملة الضريبة', digits=(16, 2))

    # Row 5: Exempt goods & services
    sales_exempt_total = fields.Float(string='/٥ السلع والخدمات المعفاة', digits=(16, 2))

    # Row 6: Exported goods & services
    sales_export_total = fields.Float(string='/٦ سلع وخدمات الصادر', digits=(16, 2))

    # Total sales tax collected this month
    total_sales_tax = fields.Float(
        string='إجمالي الضريبة المحصلة عن الشهر',
        compute='_compute_totals',
        store=True,
        digits=(16, 2),
    )

    # ── Purchases Section ───────────────────────────────────────────────────
    # Row 7: Imported purchases (17%)
    purchase_import_total = fields.Float(string='/٧ المستوردة - المبلغ الكلي', digits=(16, 2))
    purchase_import_tax_rate = fields.Char(string='نسبة الضريبة', default='%17')
    purchase_import_tax_amount = fields.Float(string='مقدار الضريبة', digits=(16, 2))
    purchase_import_tax_total = fields.Float(string='جملة الضريبة', digits=(16, 2))

    # Row 8: Local purchases (17%)
    purchase_local_total = fields.Float(string='/٨ المحلية - المبلغ الكلي', digits=(16, 2))
    purchase_local_tax_rate = fields.Char(string='نسبة الضريبة', default='%17')
    purchase_local_tax_amount = fields.Float(string='مقدار الضريبة', digits=(16, 2))
    purchase_local_tax_total = fields.Float(string='جملة الضريبة', digits=(16, 2))

    # Row 9: Fixed assets purchases (17%)
    purchase_assets_total = fields.Float(string='/٩ الأصول الثابتة - المبلغ الكلي', digits=(16, 2))
    purchase_assets_tax_rate = fields.Char(string='نسبة الضريبة', default='%17')
    purchase_assets_tax_amount = fields.Float(string='مقدار الضريبة', digits=(16, 2))
    purchase_assets_tax_total = fields.Float(string='جملة الضريبة', digits=(16, 2))

    # Row 10: Special local goods/services (quantity/unit based)
    purchase_special_basis_type = fields.Selection(
        [('percentage', 'نسبة / مبلغ'), ('quantity', 'مبلغ / كمية')],
        string='أساس التحاسب',
    )
    purchase_special_tax_amount_unit = fields.Float(string='وعاء الضريبة مبلغ/كمية', digits=(16, 2))
    purchase_special_tax_total = fields.Float(string='جملة الضريبة', digits=(16, 2))

    # ── Expenses & Services Section ─────────────────────────────────────────
    # Row 11: Telecommunications (30%)
    expense_telecom_total = fields.Float(string='/١١ الاتصالات - المبلغ الكلي', digits=(16, 2))
    expense_telecom_tax_rate = fields.Char(string='نسبة الضريبة', default='%٣٠')
    expense_telecom_tax_amount = fields.Float(string='مقدار الضريبة', digits=(16, 2))
    expense_telecom_tax_total = fields.Float(string='جملة الضريبة', digits=(16, 2))

    # Row 12: Other services (17%)
    expense_other_total = fields.Float(string='/١٢ أخرى - المبلغ الكلي', digits=(16, 2))
    expense_other_tax_rate = fields.Char(string='نسبة الضريبة', default='%17')
    expense_other_tax_amount = fields.Float(string='مقدار الضريبة', digits=(16, 2))
    expense_other_tax_total = fields.Float(string='جملة الضريبة', digits=(16, 2))

    # Row 13: Imported exempt
    expense_import_exempt_total = fields.Float(string='/١٣ المستوردة المعفاة', digits=(16, 2))

    # Row 14: Local exempt
    expense_local_exempt_total = fields.Float(string='/١٤ المحلية المعفاة', digits=(16, 2))

    # ── Summary / Reconciliation ────────────────────────────────────────────
    total_purchase_tax_paid = fields.Float(
        string='إجمالي الضريبة المدفوعة عن الشهر',
        compute='_compute_totals',
        store=True,
        digits=(16, 2),
    )
    monthly_net_tax = fields.Float(
        string='الضريبة عن الشهر (دائن / مدين)',
        compute='_compute_totals',
        store=True,
        digits=(16, 2),
    )

    # Carried forward balance
    carried_forward_balance = fields.Float(
        string='/١٥ رصيد الضريبة المرحل عن الشهر السابق',
        digits=(16, 2),
    )
    creditor_carried_balance = fields.Float(
        string='/١٦ رصيد الضريبة الدائن المرحل',
        compute='_compute_totals',
        store=True,
        digits=(16, 2),
    )
    debtor_payable_balance = fields.Float(
        string='/١٧ رصيد الضريبة المدين الواجب السداد',
        compute='_compute_totals',
        store=True,
        digits=(16, 2),
    )
    refund_amount = fields.Float(string='/١٨ الإسترداد', digits=(16, 2))
    petroleum_certificates = fields.Char(string='/١٩ شهادات شركات البترول')

    # ── Submitter Information ───────────────────────────────────────────────
    submitter_name = fields.Char(string='الاسم')
    submitter_role = fields.Selection(
        [('owner', 'صاحب النشاط'), ('authorized', 'مفوض')],
        string='بصفتي',
        default='authorized',
    )
    submission_date = fields.Date(string='التاريخ', default=fields.Date.today)

    # ────────────────────────────────────────────────────────────────────────
    # Computed Methods
    # ────────────────────────────────────────────────────────────────────────

    @api.depends('company_id')
    def _compute_company_info(self):
        for rec in self:
            company = rec.company_id
            rec.taxpayer_name = company.name
            rec.trade_name = company.name
            rec.tax_registration_number = company.vat or ''
            rec.address = ' '.join(filter(None, [
                company.street, company.city,
                company.state_id.name if company.state_id else '',
                company.country_id.name if company.country_id else '',
            ]))
            rec.phone = company.phone or ''
            rec.email = company.email or ''
            rec.mobile = company.mobile or ''

    @api.depends(
        'sales_local_tax_total', 'sales_telecom_tax_total',
        'sales_assets_tax_total', 'sales_special_tax_total',
        'purchase_import_tax_total', 'purchase_local_tax_total',
        'purchase_assets_tax_total', 'purchase_special_tax_total',
        'expense_telecom_tax_total', 'expense_other_tax_total',
        'carried_forward_balance',
    )
    def _compute_totals(self):
        for rec in self:
            rec.total_sales_tax = (
                rec.sales_local_tax_total
                + rec.sales_telecom_tax_total
                + rec.sales_assets_tax_total
                + rec.sales_special_tax_total
            )
            rec.total_purchase_tax_paid = (
                rec.purchase_import_tax_total
                + rec.purchase_local_tax_total
                + rec.purchase_assets_tax_total
                + rec.purchase_special_tax_total
                + rec.expense_telecom_tax_total
                + rec.expense_other_tax_total
            )
            net = rec.total_sales_tax - rec.total_purchase_tax_paid
            rec.monthly_net_tax = net

            # Carried forward from previous month
            if net >= 0:
                rec.debtor_payable_balance = max(0.0, net - rec.carried_forward_balance)
                rec.creditor_carried_balance = max(0.0, rec.carried_forward_balance - net)
            else:
                rec.creditor_carried_balance = abs(net) + rec.carried_forward_balance
                rec.debtor_payable_balance = 0.0

    @api.onchange('sales_local_total')
    def _onchange_sales_local(self):
        self.sales_local_tax_amount = self.sales_local_total * 0.17
        self.sales_local_tax_total = self.sales_local_tax_amount

    @api.onchange('sales_telecom_total')
    def _onchange_sales_telecom(self):
        self.sales_telecom_tax_amount = self.sales_telecom_total * 0.30
        self.sales_telecom_tax_total = self.sales_telecom_tax_amount

    @api.onchange('sales_assets_total')
    def _onchange_sales_assets(self):
        self.sales_assets_tax_amount = self.sales_assets_total * 0.17
        self.sales_assets_tax_total = self.sales_assets_tax_amount

    @api.onchange('purchase_import_total')
    def _onchange_purchase_import(self):
        self.purchase_import_tax_amount = self.purchase_import_total * 0.17
        self.purchase_import_tax_total = self.purchase_import_tax_amount

    @api.onchange('purchase_local_total')
    def _onchange_purchase_local(self):
        self.purchase_local_tax_amount = self.purchase_local_total * 0.17
        self.purchase_local_tax_total = self.purchase_local_tax_amount

    @api.onchange('purchase_assets_total')
    def _onchange_purchase_assets(self):
        self.purchase_assets_tax_amount = self.purchase_assets_total * 0.17
        self.purchase_assets_tax_total = self.purchase_assets_tax_amount

    @api.onchange('expense_telecom_total')
    def _onchange_expense_telecom(self):
        self.expense_telecom_tax_amount = self.expense_telecom_total * 0.30
        self.expense_telecom_tax_total = self.expense_telecom_tax_amount

    @api.onchange('expense_other_total')
    def _onchange_expense_other(self):
        self.expense_other_tax_amount = self.expense_other_total * 0.17
        self.expense_other_tax_total = self.expense_other_tax_amount

    def action_print_report(self):
        """Generate and print the VAT declaration report."""
        self.ensure_one()
        return self.env.ref(
            'sudan_vat_report.action_report_sudan_vat'
        ).report_action(self)
