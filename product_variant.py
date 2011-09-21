# -*- encoding: utf-8 -*-
from osv import fields, osv

import wizard
import decimal_precision as dp
import pooler
import time
from tools.translate import _
from osv import osv, fields
from tools.translate import _
import tools
import base64
from tempfile import TemporaryFile
from osv import osv, fields




class crea_articolo(osv.osv_memory):
    _name = 'crea.articolo'
    _description = 'Crea un articolo partendo dalle sue varianti definite '
    _columns = {
                'name': fields.many2one('product.template', 'Modello', required=True),
                'elenco_varianti':fields.one2many('crea.articolo.righe', 'testa', 'Righe Varianti Utilizzabili'),
    #            'marchio_id':fields.many2one('marchio.marchio', 'Marca', required=False),
         }
    
    def _get_modello(self, cr, uid, context=None):
      #  import pdb;pdb.set_trace()
        Modello = self.pool.get('stock.move')
        if context is None:
            context = {}              
        ids = context.get('active_ids', [])
        if ids:
            return ids[0]
        else:
            return None

    
    
    _defaults = {
                # 'name':_get_modello
                }
    
    def onchange_modello(self, cr, uid, ids, name):
       # import pdb;pdb.set_trace()
        v = {}
        vals = {
                'name':name,
                }
        # id_art = self.create(cr, uid, vals, {})
        param = [('product_tmpl_id', '=', name)]
        ids_dimension = self.pool.get("product.variant.dimension.type").search(cr, uid, param)
        if ids_dimension:
            elenco_varianti = []
            for id_dim in ids_dimension:
                desc = self.pool.get("product.variant.dimension.type").browse(cr, uid, [id_dim])[0].desc_type
                elenco_varianti.append({'Dimensione_id':id_dim, 'desc_type':desc, 'valore_id': None})
            v = {'name':name, 'elenco_varianti':elenco_varianti}
                
        #Dimension_ids 
        return {'value':v}
    
    def crea_articolo(self, cr, uid, ids, context=None):
        #import pdb;pdb.set_trace()
        car_art = self.browse(cr, uid, ids)[0]
        Template = car_art.name
        codice_product = Template.codice_template
        extra_prezzo = 0
        desvar = ''
        lista_variant_value = []
        first = True
        for variante in car_art.elenco_varianti:
         if variante.valore_id:  ## sole se ha assegnato un codice alla variante
            codice_product = codice_product + "-" + variante.valore_id.name
            if first:
                first = False
            else:
                desvar = desvar + "-"
            des_var = desvar + variante.Dimensione_id.name + ":" + variante.valore_id.name
            extra_prezzo = extra_prezzo + variante.valore_id.price_extra
            lista_variant_value.append(variante.valore_id.id)
        #import pdb;pdb.set_trace()
        Prodotto = {
                    'product_tmpl_id':car_art.name.id,
                    'dimension_value_ids': [(6, 0, tuple(lista_variant_value))],
                    'default_code':codice_product, #+ "-" + car_art.marchio_id.name,

                    'price_extra':extra_prezzo,

                    }
        id_Articolo = self.pool.get('product.product').create(cr, uid, Prodotto, {})
        #import pdb;pdb.set_trace()
        # Articolo = self.pool.get('product.product').browse(cr, uid, [id_Articolo])
        #import pdb;pdb.set_trace()
        ''' MEMENTANEAMENTE IN COMMENTO IN MODO CHE LA CREAZIONE DELLA DISTINTA ABBIA UN ULTERIORE 
        #PASSAGGIO IN WIZARD E CHE LA GENERAZIONE DELLA DISTINTA A WIZARD  POSSA ESSERE LANCIATA SEPARATAMENTE
        '''
        if id_Articolo:
		          ok_dist = self.genera_distinta(cr, uid, [id_Articolo], context)
        
        context.update({'product_id':id_Articolo})
        context.update({'active_id':id_Articolo})
        context.update({'active_ids':[id_Articolo]})
        return {
            'name': _('Prodotto'),
            'view_type': 'form',
            'view_mode': 'form,tree',
            'res_model': 'product.product',
            'res_id':context['product_id'],
            'view_id': False,
            'context': context,
            'type': 'ir.actions.act_window',
         }
        

        
        # return {'type': 'ir.actions.act_window_close'}
 

    def genera_distinta(self, cr, uid, ids, context=None):
      # VERIFICA CHE CI SIA LA DISTINTA BASE PER OGNI SINGOLO ARTICOLO DEL TEMPLATE SE C'È
      # VERIFICA ED EVENTUALMENTE AGGIUNGE LA RIGA DELLA DISTINTA DI TEMPLATE ALTRIMENTI CREA L'INTERA DISTINTA BASE PER L'ARTICOLO. 
        # legge i parametri
     #import pdb;pdb.set_trace()
     skeletro_id = self.pool.get('mrp.bom').search(cr, uid, [('type', '=', 'phantom'), ('bom_id', '=', 0)])
     if skeletro_id:  
      articoli = ids     
      if articoli:
         riga_bom = self.pool.get('mrp.bom').browse(cr, uid, skeletro_id)[0]
         for articolo_id in articoli:
           #import pdb;pdb.set_trace()
           # per ogni articolo cerca le distinte attive
           cerca = [('product_id', '=', articolo_id), ('bom_id', '=', 0), ('active', '=', True)]
           distinte = self.pool.get('mrp.bom').search(cr, uid, cerca)
           if distinte:
             # ci sono distinte
             for distinta_id in distinte:
                cerca = [('bom_id', '=', distinta_id), ('active', '=', True), ('product_id', '=', riga_bom.product_id.id)]
                righe_comp = self.pool.get('mrp.bom').search(cr, uid, cerca)
                if righe_comp:
                  # C'E' GIÀ LA RIGA CON L'ARTICOLO DISTINTA SKELETRO
                  #import pdb;pdb.set_trace()
                  pass
                else:
                  # aggiunge una riga alla distinta con la voce di skeletro
                  #import pdb;pdb.set_trace()
                  riga_distinta = {
                               'name':riga_comp.name,
                               'code':'',
                               'product_id':riga_comp.product_id.id,
                               'bom_id':distinta_id,
                               'type':'phantom',
                               'product_uom': riga_comp.product_id.uom_id.id,
                               }
                  riga_dist_id = self.pool.get('mrp.bom').create(cr, uid, riga_distinta)
           else:
             # non ci sono ditinte dell' articolo
             riga_art = self.pool.get('product.product').browse(cr, uid, [articolo_id])[0]

             testa_distinta = {
                               'name':riga_art.name,
                               'code':riga_art.default_code,
                               'product_id':riga_art.id,
                               'bom_id':0,
                               'product_uom': riga_art.uom_id.id,
                               }
             testa_id = self.pool.get('mrp.bom').create(cr, uid, testa_distinta)
             if testa_id:
                riga_comp = self.pool.get('product.product').browse(cr, uid, [riga_bom.product_id.id])[0]
                # scrive la riga componente fantasma
                riga_distinta = {
                               'name':riga_comp.name,
                               'code':'',
                               'product_id':riga_comp.id,
                               'bom_id':testa_id,
                               'type':'phantom',
                               'product_uom': riga_comp.uom_id.id,
                               }
                riga_dist_id = self.pool.get('mrp.bom').create(cr, uid, riga_distinta)
        
     return True


 
    
crea_articolo()


class crea_articolo_righe(osv.osv_memory):
    _name = 'crea.articolo.righe'
    _description = 'Dettaglio Varianti Sefinite '
    _columns = {
                'Dimensione_id': fields.many2one('product.variant.dimension.type', 'Dimensione', required=True, ondelete='cascade'),
                'desc_type':fields.related('Dimensione_id', 'desc_type', type='char', relation='rproduct.variant.dimension.type', string='Descrizione', store=True, readonly=True),
                'testa':fields.many2one('crea.articolo', 'Modello', required=True, ondelete='cascade', select=True,),
                'valore_id':fields.many2one('product.variant.dimension.value', 'Valore', required=False),
         }
    
    def onchange_valore(self, cr, uid, ids, name, elenco_varianti):
        #import pdb;pdb.set_trace()
        v = {}
        return {'value':v}

crea_articolo_righe()
