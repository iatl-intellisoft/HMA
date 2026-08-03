from odoo import models, fields, api
from odoo.exceptions import ValidationError


class CustomCurrencyRate(models.Model):
    _name = 'custom.currency.rate'
    _description = 'Custom Currency Conversion Rate'
    _order = 'from_currency_id, to_currency_id'

    from_currency_id = fields.Many2one(
        'res.currency',
        string='From Currency',
        required=True,
        ondelete='cascade',
    )
    to_currency_id = fields.Many2one(
        'res.currency',
        string='To Currency',
        required=True,
        ondelete='cascade',
    )
    rate = fields.Float(
        string='To Currency per Unit',
        required=True,
        digits=(16, 12),
        help='Example: AED → SDG = 700 means 1 AED = 700 SDG.',
    )
    inverse_rate = fields.Float(
        string='Unit per To Currency',
        compute='_compute_inverse_rate',
        inverse='_inverse_inverse_rate',
        digits=(16, 12),
        help='Inverse of the rate. Example: 0.00142857 means 1 SDG = 0.00142857 AED.',
    )
    effective_date = fields.Date(
        string="Effective Date",
        required=True,
        default=fields.Date.context_today,
        help="Rate is applicable from this date."
    )
    active = fields.Boolean(default=True)
    note = fields.Char(string='Note')

    _sql_constraints = [
        (
            'unique_currency_pair_date',
            'UNIQUE(from_currency_id, to_currency_id, effective_date)',
            'A rate for this currency pair already exists for the selected date.',
        )
    ]

    @api.depends('rate')
    def _compute_inverse_rate(self):
        for rec in self:
            rec.inverse_rate = 1.0 / rec.rate if rec.rate else 0.0

    def _inverse_inverse_rate(self):
        for rec in self:
            if rec.inverse_rate:
                rec.rate = 1.0 / rec.inverse_rate

    @api.constrains('from_currency_id', 'to_currency_id')
    def _check_different_currencies(self):
        for rec in self:
            if rec.from_currency_id == rec.to_currency_id:
                raise ValidationError(
                    'From Currency and To Currency must be different.'
                )

    @api.constrains('rate')
    def _check_rate_positive(self):
        for rec in self:
            if rec.rate <= 0:
                raise ValidationError('Conversion rate must be greater than zero.')

    def name_get(self):
        result = []
        for rec in self:
            name = (
                f"{rec.from_currency_id.name} → "
                f"{rec.to_currency_id.name} "
                f"({rec.effective_date}) "
                f"Rate: {rec.rate}"
            )
            result.append((rec.id, name))
        return result

    @api.model
    def get_custom_rate(
            self,
            from_currency_id,
            to_currency_id,
            date=False,
            _visited=None
    ):
        if _visited is None:
            _visited = set()

        if not date:
            date = fields.Date.context_today(self)

        pair = (from_currency_id, to_currency_id)
        if pair in _visited:
            return None

        _visited.add(pair)

        direct = self.search([
            ('from_currency_id', '=', from_currency_id),
            ('to_currency_id', '=', to_currency_id),
            ('effective_date', '<=', date),
            ('active', '=', True),
        ], order='effective_date desc,id desc', limit=1)

        if direct:
            return direct.rate

        inverse = self.search([
            ('from_currency_id', '=', to_currency_id),
            ('to_currency_id', '=', from_currency_id),
            ('effective_date', '<=', date),
            ('active', '=', True),
        ], order='effective_date desc,id desc', limit=1)

        if inverse:
            return 1.0 / inverse.rate

        pivot_candidates = self.search([
            ('effective_date', '<=', date),
            ('active', '=', True),
            '|',
            ('from_currency_id', '=', from_currency_id),
            ('to_currency_id', '=', from_currency_id),
        ], order='effective_date desc,id desc')

        for rec in pivot_candidates:

            if rec.from_currency_id.id == from_currency_id:
                pivot_id = rec.to_currency_id.id
                first_rate = rec.rate
            else:
                pivot_id = rec.from_currency_id.id
                first_rate = 1.0 / rec.rate

            if pivot_id == to_currency_id:
                continue

            second_rate = self.get_custom_rate(
                pivot_id,
                to_currency_id,
                date=date,
                _visited=set(_visited)
            )

            if second_rate:
                return first_rate * second_rate

        return None