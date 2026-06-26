# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

import time
from odoo.tools import parse_date, SQL


class Currency(models.Model):
    _inherit = 'res.currency'

    name = fields.Char(string='Currency', size=3, required=True, help="Currency Code (ISO 4217)", )
    sale_currency_rate = fields.Float(string="Sale Currency Rate", digits=(12, 6), change_default=True,
                                      compute='_compute_sale_current_rate')
    inverse_sale_rate = fields.Float(compute='_compute_sale_current_rate', digits=0, readonly=True,
                                     help='The currency of rate 1 to the rate of the currency.')
    sale_rate_string = fields.Char(compute='_compute_sale_current_rate')
    rate = fields.Float(compute='_compute_current_rate', string='Current Rate', digits=(12, 6),
                        help='The rate of the currency to the currency of rate 1.',
                        tracking=True)
    sale_rate_ids = fields.One2many('res.sale.currency.rate', 'currency_id', string='Sales Rates')
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company.root_id)
    is_sale_currency = fields.Boolean(string="Is Sale Currency", default=True)

    # This Method to get sale rate
    def _get_sale_rates(self, company, date):
        if not self.ids:
            return {}
        currency_query = self.env['res.currency']._where_calc([
            ('id', 'in', self.ids),
        ], active_test=False)
        currency_id = self.env['res.currency']._field_to_sql(currency_query.table, 'id')
        rate_query = self.env['res.sale.currency.rate']._search([
            ('name', '<=', date),
            ('company_id', 'in', (False, company.root_id.id)),
            ('currency_id', '=', currency_id),
        ], order='company_id.id, name DESC', limit=1)
        rate_fallback = self.env['res.sale.currency.rate']._search([
            ('company_id', 'in', (False, company.root_id.id)),
            ('currency_id', '=', currency_id),
        ], order='company_id.id, name ASC', limit=1)
        rate = self.env['res.sale.currency.rate']._field_to_sql(rate_query.table, 'sale_currency_rate')
        return dict(self.env.execute_query(currency_query.select(
            currency_id,
            SQL("COALESCE((%s), (%s), 1.0)", rate_query.select(rate), rate_fallback.select(rate))
        )))

    # Compute sale current rate
    @api.depends('sale_rate_ids.sale_currency_rate')
    @api.depends_context('to_currency', 'date', 'company', 'company_id')
    def _compute_sale_current_rate(self):
        date = self._context.get('date') or fields.Date.context_today(self)
        company = self.env['res.company'].browse(self._context.get('company_id')) or self.env.company
        to_currency = self.browse(self.env.context.get('to_currency')) or company.currency_id
        # the subquery selects the last rate before 'date' for the given currency/company
        currency_rates = (self + to_currency)._get_sale_rates(self.env.company, date)

        for currency in self:
            currency.sale_currency_rate = (currency_rates.get(currency.id) or 1.0) / currency_rates.get(to_currency.id)
            currency.inverse_sale_rate = 1 / currency.sale_currency_rate
            if currency != company.currency_id:
                currency.sale_rate_string = '1 %s = %.6f %s' % (to_currency.name, currency.sale_currency_rate, currency.name)
            else:
                currency.sale_rate_string = ''
            # return currency.sale_currency_rate

    # conversion sale rate from currency to another
    @api.model
    def _get_conversion_sale_rate(self, from_currency, to_currency, company, date):
        currency_rates = (from_currency + to_currency)._get_sale_rates(company, date)
        if to_currency:
            res = currency_rates.get(to_currency.id) / currency_rates.get(from_currency.id)
            return 1 / res

    def _convert_sale_rate(self, from_amount, to_currency, company=None, date=None,round=True):
        """Returns the converted amount of ``from_amount``` from the currency
           ``self`` to the currency ``to_currency`` for the given ``date`` and
           company.

           :param company: The company from which we retrieve the convertion rate
           :param date: The nearest date from which we retriev the conversion rate.
           :param round: Round the result or not
        """
        self, to_currency = self or to_currency, to_currency or self

        assert self, "convert amount from unknown currency"
        assert to_currency, "convert amount to unknown currency"
        assert company, "convert amount from unknown company"
        assert date, "convert amount from unknown date"
        # apply conversion rate
        if self == to_currency:
            to_amount = from_amount
        else:
            to_amount = from_amount * self._get_conversion_sale_rate(self, to_currency, company, date)
        # apply rounding
        return to_currency.round(to_amount) if round else to_amount

    def _convert(self, from_amount, to_currency, company=None, date=None,round=True):  # noqa: A002 builtin-argument-shadowing

        """
        """
        if 'sale' in self._context and self._context['sale'] == True:
            return self._convert_sale_rate(from_amount, to_currency, company, date, round=False)
        else:
            return super()._convert(from_amount, to_currency, company, date,round)


class SaleCurrencyRate(models.Model):
    _name = 'res.sale.currency.rate'
    _description = "Sales Currency Rate"
    _rec_names_search = ['name', 'sale_currency_rate']
    _order = "name desc"

    sale_currency_rate = fields.Float(string="Sale Currency Rate", digits=0,
                                      aggregator="avg", default=1.0)
    name = fields.Date(string='Date', required=True, index=True,
                       default=lambda self: fields.Date.today())
    currency_id = fields.Many2one('res.currency', string='Currency', readonly=True)
    company_id = fields.Many2one('res.company', string='Company',
                                 default=lambda self: self.env.company.root_id)
    company_rate = fields.Float(
        digits=0,
        compute="_compute_company_sale_rate",
        inverse="_inverse_company_rate",
        aggregator="avg",
        help="The currency of rate 1 to the rate of the currency.",
    )
    inverse_company_rate = fields.Float(
        digits=0,
        compute="_compute_inverse_company_rate",
        inverse="_inverse_inverse_company_rate",
        aggregator="avg",
        help="The rate of the currency to the currency of rate 1 ",
    )
    _sql_constraints = [
        ('unique_name_per_day', 'unique (name,currency_id,company_id)', 'Only one currency rate per day allowed!'),
        ('currency_rate_check', 'CHECK (sale_currency_rate>0)', 'The currency rate must be strictly positive.'),
    ]

    def _get_latest_rate(self):
        # Make sure 'name' is defined when creating a new rate.
        if not self.name:
            raise UserError(_("The name for the current sale rate is empty.\nPlease set it."))
        return self.currency_id.sale_rate_ids.sudo().filtered(lambda x: (
                x.sale_currency_rate
                and x.company_id == (self.company_id or self.env.company.root_id)
                and x.name < (self.name or fields.Date.today())
        )).sorted('name')[-1:]

    def _get_last_rates_for_companies(self, companies):
        return {
            company: company.sudo().currency_id.sale_rate_ids.filtered(lambda x: (
                    x.sale_currency_rate
                    and x.company_id == company or not x.company_id
            )).sorted('name')[-1:].sale_currency_rate or 1
            for company in companies
        }

    @api.depends('sale_currency_rate', 'name', 'currency_id', 'company_id',
                 'currency_id.sale_rate_ids.sale_currency_rate')
    @api.depends_context('company')
    def _compute_company_sale_rate(self):
        last_rate = self.env['res.sale.currency.rate']._get_last_rates_for_companies(
            self.company_id | self.env.company.root_id)
        for currency_rate in self:
            company = currency_rate.company_id or self.env.company.root_id
            currency_rate.company_rate = (
                                                 currency_rate.sale_currency_rate or currency_rate._get_latest_rate().sale_currency_rate or 1.0) / \
                                         last_rate[company]

    @api.onchange('company_rate')
    def _inverse_company_rate(self):
        last_rate = self.env['res.sale.currency.rate']._get_last_rates_for_companies(
            self.company_id | self.env.company.root_id)
        for currency_rate in self:
            company = currency_rate.company_id or self.env.company.root_id
            currency_rate.sale_currency_rate = currency_rate.company_rate * last_rate[company]

    @api.depends('company_rate')
    def _compute_inverse_company_rate(self):
        for currency_rate in self:
            if not currency_rate.company_rate:
                currency_rate.company_rate = 1.0
            currency_rate.inverse_company_rate = 1.0 / currency_rate.company_rate

    @api.onchange('inverse_company_rate')
    def _inverse_inverse_company_rate(self):
        for currency_rate in self:
            if not currency_rate.inverse_company_rate:
                currency_rate.inverse_company_rate = 1.0
            currency_rate.company_rate = 1.0 / currency_rate.inverse_company_rate

    @api.onchange('company_rate')
    def _onchange_rate_warning(self):
        latest_rate = self._get_latest_rate()
        if latest_rate:
            diff = (latest_rate.sale_currency_rate - self.sale_currency_rate) / latest_rate.sale_currency_rate
            if abs(diff) > 0.2:
                return {
                    'warning': {
                        'title': _("Warning for %s", self.currency_id.name),
                        'message': _(
                            "The new rate is quite far from the previous rate.\n"
                            "Incorrect currency rates may cause critical problems, make sure the rate is correct!"
                        )
                    }
                }

    @api.constrains('company_id')
    def _check_company_id(self):
        for rate in self:
            if rate.company_id.sudo().parent_id:
                raise ValidationError("Sale Currency rates should only be created for main companies")

    @api.model
    def _search_display_name(self, operator, value):
        value = parse_date(self.env, value)
        return super()._search_display_name(operator, value)

    @api.model
    def _get_view_cache_key(self, view_id=None, view_type='form', **options):
        """The override of _get_view changing the rate field labels according to the company currency
        makes the view cache dependent on the company currency"""
        key = super()._get_view_cache_key(view_id, view_type, **options)
        return key + (
            (self.env['res.company'].browse(self._context.get('company_id')) or self.env.company).currency_id.name,)

    @api.model
    def _get_view(self, view_id=None, view_type='form', **options):
        arch, view = super()._get_view(view_id, view_type, **options)
        if view_type == 'list':
            names = {
                'company_currency_name': (self.env['res.company'].browse(
                    self._context.get('company_id')) or self.env.company).currency_id.name,
                'rate_currency_name': self.env['res.currency'].browse(self._context.get('active_id')).name or 'Unit',
            }
            for name, label in [['company_rate', _('%(rate_currency_name)s per %(company_currency_name)s', **names)],
                                ['inverse_company_rate',
                                 _('%(company_currency_name)s per %(rate_currency_name)s', **names)]]:

                if (node := arch.find(f"./field[@name='{name}']")) is not None:
                    node.set('string', label)
        return arch, view

    # Add rate in name search
    # @api.model
    # def _name_search(self, name, args=None, operator='ilike', limit=100, name_get_uid=None):
    #     if operator in ['=', '!=']:
    #         try:
    #             date_format = '%Y-%m-%d'
    #             if self._context.get('lang'):
    #                 lang_id = self.env['res.lang'].search([('code', '=', self._context['lang'])],
    #                                                       access_rights_uid=name_get_uid)
    #                 if lang_id:
    #                     date_format = self.browse(lang_id).date_format
    #             name = time.strftime('%Y-%m-%d', time.strptime(name, date_format))
    #         except ValueError:
    #             try:
    #                 args.append(('rate', operator, float(name)))
    #             except ValueError:
    #                 return []
    #             name = ''
    #             operator = 'ilike'
    #     return super(SaleCurrencyRate, self).search(name, args=args, operator=operator,
    #                                                 limit=limit, name_get_uid=name_get_uid)
