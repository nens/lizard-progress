'''
Created on Aug 1, 2012

@author: ouayed
'''

import logging,os
import hdsr_controle.realtech_hdsr.models as model
from django.contrib.gis.utils import LayerMapping,LayerMapError
from django.db import transaction,IntegrityError
from django.utils.datetime_safe import datetime
from hdsr_controle.realtech_hdsr import export
from metfileparser import metfileparser

DATA_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), 'data'))
ROOT_PATH = os.path.abspath(os.path.dirname(__file__))

HYDROVAKKEN_TAG = "Hydrovakken_"
PROFIELEN_TAG = "DWP_"
METFILE_TAG = ".met"
SHAPEFILE_TAG =".shp"


logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s %(levelname)-8s %(name)-12s  %(message)s',
                    datefmt='%m-%d %H:%M',
                    filename= os.path.join( ROOT_PATH ,'log.txt'),
                    filemode='w')

console = logging.StreamHandler()
console.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(name)s - %(message)s')
console.setFormatter(formatter)
logger = logging.getLogger('')
logger.setLevel(logging.INFO)
logging.getLogger('').addHandler(console)


def save(obj):
    try:
        obj.save()
    except IntegrityError:
        transaction.rollback()
    else:
        transaction.commit()

class projectData:

    def __init__(self,projectnaam,gebruiker=None,gebruikFoldersIndeling=True,datafolder=DATA_PATH):


        self.name = projectnaam
        self.profielenShapes =[]
        self.hydrovakkenShapes = []
        self.metBestanden   = []
        self.klant_id=0
        self.datafolder=datafolder
        if gebruikFoldersIndeling:
            self.setDataFoldersIndeling(gebruiker)

    def setDataFoldersIndeling(self,gebruiker):
        try:
            self.project,created = model.HdsrGebruikersProjecten.objects.get_or_create(gebruiker = gebruiker,project =  os.path.basename(self.name))
            if not created:
                raise Exception( "Kan het project " + self.projectpath + " niet aanmaken")
            for root, _ , filenames in os.walk(os.path.join(self.datafolder, self.name)):
                for filename in filenames:
                    if filename.endswith(SHAPEFILE_TAG):
                        if filename.startswith(PROFIELEN_TAG):
                            self.profielenShapes.append(os.path.join(root, filename))
                        if filename.startswith(HYDROVAKKEN_TAG):
                            self.hydrovakkenShapes.append(os.path.join(root, filename))
                    if filename.endswith(METFILE_TAG):
                        self.metBestanden.append(os.path.join(root, filename))
        except Exception,e:
            self.load_log = logging.getLogger("projectData")
            self.load_log.exception(e)
            raise

class gebruikerData:

    def __init__(self,gebruikernaam,gebruikFoldersIndeling=True,datafolder=DATA_PATH):
        self.name = gebruikernaam
        self.projecten=[]
        self.datafolder=datafolder
        if gebruikFoldersIndeling:
                self.setDataFoldersIndeling()

    def setDataFoldersIndeling(self):
        try:
            self.gebruiker,created = model.HdsrGebruikers.objects.get_or_create (gebruiker_ref = self.name)
            if not created:
                raise Exception("Kan de aannemer " + self.name + " niet aanmaken!")
            for l in os.listdir(os.path.join(self.datafolder,self.name)):
                if os.path.isdir(os.path.join(self.datafolder,os.path.join(self.name,l))):
                    self.projecten.append(projectData(gebruiker=self.gebruiker,projectnaam=os.path.join(self.name,l)))
        except Exception,e:
            self.load_log = logging.getLogger('gebruikerData')
            self.load_log.exception("laden data voor aannemer " + self.name)
            raise e

def loadGebruikersData(datafolder):
    load_log = logging.getLogger('loadGebruikersData')
    load_log.info("datapath: " + datafolder)
    data =[]
    try:
        for f in os.listdir(datafolder):
            if os.path.isdir(os.path.join(datafolder,f)):
                g = gebruikerData(gebruikernaam=f)
                data.append(g)
    except Exception,e:
        raise (e)
    return data

def saveShapeFile(model,data,mapping,verbose,project,beginTime):
    load_log = logging.getLogger('saveShapeFile')
    try:

        lm = LayerMapping(model, data, mapping,transform=False, encoding='iso-8859-1')

        lm.save(strict=True, verbose=verbose)
        model.objects.filter(datum_verw__gte = beginTime,project = None).update(project=project.project)
    except LayerMapError,e:
        load_log.error("Kolommen komen niet overeen met de shapebestand: " + os.path.basename(data) )
        raise e
    except Exception,e:

        load_log.info("mappen datamodel met de shapebestand: "+ data)
        load_log.exception(e)
        raise e

def loadshapefiles(verbose,gebruikersdata):

    load_log = logging.getLogger('loadshapefiles')

    for gebruiker in gebruikersdata:
        load_log.info("laden shape bestanden voor gebruiker: " + gebruiker.name)
        for project in gebruiker.projecten:
            load_log.info("laden shape bestanden voor project: " + project.name)
            beginTime = datetime.now()
            for shapefile in project.hydrovakkenShapes:
                saveShapeFile(model.hdsrHydrovakken, shapefile, model.realtech_hdsr_Hydrovakken_mapping, verbose, project, beginTime)
            for shapefile in project.profielenShapes:
                saveShapeFile(model.HdsrDWPProfielen, shapefile, model.realtech_hdsr_DWPProfielen_mapping, verbose, project, beginTime)


def exportHydrovakken(gebruikersdata):
    for gebruiker in gebruikersdata:
        for project in gebruiker.projecten:
            for shapefile in project.hydrovakkenShapes:
                export.ShpResponder(queryset=model.hdsrHydrovakken.objects.filter(project=project.project), file_name= shapefile,geo_field=None, proj_transform=None)

def loadmetfiles(gebruikersdata):
    for gebruiker in gebruikersdata:
        for project in gebruiker.projecten:
            model.hdsrHydrovakken.objects.filter(project=project.project).update(slib_vb_cl=0,slib_od_cl=0)
            for metfile in project.metBestanden:
                metfileparser.parsMetfile(metfile,project.project)

def controleren(hydrovakkenshapefile,dwpshapefile,metfile,projectnaam="dummyProject",aannemer="dummyAannemer",verwijderOudeData=True):
    """
      Input:
          hydrovakkenshapefile = hydrovakken shape bestand zoals ./Hydrovakken_TestProject.shp
          dwpshapefile = dwp profielen shape bestand zoals ./DWP_TestProject.shp
          metfile = metfile bestand  zoals ./Metfile_TestProject.met
          projectnaam = naam van het project
          aannemer = naam van de aannemer
          verwijderOudeData: wordt gebruikt om hdsr controletabellen leeg te maken.
                             volgende tabellen worden hiermee leeg gemaakt:
                                -model.HdsrMeetpunten
                                -model.HdsrProfielen
                                -model.hdsrHydrovakken
                                -model.HdsrDWPProfielen
                                -model.HdsrGebruikersProjecten
                                -model.HdsrGebruikers
    """

    load_log = logging.getLogger('controleren')
    dataOntbreekt=""
    if not os.path.exists(hydrovakkenshapefile):
        dataOntbreekt = 'Hydrovakken shape %s bestaat niet!\n' % hydrovakkenshapefile
    elif not os.path.exists(dwpshapefile):
        dataOntbreekt = dataOntbreekt +  'DWP profielen shape %s bestaat niet!\n' % dwpshapefile
    elif  not os.path.exists(metfile):
        dataOntbreekt = dataOntbreekt +  'Metfile %s bestaat niet!\n' % metfile

    if dataOntbreekt != "":
        load_log.exception(dataOntbreekt)
        return
    try:


        truncateTables(verwijderOudeData)
        data =[]
        gebruiker,created = model.HdsrGebruikers.objects.get_or_create (gebruiker_ref = aannemer)
        if not created:
            raise Exception( "Kan de aannemer " + aannemer + " niet aanmaken")

        project,created = model.HdsrGebruikersProjecten.objects.get_or_create(gebruiker = gebruiker,project =  projectnaam)
        if not created:
            raise Exception( "Kan het project " + projectnaam + " niet aanmaken")

        projectdata = projectData(projectnaam=projectnaam, gebruiker=gebruiker,gebruikFoldersIndeling=False)
        projectdata.project = project
        projectdata.profielenShapes.append(dwpshapefile)
        projectdata.hydrovakkenShapes.append(hydrovakkenshapefile)
        projectdata.metBestanden.append(metfile)

        gebruikerdata = gebruikerData(gebruikernaam= aannemer,gebruikFoldersIndeling=False)

        gebruikerdata.projecten.append(projectdata)
        data.append(gebruikerdata)

        loadshapefiles(False,data)
        loadmetfiles(data)
        exportHydrovakken(data)
    except Exception,e :
        load_log.error("ERROR")
        load_log.exception(e)

#@transaction.commit_manually
def datafolder_controleren(verwijderOudeData=True,datafolder= DATA_PATH):
    """
       Data laden en controleren uit een gegeven folder default is het ./data.
       In de datafolder dienen folders staan in het volgende hierarchie
       data -> klant_1
                   project_1
                       hydrovakken shapebestanden
                       dwg profielen shapebestanden
                       en metfiles
                   project_2
                   ...
            -  klant_2
            ...

        De databestaden moeten beginnen met volgende prefixen
        HYDROVAKKEN_TAG = "Hydrovakken_"
        PROFIELEN_TAG = "DWP_"
        METFILE_TAG = ".met"
        SHAPEFILE_TAG =".shp"
    """
    load_log = logging.getLogger('Load')
    if not os.path.exists(datafolder):
        load_log.exception(datafolder + " bestaat niet!")
        return
    try:
        load_log.info("Data laden uit de map structuur")
        truncateTables(verwijderOudeData)
        load_log.info("laden gebruikers data uit data folder")
        GEBRUIKERS_DATA = loadGebruikersData(datafolder)
        load_log.info("export shape bestanden hydovakken en dwpprofielen")
        loadshapefiles(True,GEBRUIKERS_DATA)
        load_log.info("export MET-FILES")
        loadmetfiles(GEBRUIKERS_DATA)
        exportHydrovakken(GEBRUIKERS_DATA)
        load_log.info("Klaar")
    except Exception,e :
        load_log.error("ERROR")
        load_log.exception(e)

def truncateTables(verwijderOudeData=True):
    if verwijderOudeData:
        model.HdsrMeetpunten.objects.all().delete()
        model.HdsrProfielen.objects.all().delete()
        model.hdsrHydrovakken.objects.all().delete()
        model.HdsrDWPProfielen.objects.all().delete()
        model.HdsrGebruikersProjecten.objects.all().delete()
        model.HdsrGebruikers.objects.all().delete()

def test_controleren():
    datapath = '/home/ouayed/Documents/pydev_ws/hdsr_controle/realtech_hdsr/data/klant1/project1/'
    controleren(
            projectnaam = "hdsr",
            aannemer="ouayed",
            hydrovakkenshapefile='%s%s' % (datapath,'Hydrovakken_TestProject.shp'),
            dwpshapefile='%s%s' % (datapath,'DWP_TestProject.shp'),
            metfile='%s%s' % (datapath,'Metfile_TestProject.met'),
            verwijderOudeData=True
            )



