# -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
# Copyright (C) 2013  Renato Lima - Akretion                                  #
#                                                                             #
#This program is free software: you can redistribute it and/or modify         #
#it under the terms of the GNU Affero General Public License as published by  #
#the Free Software Foundation, either version 3 of the License, or            #
#(at your option) any later version.                                          #
#                                                                             #
#This program is distributed in the hope that it will be useful,              #
#but WITHOUT ANY WARRANTY; without even the implied warranty of               #
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the                #
#GNU Affero General Public License for more details.                          #
#                                                                             #
#You should have received a copy of the GNU Affero General Public License     #
#along with this program.  If not, see <http://www.gnu.org/licenses/>.        #
###############################################################################

import time
import datetime
from openerp import SUPERUSER_ID

from openerp.osv import orm, fields
from openerp.addons import decimal_precision as dp

from .l10n_br_account_product import (
    PRODUCT_FISCAL_TYPE,
    PRODUCT_FISCAL_TYPE_DEFAULT)
from .product import PRODUCT_ORIGIN
from .sped.nfe.validator import txt


class AccountInvoice(orm.Model):
    _inherit = 'account.invoice'

    def _amount_all(self, cr, uid, ids, name, args, context=None):
        result = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            result[invoice.id] = {
                'amount_untaxed': 0.0,
                'amount_tax': 0.0,
                'amount_tax_discount': 0.0,
                'amount_total': 0.0,
                'icms_base': 0.0,
                'icms_base_other': 0.0,
                'icms_value': 0.0,
                'icms_st_base': 0.0,
                'icms_st_value': 0.0,
                'ipi_base': 0.0,
                'ipi_base_other': 0.0,
                'ipi_value': 0.0,
                'pis_base': 0.0,
                'pis_value': 0.0,
                'cofins_base': 0.0,
                'cofins_value': 0.0,
                'ii_value': 0.0,
                'amount_insurance': 0.0,
                'amount_freight': 0.0,
                'amount_costs': 0.0,
                'amount_gross': 0.0,
                'amount_discount': 0.0,
            }
            for line in invoice.invoice_line:
                result[invoice.id]['amount_untaxed'] += line.price_total
                if line.icms_cst_id.code not in ('101','102','201','202','300','500'):
                    result[invoice.id]['icms_base'] += line.icms_base
                    result[invoice.id]['icms_base_other'] += line.icms_base_other
                    result[invoice.id]['icms_value'] += line.icms_value
                result[invoice.id]['icms_st_base'] += line.icms_st_base
                result[invoice.id]['icms_st_value'] += line.icms_st_value
                result[invoice.id]['ipi_base'] += line.ipi_base
                result[invoice.id]['ipi_base_other'] += line.ipi_base_other
                result[invoice.id]['ipi_value'] += line.ipi_value
                result[invoice.id]['pis_base'] += line.pis_base
                result[invoice.id]['pis_value'] += line.pis_value
                result[invoice.id]['cofins_base'] += line.cofins_base
                result[invoice.id]['cofins_value'] += line.cofins_value
                result[invoice.id]['ii_value'] += line.ii_value
                result[invoice.id]['amount_insurance'] += line.insurance_value
                result[invoice.id]['amount_freight'] += line.freight_value
                result[invoice.id]['amount_costs'] += line.other_costs_value
                result[invoice.id]['amount_gross'] += line.price_gross
                result[invoice.id]['amount_discount'] += line.discount_value

            for invoice_tax in invoice.tax_line:
                if not invoice_tax.tax_code_id.tax_discount:
                    result[invoice.id]['amount_tax'] += invoice_tax.amount

            result[invoice.id]['amount_total'] = result[invoice.id]['amount_tax'] + result[invoice.id]['amount_untaxed']
        return result

    def _get_invoice_line(self, cr, uid, ids, context=None):
        result = {}
        for line in self.pool.get('account.invoice.line').browse(
            cr, uid, ids, context=context):
            result[line.invoice_id.id] = True
        return list(result.keys())

    def _get_cfops(self, cr, uid, ids, name, arg, context=None):
        result = {}
        for invoice in self.browse(cr, uid, ids, context=context):
            result[invoice.id] = []
            new_ids = []
            for line in invoice.invoice_line:
                if line.cfop_id and not line.cfop_id.id in new_ids:
                    new_ids.append(line.cfop_id.id)
            new_ids.sort()
            result[invoice.id] = new_ids
        return result

    def _get_invoice_tax(self, cr, uid, ids, context=None):
        result = {}
        for tax in self.pool.get('account.invoice.tax').browse(
            cr, uid, ids, context=context):
            result[tax.invoice_id.id] = True
        return list(result.keys())

    _columns = {
        'nfe_version': fields.selection(
            [('1.10', '1.10'), ('2.00', '2.00'), ('3.10', '3.10')],
            u'Versão NFe', readonly=True,
            states={'draft': [('readonly', False)]}, required=True),
        'date_hour_invoice': fields.datetime(
            u'Data e hora de emissão', readonly=True,
            states={'draft': [('readonly', False)]},
            select=True, help="Deixe em branco para usar a data atual"),
        'ind_final': fields.selection([
            ('0', u'Não'),
            ('1', u'Consumidor final')
        ], u'Operação com Consumidor final', readonly=True,
            states={'draft': [('readonly', False)]}, required=False,
            help=u'Indica operação com Consumidor final.'),
        'ind_pres': fields.selection([
            ('0', u'Não se aplica'),
            ('1', u'Operação presencial'),
            ('2', u'Operação não presencial, pela Internet'),
            ('3', u'Operação não presencial, Teleatendimento'),
            ('4', u'NFC-e em operação com entrega em domicílio'),
            ('9', u'Operação não presencial, outros'),
        ], u'Tipo de operação', readonly=True,
            states={'draft': [('readonly', False)]}, required=False,
            help=u'Indicador de presença do comprador no \
                \nestabelecimento comercial no momento \
                \nda operação.'),
        'date_in_out': fields.datetime(
            u'Data de Entrada/Saida', readonly=True,
            states={'draft': [('readonly', False)]},
            select=True, help="Deixe em branco para usar a data atual"),
        'partner_shipping_id': fields.many2one(
            'res.partner', 'Delivery Address',
            readonly=True, required=True,
            states={'draft': [('readonly', False)]},
            help="Delivery address for current sales order."),
        'state': fields.selection([
            ('draft', 'Draft'),
            ('proforma', 'Pro-forma'),
            ('proforma2', 'Pro-forma'),
            ('sefaz_export', 'Enviar para Receita'),
            ('sefaz_exception', u'Erro de autorização da Receita'),
            ('sefaz_cancelled', 'Cancelado no Sefaz'),
            ('open', 'Open'),
            ('paid', 'Paid'),
            ('cancel', 'Cancelled')
            ], 'State', select=True, readonly=True,
            help=u' * The \'Draft\' state is used when a user is encoding a new and unconfirmed Invoice. \
            \n* The \'Pro-forma\' when invoice is in Pro-forma state,invoice does not have an invoice number. \
            \n* The \'Open\' state is used when user create invoice,a invoice number is generated.Its in open state till user does not pay invoice. \
            \n* The \'Paid\' state is set automatically when invoice is paid.\
            \n* The \'sefaz_out\' Gerado aquivo de exportação para sistema daReceita.\
            \n* The \'sefaz_aut\' Recebido arquivo de autolização da Receita.\
            \n* The \'Cancelled\' state is used when user cancel invoice.'),
        'fiscal_type': fields.selection(PRODUCT_FISCAL_TYPE, 'Tipo Fiscal', required=True),
        'partner_shipping_id': fields.many2one(
            'res.partner', u'Endereço de Entrega', readonly=True,
            states={'draft': [('readonly', False)]},
            help="Shipping address for current sales order."),
        'nfe_purpose': fields.selection(
            [('1', 'Normal'),
             ('2', 'Complementar'),
             ('3', 'Ajuste')], u'Finalidade da Emissão', readonly=True,
            states={'draft': [('readonly', False)]}),
        'nfe_access_key': fields.char(
            'Chave de Acesso NFE', size=44,
            readonly=True, states={'draft': [('readonly', False)]}),
        'nfe_protocol_number': fields.char(
            'Protocolo', size=15,
            readonly=True, states={'draft': [('readonly', False)]}),        
        'nfe_status': fields.char('Status na Sefaz', size=44, readonly=True),
        'nfe_date': fields.datetime('Data do Status NFE', readonly=True),
        'nfe_export_date': fields.datetime(u'Exportação NFE', readonly=True),
        'cfop_ids': fields.function(
            _get_cfops, method=True, type='many2many',
            relation='l10n_br_account_product.cfop', string='CFOP'),
        'fiscal_document_related_ids': fields.one2many(
            'l10n_br_account_product.document.related', 'invoice_id',
            'Fiscal Document Related', readonly=True,
            states={'draft': [('readonly', False)]}),
        'carrier_name': fields.char('Nome Transportadora', size=32),
        'vehicle_plate': fields.char('Placa do Veiculo', size=7),
        'vehicle_state_id': fields.many2one(
            'res.country.state', 'UF da Placa'),
        'vehicle_l10n_br_city_id': fields.many2one('l10n_br_base.city',
            'Municipio', domain="[('state_id', '=', vehicle_state_id)]"),
        'amount_gross': fields.function(
            _amount_all, method=True,
            digits_compute=dp.get_precision('Account'), string='Vlr. Bruto',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids,
                                    ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (
                    _get_invoice_line, ['price_unit',
                                        'invoice_line_tax_id',
                                        'quantity', 'discount'], 20),
            }, multi='all'),
        'amount_discount': fields.function(
            _amount_all, method=True,
            digits_compute=dp.get_precision('Account'), string='Desconto',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids,
                                    ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (
                    _get_invoice_line, ['price_unit',
                                        'invoice_line_tax_id',
                                        'quantity', 'discount'], 20),
            }, multi='all'),
        'amount_untaxed': fields.function(
            _amount_all, method=True,
            digits_compute=dp.get_precision('Account'), string='Untaxed',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids,
                                    ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (
                    _get_invoice_line, ['price_unit',
                                        'invoice_line_tax_id',
                                        'quantity', 'discount'], 20),
            }, multi='all'),
        'amount_tax': fields.function(
            _amount_all, method=True,
            digits_compute=dp.get_precision('Account'), string='Tax',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids,
                                    ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line,
                                         ['price_unit',
                                          'invoice_line_tax_id',
                                          'quantity', 'discount'], 20),
            }, multi='all'),
        'amount_total': fields.function(
            _amount_all, method=True,
            digits_compute=dp.get_precision('Account'), string='Total',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids,
                                    ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line,
                                         ['price_unit',
                                          'invoice_line_tax_id',
                                          'quantity', 'discount'], 20),
            }, multi='all'),
        'icms_base': fields.function(
            _amount_all, method=True,
            digits_compute=dp.get_precision('Account'), string='Base ICMS',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids,
                                    ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line,
                                         ['price_unit',
                                          'invoice_line_tax_id',
                                          'quantity', 'discount'], 20),
            }, multi='all'),
        'icms_base_other': fields.function(
            _amount_all, method=True,
            digits_compute=dp.get_precision('Account'),
            string='Base ICMS Outras',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids,
                                    ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line,
                                         ['price_unit',
                                          'invoice_line_tax_id',
                                          'quantity', 'discount'], 20),
            }, multi='all'),
        'icms_value': fields.function(
            _amount_all, method=True,
            digits_compute=dp.get_precision('Account'), string='Valor ICMS',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids,
                                    ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line,
                                         ['price_unit',
                                          'invoice_line_tax_id',
                                          'quantity', 'discount'], 20),
            }, multi='all'),
        'icms_st_base': fields.function(
            _amount_all, method=True,
            digits_compute=dp.get_precision('Account'), string='Base ICMS ST',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids,
                                    ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line,
                                         ['price_unit',
                                          'invoice_line_tax_id',
                                          'quantity', 'discount'], 20),
            },
            multi='all'),
        'icms_st_value': fields.function(
            _amount_all, method=True,
            digits_compute=dp.get_precision('Account'), string='Valor ICMS ST',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids,
                                    ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line,
                                         ['price_unit',
                                          'invoice_line_tax_id',
                                          'quantity', 'discount'], 20),
            }, multi='all'),
        'ipi_base': fields.function(
            _amount_all, method=True,
            digits_compute=dp.get_precision('Account'), string='Base IPI',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids,
                                    ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line,
                                         ['price_unit',
                                          'invoice_line_tax_id',
                                          'quantity', 'discount'], 20),
            }, multi='all'),
        'ipi_base_other': fields.function(
            _amount_all, method=True,
            digits_compute=dp.get_precision('Account'),
            string='Base IPI Outras',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids,
                                    ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line,
                                         ['price_unit',
                                          'invoice_line_tax_id',
                                          'quantity', 'discount'], 20),
            }, multi='all'),
        'ipi_value': fields.function(
            _amount_all, method=True,
            digits_compute=dp.get_precision('Account'), string='Valor IPI',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids,
                                    ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line,
                                         ['price_unit',
                                          'invoice_line_tax_id',
                                          'quantity', 'discount'], 20),
            }, multi='all'),
        'pis_base': fields.function(
            _amount_all, method=True,
            digits_compute=dp.get_precision('Account'), string='Base PIS',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids,
                                    ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line,
                                         ['price_unit',
                                          'invoice_line_tax_id',
                                          'quantity', 'discount'], 20),
            }, multi='all'),
        'pis_value': fields.function(
            _amount_all, method=True,
            digits_compute=dp.get_precision('Account'), string='Valor PIS',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids,
                                    ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line,
                                         ['price_unit',
                                          'invoice_line_tax_id',
                                          'quantity', 'discount'], 20),
            }, multi='all'),
        'cofins_base': fields.function(
            _amount_all, method=True,
            digits_compute=dp.get_precision('Account'), string='Base COFINS',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids,
                                    ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line,
                                         ['price_unit',
                                          'invoice_line_tax_id',
                                          'quantity', 'discount'], 20),
            }, multi='all'),
        'cofins_value': fields.function(
            _amount_all, method=True,
            digits_compute=dp.get_precision('Account'), string='Valor COFINS',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids,
                                    ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line,
                                         ['price_unit',
                                          'invoice_line_tax_id',
                                          'quantity', 'discount'], 20),
            }, multi='all'),
        'ii_value': fields.function(
            _amount_all, method=True,
            digits_compute=dp.get_precision('Account'), string='Valor II',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids,
                                    ['invoice_line'], 20),
                'account.invoice.tax': (_get_invoice_tax, None, 20),
                'account.invoice.line': (_get_invoice_line,
                                         ['price_unit',
                                          'invoice_line_tax_id',
                                          'quantity', 'discount'], 20),
            }, multi='all'),
        'weight': fields.float('Gross weight', readonly=True,
                               states={'draft': [('readonly', False)]},
                               help="The gross weight in Kg.",),
        'weight_net': fields.float('Net weight', help="The net weight in Kg.",
                                    readonly=True,
                                    states={'draft': [('readonly', False)]}),
        'number_of_packages': fields.integer(
            'Quantidade de Volumes',  readonly=True, states={'draft': [('readonly', False)]}),
        'kind_of_packages': fields.char(
            'Espécie', size=60, readonly=True, states={'draft': [('readonly', False)]}),
        'brand_of_packages': fields.char(
            'Brand',  size=60, readonly=True, states={'draft': [('readonly', False)]}),
        'notation_of_packages': fields.char(
            'Numeração', size=60, readonly=True, states={'draft': [('readonly', False)]}),
        'amount_insurance': fields.function(
            _amount_all, method=True,
            digits_compute=dp.get_precision('Account'),
            string='Valor do Seguro',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids,
                                    ['invoice_line'], 20),
                'account.invoice.line': (_get_invoice_line,
                                         ['insurance_value'], 20),
            }, multi='all'),
        'amount_freight': fields.function(
            _amount_all, method=True,
            digits_compute=dp.get_precision('Account'),
            string='Valor do Seguro',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids,
                                    ['invoice_line'], 20),
                'account.invoice.line': (_get_invoice_line,
                                        ['freight_value'], 20),
            }, multi='all'),
        'amount_costs': fields.function(
            _amount_all, method=True,
            digits_compute=dp.get_precision('Account'), string='Outros Custos',
            store={
                'account.invoice': (lambda self, cr, uid, ids, c={}: ids,
                    ['invoice_line'], 20),
                'account.invoice.line': (_get_invoice_line,
                    ['other_costs_value'], 20)}, multi='all'),
    }

    def _default_fiscal_category(self, cr, uid, context=None):

        DEFAULT_FCATEGORY_PRODUCT = {
            'in_invoice': 'in_invoice_fiscal_category_id',
            'out_invoice': 'out_invoice_fiscal_category_id',
            'in_refund': 'in_refund_fiscal_category_id',
            'out_refund': 'out_refund_fiscal_category_id'
        }

        default_fo_category = {
           'product': DEFAULT_FCATEGORY_PRODUCT,
        }

        invoice_type = context.get('type', 'out_invoice')
        invoice_fiscal_type = context.get('fiscal_type', 'product')

        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        fcategory = self.pool.get('res.company').read(
            cr, uid, user.company_id.id,
            [default_fo_category[invoice_fiscal_type][invoice_type]],
            context=context)[default_fo_category[invoice_fiscal_type][
                invoice_type]]

        return fcategory and fcategory[0] or False

    def _default_fiscal_document(self, cr, uid, context):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        fiscal_document = self.pool.get('res.company').read(
            cr, uid, user.company_id.id, ['product_invoice_id'],
            context=context)['product_invoice_id']

        return fiscal_document and fiscal_document[0] or False

    def _default_fiscal_document_serie(self, cr, uid, context):
        fiscal_document_serie = False
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        company = self.pool.get('res.company').browse(
            cr, uid, user.company_id.id, context=context)

        fiscal_document_series = [doc_serie for doc_serie in
            company.document_serie_product_ids if
            doc_serie.fiscal_document_id.id ==
            company.product_invoice_id.id and doc_serie.active]
        if fiscal_document_series:
            fiscal_document_serie = fiscal_document_series[0].id

        return fiscal_document_serie

    def _default_nfe_version(self, cr, uid, context=None):
        user = self.pool.get('res.users').browse(cr, uid, uid, context=context)
        nfe_version = self.pool.get('res.company').read(
            cr, uid, user.company_id.id, ['nfe_version'],
            context=context)['nfe_version']
        return nfe_version or False

    _defaults = {
        'nfe_version': _default_nfe_version,
        'ind_final': '0',
        'ind_pres': '0',
        'fiscal_category_id': _default_fiscal_category,
        'fiscal_document_id': _default_fiscal_document,
        'document_serie_id': _default_fiscal_document_serie,
        'issuer': '0',
        'nfe_purpose': '1',
        'fiscal_type': PRODUCT_FISCAL_TYPE_DEFAULT,
    }

    def nfe_check(self, cr, uid, ids, context=None):

        result = txt.validate(cr, uid, ids, context)
        return result

    def action_move_create(self, cr, uid, ids, *args):
        result = super(AccountInvoice, self).action_move_create(
            cr, uid, ids, *args)

        user = self.pool.get('res.users').browse(cr, uid, uid)
        obj_company = self.pool.get('res.company')
        company_id = obj_company.browse(cr, uid, user.company_id.id).id

        for invoice in self.browse(cr, uid, ids):
            date_time_now = fields.datetime.now()

            if not invoice.date_hour_invoice:
                self.write(cr, uid, [invoice.id], {'date_hour_invoice': date_time_now})

            if not invoice.date_in_out:
                self.write(cr, uid, [invoice.id], {'date_in_out': date_time_now})

        return result

    def action_date_assign(self, cr, uid, ids, *args):

        for inv in self.browse(cr, uid, ids):
            if inv.date_hour_invoice:
                aux = datetime.datetime.strptime(inv.date_hour_invoice, '%Y-%m-%d %H:%M:%S').date()
                inv.date_invoice = str(aux)

            res = self.onchange_payment_term_date_invoice(cr, uid, inv.id, inv.payment_term.id, inv.date_invoice)

            if res and res['value']:
                self.write(cr, uid, [inv.id], res['value'])
        return True


class AccountInvoiceLine(orm.Model):
    _inherit = 'account.invoice.line'

    def _amount_line(self, cr, uid, ids, prop, unknow_none, unknow_dict):
        res = {}
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        for line in self.browse(cr, uid, ids):
            res[line.id] = {
                'price_subtotal': 0.0,
                'price_total': 0.0,
                'discount_value': 0.0,
                'price_gross': 0.0,
            }

            price = line.price_unit * (1 - (line.discount or 0.0) / 100.0)
            taxes = tax_obj.compute_all(
                cr, uid, line.invoice_line_tax_id, price, line.quantity,
                line.product_id, line.invoice_id.partner_id,
                fiscal_position=line.fiscal_position,
                insurance_value=line.insurance_value,
                freight_value=line.freight_value,
                other_costs_value=line.other_costs_value)

            if line.invoice_id:
                currency = line.invoice_id.currency_id
                price_gross = cur_obj.round(cr, uid, currency,
                    line.price_unit * line.quantity)
                res[line.id].update({
                    'price_subtotal': cur_obj.round(
                        cr, uid, currency,
                        taxes['total'] - taxes['total_tax_discount']),
                    'price_total': cur_obj.round(
                        cr, uid, currency, taxes['total']),
                    'price_gross': price_gross,
                    'discount_value': (price_gross - taxes['total']),
                })

        return res

    _columns = {
        'date_invoice': fields.date('Invoice Date', readonly=True, states={'draft':[('readonly',False)]}, select=True, help="Keep empty to use the current date"),
        'fiscal_category_id': fields.many2one(
            'l10n_br_account.fiscal.category', 'Categoria'),
        'fiscal_position': fields.many2one(
            'account.fiscal.position', u'Posição Fiscal',
            domain="[('fiscal_category_id','=',fiscal_category_id)]"),
        'import_declaration_ids': fields.one2many(
            'l10n_br_account_product.import.declaration',
            'invoice_line_id', u'Declaração de Importação'),
        'cfop_id': fields.many2one('l10n_br_account_product.cfop', 'CFOP'),
        'fiscal_classification_id': fields.many2one(
            'account.product.fiscal.classification', u'Classificação Fiscal'),
        'product_type': fields.selection(
            [('product', 'Produto'), ('service', u'Serviço')],
            'Tipo do Produto', required=True),
        'discount_value': fields.function(
            _amount_line, method=True, string='Vlr. desconto', type="float",
            digits_compute=dp.get_precision('Account'),
            store=True, multi='all'),
        'price_total': fields.function(
            _amount_line, method=True, string='Total', type="float",
            digits_compute=dp.get_precision('Account'),
            store=True, multi='all'),
        'price_gross': fields.function(
            _amount_line, method=True, string='Vlr. Bruto', type="float",
            digits_compute=dp.get_precision('Account'),
            store=True, multi='all'),
        'price_subtotal': fields.function(
            _amount_line, method=True, string='Subtotal', type="float",
            digits_compute=dp.get_precision('Account'),
            store=True, multi='all'),
        'price_total': fields.function(
            _amount_line, method=True, string='Total', type="float",
            digits_compute=dp.get_precision('Account'),
            store=True, multi='all'),
        'icms_manual': fields.boolean('ICMS Manual?'),
        'icms_origin': fields.selection(PRODUCT_ORIGIN, 'Origem'),
        'icms_base_type': fields.selection(
            [('0', 'Margem Valor Agregado (%)'), ('1', 'Pauta (valor)'),
            ('2', u'Preço Tabelado Máximo (valor)'),
            ('3', u'Valor da Operação')],
            'Tipo Base ICMS', required=True),
        'icms_base': fields.float('Base ICMS', required=True,
            digits_compute=dp.get_precision('Account')),
        'icms_base_other': fields.float('Base ICMS Outras', required=True,
            digits_compute=dp.get_precision('Account')),
        'icms_value': fields.float('Valor ICMS', required=True,
            digits_compute=dp.get_precision('Account')),
        'icms_percent': fields.float('Perc ICMS',
            digits_compute=dp.get_precision('Discount')),
        'icms_percent_reduction': fields.float(u'Perc Redução de Base ICMS',
            digits_compute=dp.get_precision('Discount')),
        'icms_st_base_type': fields.selection(
            [('0', u'Preço tabelado ou máximo  sugerido'),
            ('1', 'Lista Negativa (valor)'),
            ('2', 'Lista Positiva (valor)'), ('3', 'Lista Neutra (valor)'),
            ('4', 'Margem Valor Agregado (%)'), ('5', 'Pauta (valor)')],
            'Tipo Base ICMS ST', required=True),
        'icms_st_value': fields.float('Valor ICMS ST', required=True,
            digits_compute=dp.get_precision('Account')),
        'icms_st_base': fields.float('Base ICMS ST', required=True,
            digits_compute=dp.get_precision('Account')),
        'icms_st_percent': fields.float('Percentual ICMS ST',
            digits_compute=dp.get_precision('Discount')),
        'icms_st_percent_reduction': fields.float(
            u'Perc Redução de Base ICMS ST',
            digits_compute=dp.get_precision('Discount')),
        'icms_st_mva': fields.float('MVA ICMS ST',
            digits_compute=dp.get_precision('Discount')),
        'icms_st_base_other': fields.float('Base ICMS ST Outras',
            required=True, digits_compute=dp.get_precision('Account')),
        'icms_cst_id': fields.many2one('account.tax.code', 'CST ICMS',
            domain=[('domain', '=', 'icms')]),
        'issqn_manual': fields.boolean('ISSQN Manual?'),
        'issqn_type': fields.selection(
            [('N', 'Normal'), ('R', 'Retida'),
            ('S', 'Substituta'), ('I', 'Isenta')], 'Tipo do ISSQN',
            required=True),
        'service_type_id': fields.many2one(
            'l10n_br_account.service.type', u'Tipo de Serviço'),
        'issqn_base': fields.float('Base ISSQN', required=True,
            digits_compute=dp.get_precision('Account')),
        'issqn_percent': fields.float('Perc ISSQN', required=True,
            digits_compute=dp.get_precision('Discount')),
        'issqn_value': fields.float('Valor ISSQN', required=True,
            digits_compute=dp.get_precision('Account')),
        'ipi_manual': fields.boolean('IPI Manual?'),
        'ipi_type': fields.selection(
            [('percent', 'Percentual'), ('quantity', 'Em Valor')],
            'Tipo do IPI', required=True),
        'ipi_base': fields.float('Base IPI', required=True,
            digits_compute=dp.get_precision('Account')),
        'ipi_base_other': fields.float('Base IPI Outras', required=True,
            digits_compute=dp.get_precision('Account')),
        'ipi_value': fields.float('Valor IPI', required=True,
            digits_compute=dp.get_precision('Account')),
        'ipi_percent': fields.float('Perc IPI', required=True,
            digits_compute=dp.get_precision('Discount')),
        'ipi_cst_id': fields.many2one('account.tax.code', 'CST IPI',
            domain=[('domain', '=', 'ipi')]),
        'pis_manual': fields.boolean('PIS Manual?'),
        'pis_type': fields.selection(
            [('percent', 'Percentual'), ('quantity', 'Em Valor')],
            'Tipo do PIS', required=True),
        'pis_base': fields.float('Base PIS', required=True,
            digits_compute=dp.get_precision('Account')),
        'pis_base_other': fields.float('Base PIS Outras', required=True,
            digits_compute=dp.get_precision('Account')),
        'pis_value': fields.float('Valor PIS', required=True,
            digits_compute=dp.get_precision('Account')),
        'pis_percent': fields.float('Perc PIS', required=True,
            digits_compute=dp.get_precision('Discount')),
        'pis_cst_id': fields.many2one('account.tax.code', 'CST PIS',
            domain=[('domain', '=', 'pis')]),
        'pis_st_type': fields.selection(
            [('percent', 'Percentual'), ('quantity', 'Em Valor')],
            'Tipo do PIS ST', required=True),
        'pis_st_base': fields.float('Base PIS ST', required=True,
            digits_compute=dp.get_precision('Account')),
        'pis_st_percent': fields.float('Perc PIS ST', required=True,
            digits_compute=dp.get_precision('Account')),
        'pis_st_value': fields.float('Valor PIS ST', required=True,
            digits_compute=dp.get_precision('Account')),
        'cofins_manual': fields.boolean('COFINS Manual?'),
        'cofins_type': fields.selection(
            [('percent', 'Percentual'), ('quantity', 'Em Valor')],
            'Tipo do COFINS', required=True),
        'cofins_base': fields.float('Base COFINS', required=True,
            digits_compute=dp.get_precision('Account')),
        'cofins_base_other': fields.float('Base COFINS Outras', required=True,
            digits_compute=dp.get_precision('Account')),
        'cofins_value': fields.float('Valor COFINS', required=True,
            digits_compute=dp.get_precision('Account')),
        'cofins_percent': fields.float('Perc COFINS', required=True,
            digits_compute=dp.get_precision('Discount')),
        'cofins_cst_id': fields.many2one('account.tax.code', 'CST PIS',
            domain=[('domain', '=', 'cofins')]),
        'cofins_st_type': fields.selection(
            [('percent', 'Percentual'), ('quantity', 'Em Valor')],
            'Tipo do COFINS ST', required=True),
        'cofins_st_base': fields.float('Base COFINS ST', required=True,
            digits_compute=dp.get_precision('Account')),
        'cofins_st_percent': fields.float('Perc COFINS ST', required=True,
            digits_compute=dp.get_precision('Discount')),
        'cofins_st_value': fields.float('Valor COFINS ST', required=True,
            digits_compute=dp.get_precision('Account')),
        'ii_base': fields.float('Base II', required=True,
            digits_compute=dp.get_precision('Account')),
        'ii_value': fields.float('Valor II', required=True,
            digits_compute=dp.get_precision('Account')),
        'ii_iof': fields.float('Valor IOF', required=True,
            digits_compute=dp.get_precision('Account')),
        'ii_customhouse_charges': fields.float('Depesas Atuaneiras',
            required=True, digits_compute=dp.get_precision('Account')),
        'insurance_value': fields.float('Valor do Seguro',
            digits_compute=dp.get_precision('Account')),
        'other_costs_value': fields.float('Outros Custos',
            digits_compute=dp.get_precision('Account')),
        'freight_value': fields.float('Frete',
            digits_compute=dp.get_precision('Account'))
    }
    _defaults = {
        'product_type': 'product',
        'icms_manual': False,
        'icms_origin': '0',
        'icms_base_type': '0',
        'icms_base': 0.0,
        'icms_base_other': 0.0,
        'icms_value': 0.0,
        'icms_percent': 0.0,
        'icms_percent_reduction': 0.0,
        'icms_st_base_type': 'percent',
        'icms_st_value': 0.0,
        'icms_st_base': 0.0,
        'icms_st_percent': 0.0,
        'icms_st_percent_reduction': 0.0,
        'icms_st_mva': 0.0,
        'icms_st_base_other': 0.0,
        'icms_st_base_type': '4',
        'issqn_manual': False,
        'issqn_type': 'N',
        'issqn_base': 0.0,
        'issqn_percent': 0.0,
        'issqn_value': 0.0,
        'ipi_manual': False,
        'ipi_type': 'percent',
        'ipi_base': 0.0,
        'ipi_base_other': 0.0,
        'ipi_value': 0.0,
        'ipi_percent': 0.0,
        'pis_manual': False,
        'pis_type': 'percent',
        'pis_base': 0.0,
        'pis_base_other': 0.0,
        'pis_value': 0.0,
        'pis_percent': 0.0,
        'pis_st_type': 'percent',
        'pis_st_base': 0.0,
        'pis_st_percent': 0.0,
        'pis_st_value': 0.0,
        'cofins_manual': False,
        'cofins_type': 'percent',
        'cofins_base': 0.0,
        'cofins_base_other': 0.0,
        'cofins_value': 0.0,
        'cofins_percent': 0.0,
        'cofins_st_type': 'percent',
        'cofins_st_base': 0.0,
        'cofins_st_percent': 0.0,
        'cofins_st_value': 0.0,
        'ii_base': 0.0,
        'ii_value': 0.0,
        'ii_iof': 0.0,
        'ii_customhouse_charges': 0.0,
        'insurance_value': 0.0,
        'other_costs_value': 0.0,
        'freight_value': 0.0,
    }

    def _amount_tax_icms(self, cr, uid, tax=None):
        result = {
            'icms_base_type': '0',
            'icms_base': tax.get('total_base', 0.0),
            'icms_base_other': tax.get('total_base_other', 0.0),
            'icms_value': tax.get('amount', 0.0),
            'icms_percent': tax.get('percent', 0.0) * 100,
            'icms_percent_reduction': tax.get('base_reduction') * 100,
        }
        return result

    def _amount_tax_icmsst(self, cr, uid, tax=None):
        result = {
            'icms_st_value': tax.get('amount', 0.0),
            'icms_st_base': tax.get('total_base', 0.0),
            'icms_st_percent': tax.get('icms_st_percent', 0.0) * 100,
            'icms_st_percent_reduction': tax.get('icms_st_percent_reduction', 0.0) * 100,
            'icms_st_mva': tax.get('amount_mva', 0.0) * 100,
            'icms_st_base_other': tax.get('icms_st_base_other', 0.0),
        }
        return result

    def _amount_tax_ipi(self, cr, uid, tax=None):
        result = {
            'ipi_type': tax.get('type'),
            'ipi_base': tax.get('total_base', 0.0),
            'ipi_value': tax.get('amount', 0.0),
            'ipi_percent': tax.get('percent', 0.0) * 100,
        }
        return result

    def _amount_tax_cofins(self, cr, uid, tax=None):
        result = {
            'cofins_base': tax.get('total_base', 0.0),
            'cofins_base_other': tax.get('total_base_other', 0.0),
            'cofins_value': tax.get('amount', 0.0),
            'cofins_percent': tax.get('percent', 0.0) * 100,
        }
        return result

    def _amount_tax_cofinsst(self, cr, uid, tax=None):
        result = {
            'cofins_st_type': 'percent',
            'cofins_st_base': 0.0,
            'cofins_st_percent': 0.0,
            'cofins_st_value': 0.0,
        }
        return result

    def _amount_tax_pis(self, cr, uid, tax=False):
        result = {
            'pis_base': tax.get('total_base', 0.0),
            'pis_base_other': tax.get('total_base_other', 0.0),
            'pis_value': tax.get('amount', 0.0),
            'pis_percent': tax.get('percent', 0.0) * 100,
        }
        return result

    def _amount_tax_pisst(self, cr, uid, tax=False):
        result = {
            'pis_st_type': 'percent',
            'pis_st_base': 0.0,
            'pis_st_percent': 0.0,
            'pis_st_value': 0.0,
        }
        return result

    def _amount_tax_ii(self, cr, uid, tax=False):
        result = {
            'ii_base': 0.0,
            'ii_value': 0.0,
        }
        return result

    def _amount_tax_issqn(self, cr, uid, tax=False):

        # TODO deixar dinamico a definição do tipo do ISSQN
        # assim como todos os impostos
        issqn_type = 'N'
        if not tax.get('amount'):
            issqn_type = 'I'

        result = {
            'issqn_type': issqn_type,
            'issqn_base': tax.get('total_base', 0.0),
            'issqn_percent': tax.get('percent', 0.0) * 100,
            'issqn_value': tax.get('amount', 0.0),
        }
        return result

    def _get_tax_codes(self, cr, uid, product_id, fiscal_position,
                        taxes, company_id, context=None):

        context = dict(context or {})
        result = {}

        if fiscal_position.fiscal_category_id.journal_type in ('sale', 'sale_refund'):
            context['type_tax_use'] = 'sale'
        else:
            context['type_tax_use'] = 'purchase'

        context['fiscal_type'] = fiscal_position.fiscal_category_fiscal_type

        tax_codes = self.pool.get('account.fiscal.position').map_tax_code(
            cr, uid, product_id, fiscal_position, company_id,
            taxes, context=context)

        result['icms_cst_id'] = tax_codes.get('icms', False)
        result['ipi_cst_id'] = tax_codes.get('ipi', False)
        result['pis_cst_id'] = tax_codes.get('pis', False)
        result['cofins_cst_id'] = tax_codes.get('cofins', False)
        return result

    def _validate_taxes(self, cr, uid, values, context=None):
        """Verifica se o valor dos campos dos impostos estão sincronizados
        com os impostos do OpenERP"""
        if not context:
            context = {}

        tax_obj = self.pool.get('account.tax')

        if (not values.get('product_id')
                or not values.get('quantity')
                or not values.get('fiscal_position')):
            invoice_line_id = context.get('invoice_line_id', False)
            if not invoice_line_id:
                return {}
            elif isinstance(invoice_line_id, (list)) and not len(invoice_line_id) == 1:
                return {}
            else:
                if isinstance(invoice_line_id, (int)):
                    invoice_line_id = [invoice_line_id]
                old = self.read(cr, uid, invoice_line_id,[
                    'fiscal_position', 'product_id', 'price_unit',
                     'company_id', 'invoice_line_tax_id', 'partner_id',
                     'quantity'])[0]
                for aux in old:
                    if isinstance(old[aux], (tuple)):
                        old[aux] = old[aux][0]
                old['invoice_line_tax_id'] = [[6, 0, old['invoice_line_tax_id']]]
                values = dict(old.items() + values.items())

        result = {
            'product_type': 'product',
            'service_type_id': False,
            'fiscal_classification_id': False
        }

        if values.get('partner_id') and values.get('company_id'):
            partner_id = values.get('partner_id')
            company_id = values.get('company_id')
        else:
            if values.get('invoice_id'):
                inv = self.pool.get('account.invoice').read(
                    cr, uid, values.get('invoice_id'),
                    ['partner_id', 'company_id'])

                partner_id = inv.get('partner_id', [False])[0]
                company_id = inv.get('company_id', [False])[0]

        taxes = tax_obj.browse(
            cr, uid, values.get('invoice_line_tax_id')[0][2])
        fiscal_position = self.pool.get('account.fiscal.position').browse(
            cr, uid, values.get('fiscal_position'))

        price_unit = values.get('price_unit', 0.0)
        price = price_unit * (1 - values.get('discount', 0.0) / 100.0)

        taxes_calculed = tax_obj.compute_all(
            cr, uid, taxes, price, values.get('quantity', 0.0),
            values.get('product_id'), partner_id,
            fiscal_position=fiscal_position,
            insurance_value=values.get('insurance_value', 0.0),
            freight_value=values.get('freight_value', 0.0),
            other_costs_value=values.get('other_costs_value', 0.0))

        if values.get('product_id'):
            obj_product = self.pool.get('product.product').browse(
                cr, uid, values.get('product_id'), context=context)
            if obj_product.type == 'service':
                result['product_type'] = 'service'
                result['service_type_id'] = obj_product.service_type_id.id
            else:
                result['product_type'] = 'product'
            if obj_product.ncm_id:
                result['fiscal_classification_id'] = obj_product.ncm_id.id

            result['icms_origin'] = obj_product.origin

        for tax in taxes_calculed['taxes']:
            try:
                amount_tax = getattr(
                    self, '_amount_tax_%s' % tax.get('domain', ''))
                result.update(amount_tax(cr, uid, tax))
            except AttributeError:
                # Caso não exista campos especificos dos impostos
                # no documento fiscal, os mesmos são calculados.
                continue

        result.update(self._get_tax_codes(
            cr, uid, values.get('product_id'), fiscal_position,
            values.get('invoice_line_tax_id')[0][2],
            company_id, context=context))
        return result

    def create(self, cr, uid, vals, context=None):
        if not context:
            context = {}
        vals.update(self._validate_taxes(cr, uid, vals, context))
        return super(AccountInvoiceLine, self).create(cr, uid, vals, context)

    def write(self, cr, uid, ids, vals, context=None):
        if not context:
            context = {}
        context.update({'invoice_line_id': ids})
        vals.update(self._validate_taxes(cr, uid, vals, context))
        return super(AccountInvoiceLine, self).write(
            cr, uid, ids, vals, context=context)


class AccountInvoiceTax(orm.Model):
    _inherit = "account.invoice.tax"

    def compute(self, cr, uid, invoice, context=None):
        tax_grouped = {}
        tax_obj = self.pool.get('account.tax')
        cur_obj = self.pool.get('res.currency')
        inv = self.pool.get('account.invoice').browse(
            cr, uid, invoice.id, context=context)
        cur = inv.currency_id
        currenty_date = time.strftime('%Y-%m-%d')
        company_currency = inv.company_id.currency_id.id

        for line in inv.invoice_line:
            for tax in tax_obj.compute_all(
                cr, uid, line.invoice_line_tax_id,
                (line.price_unit * (1 - (line.discount or 0.0) / 100.0)),
                line.quantity, line.product_id, inv.partner_id,
                fiscal_position=line.fiscal_position,
               insurance_value=line.insurance_value,
                freight_value=line.freight_value,
                other_costs_value=line.other_costs_value)['taxes']:
                val = {}
                val['invoice_id'] = inv.id
                val['name'] = tax['name']
                val['amount'] = tax['amount']
                val['manual'] = False
                val['sequence'] = tax['sequence']
                val['base'] = tax.get('total_base', 0.0)

                if inv.type in ('out_invoice', 'in_invoice'):
                    val['base_code_id'] = tax['base_code_id']
                    val['tax_code_id'] = tax['tax_code_id']
                    val['base_amount'] = cur_obj.compute(cr, uid,
                        inv.currency_id.id, company_currency,
                        val['base'] * tax['base_sign'],
                        context={'date': inv.date_invoice or currenty_date},
                        round=False)
                    val['tax_amount'] = cur_obj.compute(
                        cr, uid, inv.currency_id.id, company_currency,
                        val['amount'] * tax['tax_sign'],
                        context={'date': inv.date_invoice or currenty_date},
                        round=False)
                    val['account_id'] = tax['account_collected_id'] or line.account_id.id
                    val['account_analytic_id'] = tax['account_analytic_collected_id']
                else:
                    val['base_code_id'] = tax['ref_base_code_id']
                    val['tax_code_id'] = tax['ref_tax_code_id']
                    val['base_amount'] = cur_obj.compute(
                        cr, uid, inv.currency_id.id, company_currency,
                        val['base'] * tax['ref_base_sign'],
                        context={'date': inv.date_invoice or currenty_date},
                        round=False)
                    val['tax_amount'] = cur_obj.compute(
                        cr, uid, inv.currency_id.id,
                        company_currency, val['amount'] * tax['ref_tax_sign'],
                        context={'date': inv.date_invoice or currenty_date},
                        round=False)
                    val['account_id'] = tax['account_paid_id'] or line.account_id.id
                    val['account_analytic_id'] = tax['account_analytic_paid_id']
                
                if not val.get('account_analytic_id') and line.account_analytic_id and val['account_id'] == line.account_id.id:
                    val['account_analytic_id'] = line.account_analytic_id.id

                key = (val['tax_code_id'], val['base_code_id'], val['account_id'])
                if not key in tax_grouped:
                    tax_grouped[key] = val
                else:
                    tax_grouped[key]['amount'] += val['amount']
                    tax_grouped[key]['base'] += val['base']
                    tax_grouped[key]['base_amount'] += val['base_amount']
                    tax_grouped[key]['tax_amount'] += val['tax_amount']

        for t in tax_grouped.values():
            t['base'] = cur_obj.round(cr, uid, cur, t['base'])
            t['amount'] = cur_obj.round(cr, uid, cur, t['amount'])
            t['base_amount'] = cur_obj.round(cr, uid, cur, t['base_amount'])
            t['tax_amount'] = cur_obj.round(cr, uid, cur, t['tax_amount'])
        return tax_grouped
