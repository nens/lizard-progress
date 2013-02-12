'''
Created on Jul 26, 2012

@author: ouayed
'''
from lxml import objectify
from StringIO import StringIO
import re
from django.contrib.gis.geos import Point,LineString,Polygon,LinearRing,MultiPolygon
from hdsr_controle.realtech_hdsr.models import hdsrHydrovakken, HdsrProfielen,HdsrMeetpunten,HdsrDWPProfielen


# metfile input : metfile bestand
#         output: Metfile object met
#                 reeksen
#                 ieder reeks heeft een aantal profielen
#                 ieder profiel heeft een aantal meetpunten

WATER_PUNT = '22'
SORTING_MEETPUNTEN = True
REEKS_TAG = 'REEKS'
PROFIEL_TAG = 'PROFIEL'
METING_TAG = 'METING'

def parsMetfile(metfile,project = None):
    #print "Open metfile in parsMetfile: " , metfile
    with open(metfile) as f:
        xml =  f.read()
    root = objectify.parse(StringIO('<ROOT>%s</ROOT>' % xml))
    m = Metfile()
    for e in root.getroot().getchildren():
        #print "e.tag: ", e.tag
        if(e.tag == REEKS_TAG):
            reeks= Reeks(e.text)
            m.add(reeks)
        elif(e.tag == PROFIEL_TAG):
            profiel = Profiel(e.text,reeks.name,e,project)
            reeks.add(profiel)
    return m


class Meeting():
    def __init__(self,str_meeting,profiel=None):
        r = re.split(',',str_meeting)
        if len(r) != 6:
            s= '%d Verkeerde aantal elementen in meetpunt: %s' % (len(r) , str_meeting)
            raise Exception(s)
        try:
            self.hdsr_meetpunt = HdsrMeetpunten(soort = r[0].strip(),
                                                profiel_id = profiel.id,
                                                boven_kant = float(r[5]),
                                                onder_kant = float(r[4]),
                                                geom = Point(float(r[2]),float(r[3]),srid=28992)
                                                )
        except Exception,e:
            s = 'Fout in de metfile bij profiel [%s] in Meeting [%s] exeption %s.' % profiel.profiel_naam,str_meeting,e
            raise Exception(s)

class Profiel():

    def __init__(self,str_profiel,reeksname = None,profiel_metingen = None,project = None):

        r = re.split(',',str_profiel)

        if len(r) != 11:
            s = 'Verkeerde aantal elementen in metfile bij profiel %s : ' %(str_profiel)
            raise Exception(s)

        self.profiel_naam =  r[0]
        self.op_peil =0
        self.geom = None
        self.hydrovak = None
        self.aantal_water_punten =0
        self.meetingen=[]
        self.dwp = None
        self.punt_22_1 =0
        self.punt_22_2 =0
        self.startx = 0

        try:
            self.startPunt = Point(float(r[8]),float(r[9]))
        except Exception,e:
            s = 'Parsing error in de metfile [%s] in startpunt van de profiel %s : %s ' % (len(r),str_profiel,self.profiel_naam, e)
            raise Exception( s)
        try:
            #print "profiel met reeks: ", reeksname br_ident is hydrocode
            self.hydrovak = hdsrHydrovakken.objects.filter( project = project ,br_ident = reeksname)[0]
        except IndexError:
            raise Exception(reeksname  + " is niet gevonden in hydrovakken shape" )
        try:
            self.dwp = HdsrDWPProfielen.objects.filter( hydro_code = reeksname,profiel_naam=self.profiel_naam)[0]
        except IndexError:
            raise Exception(reeksname + ' is niet gevonden in HdsrDWPProfielen shape')
        try:
            self.hdsr_profiel = HdsrProfielen.objects.create(profiel_naam=r[0],datum_opname=r[2],dwp =self.dwp,hydrovak = self.hydrovak)
        except Exception,e:
            s = 'Error parsing [%s] Exception: %s ' % (str_profiel, e)
            raise Exception(s)

        self.setMetingen(profiel_metingen)
        self.setProfielGeometries()
        self.setHydrovakHoeveelheiden()
        self.save()

    def add(self,meeting):
        self.meetingen.append(meeting)
        if meeting.hdsr_meetpunt.soort == WATER_PUNT and self.aantal_water_punten == 0:
            self.hdsr_profiel.op_peil = meeting.hdsr_meetpunt.boven_kant
            self.startx = self.startPunt.distance(meeting.hdsr_meetpunt.geom)
            self.aantal_water_punten = 1
            self.punt_22_1 = self.meetingen.index(meeting, )
        else:
            if meeting.hdsr_meetpunt.soort == WATER_PUNT and self.aantal_water_punten == 1:
                self.hdsr_profiel.geom = LineString(self.startPunt,meeting.hdsr_meetpunt.geom)
                self.hdsr_profiel.breedte =  self.hdsr_profiel.geom.length
                self.aantal_water_punten = 2
                self.punt_22_2 = self.meetingen.index(meeting, )

    def setMetingen(self,e):
        for meeting in e.getchildren():
                if(meeting.tag == METING_TAG):
                    meeting= Meeting(meeting.text,self.hdsr_profiel)
                    self.add(meeting)
        if self.aantal_water_punten != 2:
            raise Exception("Aantal 22 punten in de profiel moet twee zijn en gevonden : " + str(self.aantal_water_punten) )

    def setProfielGeometries(self):
        l = self.leggerGeom()
        lb = self.baggerGeom(sorting= SORTING_MEETPUNTEN)
        self.hdsr_profiel.leggergeom = l
        self.hdsr_profiel.baggergeom = lb

        lbgeom = l.intersection( lb)
        if not lbgeom.empty:
            if lbgeom.geom_type.lower() == 'polygon' :
                self.hdsr_profiel.leggerbaggergeom = MultiPolygon(lbgeom)
            elif lbgeom.geom_type.lower() == 'multipolygon' :
                self.hdsr_profiel.leggerbaggergeom =  lbgeom


    def setHydrovakHoeveelheiden(self):
        try:
            v = self.hydrovak.slib_vb_cl +  self.hdsr_profiel.baggergeom.area *  self.dwp.bep_afstand
            self.hydrovak.slib_vb_cl = round(v)
        except:
            pass
        try:
            o = self.hydrovak.slib_od_cl +  self.hdsr_profiel.leggerbaggergeom.area *  self.dwp.bep_afstand
            self.hydrovak.slib_od_cl = round(o)
        except:
            pass

        try:
            v = ((self.hydrovak.slib_vb_m3-self.hydrovak.slib_vb_cl)/self.hydrovak.slib_vb_m3) * 100
            self.hydrovak.slib_vb_pr = round(v)
        except ArithmeticError:
            self.hydrovak.slib_vb_pr =  self.hydrovak.slib_vb_cl
        else:
            pass

        try:
            o = ((self.hydrovak.slib_od_m3-self.hydrovak.slib_od_cl)/self.hydrovak.slib_od_m3) * 100
            self.hydrovak.slib_od_pr =round(o)
        except ArithmeticError:
            self.hydrovak.slib_od_pr = self.hydrovak.slib_od_cl
        else:
            pass


    def save(self):
        self.hydrovak.save()
        self.hdsr_profiel.save()
        for meeting in self.meetingen:
            meeting.hdsr_meetpunt.save()

    def leggerGeom(self):
        bbox=(self.startx,self.hydrovak.winterpeil ,self.hdsr_profiel.breedte, self.hydrovak.oh_d_nap)
        return Polygon.from_bbox(bbox)


    def baggerGeom(self,sorting):
        meetigen = [meeting for meeting in self.meetingen][self.punt_22_1:self.punt_22_2+1]
        meetingenGeom_boven = [Point(meeting.hdsr_meetpunt.geom.distance(self.startPunt), meeting.hdsr_meetpunt.boven_kant + self.op_peil) for meeting in meetigen]
        meetingenGeom_onder = [Point(meeting.hdsr_meetpunt.geom.distance(self.startPunt), meeting.hdsr_meetpunt.onder_kant + self.op_peil) for meeting in meetigen]
        if sorting:
            meetingenGeom_boven = sorted(meetingenGeom_boven,key = lambda Point:Point.x)
            meetingenGeom_onder = sorted(meetingenGeom_onder,key = lambda Point:Point.x,reverse=True)
        else:
            meetingenGeom_onder.reverse()

        meetingenGeom_boven.extend(meetingenGeom_onder)

        meetingenGeom_boven.append(meetingenGeom_boven[0])

        return Polygon(LinearRing(meetingenGeom_boven))

    def leggerBaggerGeom(self,lgeom,bgeom):
        return lgeom.intersection( bgeom.baggerGeom)

class Reeks:
    def __init__(self,reeks):
        try:
            r = re.split(',',reeks)
            p = re.compile('^\w-')
            self.name =p.sub("",r[0])
            self.omschrijving =r[1]
            self.profielen = []
        except Exception,e:
            raise e
    def add(self,profiel):
        self.profielen.append(profiel)

class Metfile:
    def __init__(self):
        self.metfile =[]
    def add(self,reeks):
        self.metfile.append(reeks)



