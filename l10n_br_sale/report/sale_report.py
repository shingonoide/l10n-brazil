# -*- encoding: utf-8 -*-
###############################################################################
#                                                                             #
# Copyright (C) 2011  Renato Lima - Akretion                                  #
#                                                                             #
#This program is free software: you can redistribute it and/or modify         #
#it under the terms of the GNU Affero General Public License as published by  #
#the Free Software Foundation, either version 3 of the License, or            #
#(at your option) any later version.                                          #
#                                                                             #
#This program is distributed in the hope that it will be useful,              #
#but WITHOUT ANY WARRANTY; without even the implied warranty of               #
#MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the                #
#GNU General Public License for more details.                                 #
#                                                                             #
#You should have received a copy of the GNU General Public License            #
#along with this program.  If not, see <http://www.gnu.org/licenses/>.        #
###############################################################################

from openerp import tools
from openerp.osv import orm, fields


class sale_report(orm.Model):
    _inherit = "sale.report"
    _columns = {
        'fiscal_category_id': fields.many2one(
            'l10n_br_account.fiscal.category', 'Fiscal Category',
            readonly=True),
        'fiscal_position': fields.many2one(
            'account.fiscal.position', 'Fiscal Position', readonly=True)
    }

    def init(self, cr):
        tools.drop_view_if_exists(cr, 'sale_report')
        cr.execute("""create or replace view sale_report as (
                select
                    min(l.id) as id,
                    l.product_id as product_id,
                    l.fiscal_category_id as fiscal_category_id,
                    l.fiscal_position as fiscal_position,
                    t.uom_id as product_uom,
                    sum(l.product_uom_qty / u.factor * u2.factor) as product_uom_qty,
                    sum(l.product_uom_qty * l.price_unit * (100.0-l.discount) / 100.0) as price_total,
                    1 as nbr,
                    s.date_order as date,
                    s.date_confirm as date_confirm,
                    to_char(s.date_order, 'YYYY') as year,
                    to_char(s.date_order, 'MM') as month,
                    to_char(s.date_order, 'YYYY-MM-DD') as day,
                    s.partner_id as partner_id,
                    s.user_id as user_id,                    
                    s.company_id as company_id,
                    extract(epoch from avg(date_trunc('day',s.date_confirm)-date_trunc('day',s.create_date)))/(24*60*60)::decimal(16,2) as delay,
                    s.state,
                    t.categ_id as categ_id,
                    s.pricelist_id as pricelist_id,
                    s.project_id as analytic_account_id
                from
                    sale_order s
                    join sale_order_line l on (s.id=l.order_id)
                        left join product_product p on (l.product_id=p.id)
                            left join product_template t on (p.product_tmpl_id=t.id)
                    left join product_uom u on (u.id=l.product_uom)
                    left join product_uom u2 on (u2.id=t.uom_id)
                group by
                    l.fiscal_category_id,
                    l.fiscal_position,
                    l.product_id,
                    l.product_uom_qty,
                    l.order_id,
                    t.uom_id,
                    t.categ_id,
                    s.date_order,
                    s.date_confirm,
                    s.partner_id,
                    s.user_id,                   
                    s.company_id,
                    s.state,
                    s.pricelist_id,
                    s.project_id)
        """)
