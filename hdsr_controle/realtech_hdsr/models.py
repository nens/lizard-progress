'''
Created on Jul 26, 2012

@author: ouayed
'''

# This is an auto-generated Django model module.
# You'll have to do the following manually to clean this up:
#     * Rearrange models' order
#     * Make sure each model has one field with primary_key=True
# Feel free to rename the models, but don't rename db_table values or field names.
#
# Also note: You'll have to insert the output of 'django-admin.py sqlcustom [appname]'
# into your database.

from django.contrib.gis.db import models

    
class HdsrGebruikers(models.Model):
    gebruiker_ref = models.TextField(blank=True)
    datum_aangemaakt = models.DateTimeField(auto_now_add=True, blank=True)
    class Meta:
        db_table = u'realtech_hdsr_gebruikers'
        get_latest_by = 'datum_aangemaakt'
        
class HdsrGebruikersProjecten(models.Model):
    project = models.TextField(blank=True) 
    gebruiker = models.ForeignKey(HdsrGebruikers, null=True, blank=True)
    datum_aangemaakt = models.DateTimeField(auto_now_add=True, blank=True)
    class Meta:
        db_table = u'realtech_hdsr_gebruikersprojecten'
        get_latest_by = 'datum_aangemaakt'

class HdsrDWPProfielen(models.Model):
    project = models.ForeignKey(HdsrGebruikersProjecten, null=True, blank=True)
    hydro_code = models.CharField(max_length=24)
    profiel_naam = models.CharField(max_length=20)
    datum_verw = models.DateTimeField(auto_now_add=True, blank=True)
    y = models.FloatField()
    x = models.FloatField()
    bep_afstand = models.IntegerField()
    geom = models.PointField(srid=28992)
    objects = models.GeoManager()
    class Meta:
        db_table = u'realtech_hdsr_DWPProfielen'
        get_latest_by = 'datum_verw'
    def __unicode__(self):
        return self.profiel_naam

class hdsrHydrovakken(models.Model):
    project = models.ForeignKey(HdsrGebruikersProjecten, null=True, blank=True)
    et_id = models.IntegerField()
    objectid = models.FloatField()
    br_ident = models.CharField(max_length=24)
    br_status = models.IntegerField()
    br_vaktype = models.IntegerField()
    naam_wtrg = models.CharField(max_length=50)
    monstervak = models.CharField(max_length=4)
    bag_gebied = models.CharField(max_length=25)
    naam_ing_b = models.CharField(max_length=25)
    rapport = models.CharField(max_length=25)
    towabo = models.CharField(max_length=25)
    datum_expt = models.DateField()
    datum_bemo = models.DateField()
    datum_impt = models.DateField()
    datum_verv = models.DateField()
    lengte = models.FloatField()
    breedte_mv = models.FloatField()
    oppervlak = models.FloatField()
    waterstand = models.FloatField()
    winterpeil = models.FloatField()
    waterdiept = models.FloatField()
    br_diepte = models.FloatField()
    br_d_nap = models.FloatField()
    overdiepte = models.FloatField()
    oh_d_nap = models.FloatField()
    sliblgdikt = models.FloatField()
    slib_ld_m3 = models.IntegerField()
    slib_od_m3 = models.IntegerField()
    slib_vb_m3 = models.IntegerField()

    slib_vb_cl = models.IntegerField(default=0)
    slib_od_cl = models.IntegerField(default=0)
    slib_vb_pr =models.FloatField(default=0) 
    slib_od_pr =models.FloatField(default=0)
    
    datum_verw = models.DateTimeField(auto_now_add=True, blank=True)

    vb_alarm = models.CharField(max_length=8)
    grondsoort = models.CharField(max_length=3)
    slibsoort = models.CharField(max_length=3)
    opmerking1 = models.CharField(max_length=254)
    voor_wabo = models.CharField(max_length=1)
    voor_asbes = models.CharField(max_length=1)
    ver_asbest = models.CharField(max_length=1)
    na_asbest = models.CharField(max_length=1)
    eind_nw4 = models.IntegerField()
    bep_nw4 = models.CharField(max_length=50)
    vers_mspaf = models.CharField(max_length=10)
    bbk_wabo = models.CharField(max_length=10)
    bep_bbk_wb = models.CharField(max_length=254)
    over_iw_wb = models.CharField(max_length=1)
    sanering = models.CharField(max_length=1)
    bbk_labo = models.CharField(max_length=10)
    bep_bbk_lb = models.CharField(max_length=254)
    over_iw_lb = models.CharField(max_length=1)
    opm_toe_lb = models.CharField(max_length=254)
    veiligheid = models.CharField(max_length=5)
    bep_t_klas = models.CharField(max_length=254)
    bestek_nr = models.CharField(max_length=15)
    bestek_m3 = models.IntegerField()
    gebag_m3 = models.IntegerField()
    m3_per_m = models.FloatField()
    start_datu = models.DateField()
    eind_datum = models.DateField()
    bag_method = models.CharField(max_length=15)
    afvoer = models.CharField(max_length=15)
    bestemming = models.CharField(max_length=20)
    opmerking2 = models.CharField(max_length=254)
    ds = models.FloatField()
    ostof = models.FloatField()
    gloeirest = models.FloatField()
    humus = models.FloatField()
    calciet = models.FloatField()
    kgf_2 = models.FloatField()
    kgf_16 = models.FloatField()
    kgf_32 = models.FloatField()
    kgf_63 = models.FloatField()
    grondfr_2 = models.FloatField()
    ars = models.FloatField()
    ba = models.FloatField()
    cd = models.FloatField()
    co = models.FloatField()
    cu = models.FloatField()
    hg = models.FloatField()
    pb = models.FloatField()
    mo = models.FloatField()
    ni = models.FloatField()
    zn = models.FloatField()
    aldn = models.FloatField()
    dieldn = models.FloatField()
    aldn_dield = models.FloatField()
    endn = models.FloatField()
    idn = models.FloatField()
    teldn = models.FloatField()
    sdrin3 = models.FloatField()
    ddt24 = models.FloatField()
    ddt44 = models.FloatField()
    sddt = models.FloatField()
    ddd24 = models.FloatField()
    ddd44 = models.FloatField()
    sddd = models.FloatField()
    dde24 = models.FloatField()
    dde44 = models.FloatField()
    sdde = models.FloatField()
    spestbbk = models.FloatField()
    aedsfn = models.FloatField()
    bedsfn = models.FloatField()
    endosulf = models.FloatField()
    ahch = models.FloatField()
    bhch = models.FloatField()
    chch = models.FloatField()
    shch4 = models.FloatField()
    hpcl = models.FloatField()
    hxclbtden = models.FloatField()
    cldn = models.FloatField()
    hpclepo = models.FloatField()
    hpcl_clepo = models.FloatField()
    pcb28 = models.FloatField()
    pcb52 = models.FloatField()
    pcb101 = models.FloatField()
    pcb118 = models.FloatField()
    pcb138 = models.FloatField()
    pcb153 = models.FloatField()
    pcb180 = models.FloatField()
    spcb6 = models.FloatField()
    spcb7 = models.FloatField()
    mcb = models.FloatField()
    s_dcb = models.FloatField()
    s_t3cb = models.FloatField()
    s_t4cb = models.FloatField()
    qcb = models.FloatField()
    hcb = models.FloatField()
    som_cb = models.FloatField()
    naf = models.FloatField()
    acny = models.FloatField()
    acne = models.FloatField()
    fle = models.FloatField()
    fen = models.FloatField()
    ant = models.FloatField()
    flu = models.FloatField()
    pyr = models.FloatField()
    baa = models.FloatField()
    chr = models.FloatField()
    bbf = models.FloatField()
    bkf = models.FloatField()
    bap = models.FloatField()
    dbahant = models.FloatField()
    bghipe = models.FloatField()
    inp = models.FloatField()
    pak10 = models.FloatField()
    pak16 = models.FloatField()
    moc10c12g = models.FloatField()
    moc22c30g = models.FloatField()
    moc30c40g = models.FloatField()
    minrole = models.FloatField()
    geometrie1 = models.IntegerField()
    geom = models.MultiLineStringField(srid=28992)
    objects = models.GeoManager()
    class Meta:
        db_table = u'realtech_hdsr_hydrovakken'
        get_latest_by = 'datum_verw'
    def __unicode__(self):
        return self.br_ident
           
class HdsrProfielen(models.Model):
    profiel_naam = models.TextField(blank=True)
    hydrovak = models.ForeignKey(hdsrHydrovakken, null=True, blank=True)
    dwp = models.ForeignKey(HdsrDWPProfielen, null=True, blank=True)
    op_peil = models.DecimalField(null=True, max_digits=5, decimal_places=3, blank=True)
    pol_peil = models.DecimalField(null=True, max_digits=5, decimal_places=3, blank=True)
    breedte = models.DecimalField(null=True, max_digits=6, decimal_places=3, blank=True)
    datum_opname = models.CharField(max_length=8, blank=True)
    datum_aangemaakt = models.DateTimeField(auto_now_add=True, blank=True)
    geom = models.LineStringField(srid=28992,null=True, blank=True)
    leggergeom = models.PolygonField(srid=28992,null=True)
    baggergeom = models.PolygonField(srid=28992,null=True)    
    leggerbaggergeom  = models.MultiPolygonField(srid=28992,null=True)
    objects = models.GeoManager()
    class Meta:
        db_table = u'realtech_hdsr_profielen'
        get_latest_by = 'datum_aangemaakt'
    def __unicode__(self):
        return self.profiel_naam
        
class HdsrMeetpunten(models.Model):
    profiel = models.ForeignKey(HdsrProfielen, null=True, blank=True)
    boven_kant = models.DecimalField(null=True, max_digits=6, decimal_places=3, blank=True)
    onder_kant = models.DecimalField(null=True, max_digits=6, decimal_places=3, blank=True)
    soort = models.CharField(max_length=4, blank=True)
    datum_aangemaakt = models.DateTimeField(auto_now_add=True, blank=True)
    geom = models.PointField(srid=28992)
    objects = models.GeoManager()
    class Meta:
        db_table = u'realtech_hdsr_meetpunten'
        get_latest_by = 'datum_aangemaakt'
    def __unicode__(self):
        return self.meetpunt_id
    
# Auto-generated `LayerMapping` dictionary for realtech_hdsr_profielen_repaf model
realtech_hdsr_DWPProfielen_mapping = {
    'hydro_code' : 'OVKIDENT',
    'profiel_naam' : 'ID_DWP',
    'y' : 'Y',
    'x' : 'X',
    'bep_afstand' : 'REP_LENGTE',
    'geom' : 'POINT',
}

# Auto-generated `LayerMapping` dictionary for realtech_hdsr_hydrovakken model
realtech_hdsr_Hydrovakken_mapping = {
    'et_id' : 'ET_ID',
    'objectid' : 'OBJECTID',
    'br_ident' : 'BR_IDENT',
    'br_status' : 'BR_STATUS',
    'br_vaktype' : 'BR_VAKTYPE',
    'naam_wtrg' : 'NAAM_WTRG',
    'monstervak' : 'MONSTERVAK',
    'bag_gebied' : 'BAG_GEBIED',
    'naam_ing_b' : 'NAAM_ING_B',
    'rapport' : 'RAPPORT',
    'towabo' : 'TOWABO',
    'datum_expt' : 'DATUM_EXPT',
    'datum_bemo' : 'DATUM_BEMO',
    'datum_impt' : 'DATUM_IMPT',
    'datum_verv' : 'DATUM_VERV',
    'lengte' : 'LENGTE',
    'breedte_mv' : 'BREEDTE_MV',
    'oppervlak' : 'OPPERVLAK',
    'waterstand' : 'WATERSTAND',
    'winterpeil' : 'WINTERPEIL',
    'waterdiept' : 'WATERDIEPT',
    'br_diepte' : 'BR_DIEPTE',
    'br_d_nap' : 'BR_D_NAP',
    'overdiepte' : 'OVERDIEPTE',
    'oh_d_nap' : 'OH_D_NAP',
    'sliblgdikt' : 'SLIBLGDIKT',
    'slib_ld_m3' : 'SLIB_LD_M3',
    'slib_od_m3' : 'SLIB_OD_M3',
    'slib_vb_m3' : 'SLIB_VB_M3',
    'vb_alarm' : 'VB_ALARM',
    'grondsoort' : 'GRONDSOORT',
    'slibsoort' : 'SLIBSOORT',
    'opmerking1' : 'OPMERKING1',
    'voor_wabo' : 'VOOR_WABO',
    'voor_asbes' : 'VOOR_ASBES',
    'ver_asbest' : 'VER_ASBEST',
    'na_asbest' : 'NA_ASBEST',
    'eind_nw4' : 'EIND_NW4',
    'bep_nw4' : 'BEP_NW4',
    'vers_mspaf' : 'VERS_MSPAF',
    'bbk_wabo' : 'BBK_WABO',
    'bep_bbk_wb' : 'BEP_BBK_WB',
    'over_iw_wb' : 'OVER_IW_WB',
    'sanering' : 'SANERING',
    'bbk_labo' : 'BBK_LABO',
    'bep_bbk_lb' : 'BEP_BBK_LB',
    'over_iw_lb' : 'OVER_IW_LB',
    'opm_toe_lb' : 'OPM_TOE_LB',
    'veiligheid' : 'VEILIGHEID',
    'bep_t_klas' : 'BEP_T_KLAS',
    'bestek_nr' : 'BESTEK_NR',
    'bestek_m3' : 'BESTEK_M3',
    'gebag_m3' : 'GEBAG_M3',
    'm3_per_m' : 'M3_PER_M',
    'start_datu' : 'START_DATU',
    'eind_datum' : 'EIND_DATUM',
    'bag_method' : 'BAG_METHOD',
    'afvoer' : 'AFVOER',
    'bestemming' : 'BESTEMMING',
    'opmerking2' : 'OPMERKING2',
    'ds' : 'DS',
    'ostof' : 'OSTOF',
    'gloeirest' : 'GLOEIREST',
    'humus' : 'HUMUS',
    'calciet' : 'CALCIET',
    'kgf_2' : 'KGF_2',
    'kgf_16' : 'KGF_16',
    'kgf_32' : 'KGF_32',
    'kgf_63' : 'KGF_63',
    'grondfr_2' : 'GRONDFR_2',
    'ars' : 'ARS',
    'ba' : 'BA',
    'cd' : 'CD',
    'co' : 'CO',
    'cu' : 'CU',
    'hg' : 'HG',
    'pb' : 'PB',
    'mo' : 'MO',
    'ni' : 'NI',
    'zn' : 'ZN',
    'aldn' : 'ALDN',
    'dieldn' : 'DIELDN',
    'aldn_dield' : 'ALDN_DIELD',
    'endn' : 'ENDN',
    'idn' : 'IDN',
    'teldn' : 'TELDN',
    'sdrin3' : 'SDRIN3',
    'ddt24' : 'DDT24',
    'ddt44' : 'DDT44',
    'sddt' : 'SDDT',
    'ddd24' : 'DDD24',
    'ddd44' : 'DDD44',
    'sddd' : 'SDDD',
    'dde24' : 'DDE24',
    'dde44' : 'DDE44',
    'sdde' : 'SDDE',
    'spestbbk' : 'SPESTBBK',
    'aedsfn' : 'AEDSFN',
    'bedsfn' : 'BEDSFN',
    'endosulf' : 'ENDOSULF',
    'ahch' : 'AHCH',
    'bhch' : 'BHCH',
    'chch' : 'CHCH',
    'shch4' : 'SHCH4',
    'hpcl' : 'HPCL',
    'hxclbtden' : 'HXCLBTDEN',
    'cldn' : 'CLDN',
    'hpclepo' : 'HPCLEPO',
    'hpcl_clepo' : 'HPCL_CLEPO',
    'pcb28' : 'PCB28',
    'pcb52' : 'PCB52',
    'pcb101' : 'PCB101',
    'pcb118' : 'PCB118',
    'pcb138' : 'PCB138',
    'pcb153' : 'PCB153',
    'pcb180' : 'PCB180',
    'spcb6' : 'SPCB6',
    'spcb7' : 'SPCB7',
    'mcb' : 'MCB',
    's_dcb' : 'S_DCB',
    's_t3cb' : 'S_T3CB',
    's_t4cb' : 'S_T4CB',
    'qcb' : 'QCB',
    'hcb' : 'HCB',
    'som_cb' : 'SOM_CB',
    'naf' : 'NAF',
    'acny' : 'ACNY',
    'acne' : 'ACNE',
    'fle' : 'FLE',
    'fen' : 'FEN',
    'ant' : 'ANT',
    'flu' : 'FLU',
    'pyr' : 'PYR',
    'baa' : 'BAA',
    'chr' : 'CHR',
    'bbf' : 'BBF',
    'bkf' : 'BKF',
    'bap' : 'BAP',
    'dbahant' : 'DBAHANT',
    'bghipe' : 'BGHIPE',
    'inp' : 'INP',
    'pak10' : 'PAK10',
    'pak16' : 'PAK16',
    'moc10c12g' : 'MOC10C12G',
    'moc22c30g' : 'MOC22C30G',
    'moc30c40g' : 'MOC30C40G',
    'minrole' : 'MINROLE',
    'geometrie1' : 'GEOMETRIE1',
    'geom' : 'MULTILINESTRING',
}
