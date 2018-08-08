var locTypes = {
    'manhole':'Put',
    'pipe':'Streng',
    'drain':'Kolk',
    'point': ''
};

var locStatuses = {
    'complete': {status: 'Compleet', color: 'limegreen', opacity: 0.75},
    'incomplete': {status: 'Niet (geheel) aanwezig en niet gepland', color: 'red', opacity: 0.75},
    'sched_incomplete': {status: 'Gepland, nog niet compleet', color: 'black', opacity: 0.75},
    'overdue': {status: 'Gepland, niet compleet en\n planningsdatum verstreken', color: 'gold', opacity: 0.75},
    'notproject': {status: 'Geen onderdeel van werkzaamheden', color: 'gray', opacity: 0.75},
    'auto_new': {status: 'Nieuw object (automatisch toegevoegd)', color: 'MediumPurple', opacity: 0.75},
    'auto_skipped': {status: 'Niet behandeld (automatisch toegevoegd)', color: 'brown', opacity: 0.75},
    'unknown': {status: 'Onbekend', color: 'fuchsia', opacity: 0.6}
};

var reqTypes = {
    1: 'Locatiecode verwijderen',
    2: 'Locatie verplaatsen',
    3: 'Nieuwe locatiecode'
};

/* altColor will be used to mark moving requests' original locations */
var reqStatuses = {
    1: {status: 'Open', color: 'blueviolet', altColor: 'blueviolet', opacity: 0.75},
    2: {status: 'Geaccepteerd', color: 'green', altColor: 'darkgreen', opacity: 0.75},
    3: {status: 'Geweigerd, ingetrokken of ongeldig', color: 'mediumvioletred', altColor: 'mediumvioletred', opacity: 0.75},
    4: {status: 'Ingetrokken', color: 'mediumvioletred', altColor: 'mediumvioletred', opacity: 0.75},
    5: {status: 'Ongeldig', color: 'mediumvioletred', altColor: 'mediumvioletred', opacity: 0.75}
};

/* base map variants */
var providers = ['osm', 'cartolight', 'stamen.tonerlite',
		 'osmnolabels', 'nlmapspastel', 'nlmapsstandaard',
		 'openmapserfer.grayscale'];
var providerData = {
    'osm': {
	tile: 'http://{s}.tile.osm.org/{z}/{x}/{y}.png',
	attr: '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
    },
    'osmnolabels': {
	tile: 'https://tiles.wmflabs.org/osm-no-labels/{z}/{x}/{y}.png',
	attr: '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
    },
    'cartolight': {
	tile: 'https://cartodb-basemaps-{s}.global.ssl.fastly.net/light_all/{z}/{x}/{y}.png',
	attr: 'Map tiles by Carto, under CC BY 3.0. Data by OpenStreetMap, under ODbL.'
    },
    'nlmapspastel': {
	tile: 'https://geodata.nationaalgeoregister.nl/tiles/service/wmts/brtachtergrondkaartpastel/EPSG:3857/{z}/{x}/{y}.png',
	attr: 'Kaartgegevens &copy; <a href="kadaster.nl">Kadaster</a>'
    },
    'nlmapsstandaard': {
	tile: 'https://geodata.nationaalgeoregister.nl/tiles/service/wmts/brtachtergrondkaart/EPSG:3857/{z}/{x}/{y}.png',
	attr: 'Kaartgegevens &copy; <a href="kadaster.nl">Kadaster</a>'
    },
    'stamen.tonerlite': {
	tile: 'https://stamen-tiles-{s}.a.ssl.fastly.net/toner-lite/{z}/{x}/{y}{r}.png',
   	attribution: 'Map tiles by <a href="http://stamen.com">Stamen Design</a>, <a href="http://creativecommons.org/licenses/by/3.0">CC BY 3.0</a> &mdash; Map data &copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    },
    'opentopomap': {
	tile: 'https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png',
	attr: 'Map data: &copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>, <a href="http://viewfinderpanoramas.org">SRTM</a> | Map style: &copy; <a href="https://opentopomap.org">OpenTopoMap</a> (<a href="https://creativecommons.org/licenses/by-sa/3.0/">CC-BY-SA</a>)'
    },
    'openmapserfer.grayscale': {
	tile: 'https://korona.geog.uni-heidelberg.de/tiles/roadsg/x={x}&y={y}&z={z}',
	attr: 'Imagery from <a href="http://giscience.uni-hd.de/">GIScience Research Group @ University of Heidelberg</a> &mdash; Map data &copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>'
    },
    'openinfrawater': {
	tile: 'https://geodata.nationaalgeoregister.nl/tiles/service/wmts/brtachtergrondkaart/EPSG:3857/{z}/{x}/{y}.png',
	attr: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>, <a href="http://www.openinframap.org/about.html">About OpenInfraMap</a>'
    }
};

var mymap, popup;
var currBounds = [[],[]];
var dynamicLegendColors = {'locations': [], 'requests': []};
var dynamicLegend = {'locations': [], 'requests': []};
var MAXZOOM = 18;
var globalDummyArr = [];

/***/
/* base map handlers */
function currBase() {
    if (window._currBase === undefined) {
	window._currBase = 0;
    }
    return window._currBase;
}
function nextBase() {
    mymap.attributionControl._attributions = {};
    var base = providerData[providers[window._currBase]];
    var baseLayer = L.tileLayer(base.tile, {
	attribution: base.attr,
	maxZoom: MAXZOOM
    });

    window._currBase = (currBase() + 1 ) % (providers.length);
    base = providerData[providers[window._currBase]];
    var newbaseLayer = L.tileLayer(base.tile, {
	attribution: base.attr,
	maxZoom: MAXZOOM
    });
    var baseMaps = {
	"Street map": newbaseLayer
    };
    mymap.removeLayer(baseLayer);
    newbaseLayer.addTo(mymap);
}

/***/
/* tabbed popup functions */
function reloadGraphs(max_image_width, callback, force) {
    // New Flot graphs
    $('.dynamic-graph').each(function () {
        reloadDynamicGraph($(this), callback, force);
    });
}
function openTab(evt, tab, lat, lng) {
    var i, tabcontent, tablinks;

    // Get all elements with class="tabcontent" and hide them
    tabcontent = document.getElementsByClassName("tabcontent");
    for (i=0; i<tabcontent.length; i++) {
	tabcontent[i].style.display = "none";
    }

    // Get all elements with class="tablinks" and remove the class "active"
    tablinks = document.getElementsByClassName("tablinks");
    for (i = 0; i < tablinks.length; i++) {
	tablinks[i].className = tablinks[i].className.replace(" active", "");
    }

    // Show the current tab, and add an "active" class to the link that opened the tab
    document.getElementById('popup-tab-' + tab.toString()).style.display = "block";
    evt.currentTarget.className += " active";
    popup.setLatLng([lat, lng]);
    reloadGraphs();
} 
function reloadDynamicGraph($graph, callback, force) {
    // check if graph is already loaded
    if (force !== true && $graph.attr('data-graph-loaded')) return;

    // the wonders of asynchronous programming
    if ($graph.attr('data-graph-loading')) return;

    // check if element is visible (again):
    // flot can't draw on an invisible surface
    if ($graph.is(':hidden')) return;

    // determine whether to use flot or the image graph
    var url = $graph.attr('data-image-graph-url');
    if (url) {
        // add a spinner
        var $loading = $('<img src="/static_media/lizard_ui/ajax-loader.gif" class="graph-loading-animation" />');
        $graph.empty().append($loading);
        $graph.attr('data-graph-loading', 'true');

        // remove spinner when loading has finished (either with or without an error)
        var on_loaded = function () {
            $graph.removeAttr('data-graph-loading');
            $loading.remove();
        };

        // set attribute and call callback when drawing has finished
        var on_drawn = function () {
            $graph.attr('data-graph-loaded', 'true');
            if (callback !== undefined) {
                callback();
            }
        };

	var on_empty = function() {
            on_loaded();
            $graph.html('Voor deze locatie is er geen data anwezig in het systeem.');
	}
	
        // show a message when loading has failed
        var on_error = function () {
            on_loaded();
	    // Assuming the image is empty because there is no data
	    on_empty();
        };

        var get_url_with_size = function () {
            // compensate width slightly to prevent a race condition
            // with the parent element
            var width = Math.round($graph.width() * 0.95);
            // add available width and height to url
            var url_with_size = url + '&' + $.param({
                width: width,
                height: $graph.height()
            });
            return url_with_size;
        };

        var update_size = function () {
            var $img = $(this);
            $img.data('current-loaded-width', $img.width());
            $img.data('current-loaded-height', $img.height());
        };

        var on_load_once = function () {
            on_loaded();

            // tab might have been hidden in the meantime
            // so check if element is visible again:
            // we can't draw on an invisible surface
            if ($graph.is(':hidden')) return;

            $graph.append($(this));
            on_drawn();
        };

        var $img = $('<img/>')
            .one('load', on_load_once) // ensure this is only called once
            .load(update_size)
            .error(on_error)
            .attr('src', get_url_with_size());

        var update_src = function () {
            $img.attr('src', get_url_with_size());
        };

        // list to parent div resizes, but dont trigger updating the image
        // until some time (> 1 sec) has passed.
        var timeout = null;
        $graph.resize(function () {
            if (timeout) {
                // clear old timeout first
                clearTimeout(timeout);
            }
            timeout = setTimeout(update_src, 1500);
        });
    }
}

/* Get activated overlay names (will be used to limit the back-end search to active overlays only */
function getActiveOverlayNames()
{
    var arr = [];
    $('.leaflet-control-layers-selector:checkbox:checked').each(function(){
	arr.push($(this).parent('div').children('span').text().trim());
    });
    return arr;
}

/* Based on various location properties, derive its status */
function calcLocationStatus(feat) {
    var status = 'unknown';
    if (feat.properties.complete === true) {
	status = 'complete';
    } else {
	if (feat.properties.planned_date !== null) {
	    var now = Date.now();    
	    var duedate = new Date(feat.properties.planned_date);
	    var overdue = duedate < now;
	    /* Scheduled, incomplete, overdue */
	    if (overdue) {
		/* Overdue */
		status = 'overdue';
	    } else {
		/* Scheduled, incomplete, not overdue*/
		status = 'sched_incomplete';
	    }
	} else {
	    if(feat.properties.complete === false) {
		status = 'incomplete';
	    }
	    if(feat.properties.new == true) {
		status = 'auto_new';
	    }
	}
    }
    if (feat.properties.work_impossible) {
	status = 'auto_skipped';
    }
    if(feat.properties.not_part_of_project == true) {
	status = 'notproject';
    }
    return status;
}

/* auxiliary function, check if array is empty */
function isEmpty(ob){
    for(var i in ob){
	return false;
    }
    return true;
}

/* main function */
function build_map(gj, extent, OoI) {
    var empty = false;
    if (isEmpty(gj) || isEmpty(extent)) {
	empty = true;
	extent = {'top': 53, 'bottom': 51.5, 'left':4.5, 'right':4.9};
    }

    /* create a leaflet map object */
    mymap = L.map('map_new', {
	fullscreenControl: {
            pseudoFullscreen: true
	},
	preferCanvas: true,
	zoomControl: false
    });
  
    currBounds = [
	[extent.top, extent.left],
	[extent.bottom, extent.right]
    ];
    var _orderingTable = {LineString: 0, Point: 10};

    mymap.fitBounds(currBounds);
    mymap.on('moveend', function() { 
	currBounds = mymap.getBounds();
    });

    /* add base map */
    var base = providerData[providers[currBase()]];
    var baseLayer = L.tileLayer(base.tile, {
	attribution: base.attr,
	maxZoom: MAXZOOM
    });
    var baseMaps = {
	"Street map": baseLayer
    };
    baseLayer.addTo(mymap);

    var scale = L.control.scale({imperial: false}).addTo(mymap);

    /* if deojsonDoc is empty, show the 'no data' message */
    if (empty) {
	var msg = L.control({position: 'bottomright'});
	msg.onAdd = function (mymap) {
	    var div = L.DomUtil.create('div', 'msg');
	    div.setAttribute("style", "background: rgba(255,255,255, .6);"
			     + "width: " + mymap.getSize().x + "px;"
			     + "margin: 0;"
			     + "font-size: 20pt;"
			     + "text-align: center;");
	    div.innerHTML += 'Geen gegevens beschikbaar';
	    return div;
	};
	msg.addTo(mymap);
	return;
    }

    /* keep object type and id of the recently clicked object (both global variables) */
    function setCurrObjId(type, id){
	currType = type;
	currObjId = id;
    }
    setCurrObjId('', '');

    function renderingOrderComparator(featA, featB){
	return _orderingTable[featA.geometry.loc_type] - _orderingTable[featB.geometry.loc_type];
    }

    var overlayMaps = {};

    /* leaflet overlay maps */
    var geojsonLayerOptions = {
	pointToLayer: function(feature, latlng){
	    if (feature.properties.type == 'location') {
		/* Displace locations slightly depending on their activity.
		   It's ok as long as the displacement is << object size.
		   2e-6 lat/lng deg is approx 22 cm. */ 
		if (globalDummyArr.indexOf(feature.properties.activity) < 0) {
		    globalDummyArr.push(feature.properties.activity);
		}
		idx = globalDummyArr.indexOf(feature.properties.activity);
		var c = L.circle([latlng['lat'] + idx*4e-6,
				  latlng['lng'] + idx*4e-6],
				 {radius: 2});
		return c;
	    } else {
		var c = L.circle([latlng['lat'], latlng['lng']],
				 {radius:3}).addTo(mymap);
		var r = L.rectangle(c.getBounds(), {stroke:true, weight: 2, lineJoin: 'round'});
		mymap.removeLayer(c);
		return r;
	    }		
	},
	style: function(feature) {
	    /* Determine color and shape of the feature marker based on its type, status etc. */
	    function featureColor(feat){
		var color = 'orange';
		var opacity = 1;
		var fillOpacity = opacity;
		var now = Date.now();    

		if (feat.properties.type == 'location') {
		    var status = calcLocationStatus(feat);
		    color = locStatuses[status].color;
		    opacity = locStatuses[status].opacity;
		    /* color/status is to be added to the legend */
		    if (dynamicLegend['locations'].indexOf(status) < 0) {dynamicLegend['locations'].push(status); }
		}
		if (feat.properties.type == 'request') {

		    color = reqStatuses[feat.properties.status].color;
		    opacity = reqStatuses[feat.properties.status].opacity;
		    fillOpacity = opacity;
		   
		    /* process moving requests separately since they come pairwise (old/new) */
		    if (feat.properties.req_type == 2) {
			if (feat.properties.old == 1) {
			    color = reqStatuses[feat.properties.status].altColor;
			    fillOpacity = 0;
			}
		    }
		    
		    legendColor = reqStatuses[feat.properties.status].color;
		    /* for requests, collect colors rather than statusses, since rejected, cancelled and invalid 
		       requests share color */
		    if (dynamicLegendColors['requests'].indexOf(legendColor) < 0) {dynamicLegendColors['requests'].push(legendColor); }
		}
		return [color, opacity, fillOpacity];
	    }
	    var dummy = featureColor(feature);
	    var color = dummy[0];
	    var opacity = dummy[1];
	    var fillOpacity = dummy[2];
	    if (feature.properties.type == 'location') {
		return {stroke:true,
			weight:2,
			lineJoin: 'round',
			color: color,
			fillColor: color,
			opacity: opacity,
			fillOpacity: fillOpacity};
	    } else {
		return {stroke:true,
			weight:3,
			lineJoin: 'round',
			color: color,
			fillColor: color,
			opacity: opacity,
			fillOpacity: fillOpacity};
	    }
	},
	onEachFeature: function(feature, layer){
	    /* Feature contain essential information only (location code, location type).
	       More about a location is available onclick. */
	    var popupHTML = locTypes[feature.properties.loc_type] + ' '
		+ feature.properties.code;
	    if (feature.properties.type == 'request') {
		popupHTML += '<br><b>Aanvraag: </b>' + reqTypes[feature.properties.req_type]
		    +' (' + reqStatuses[feature.properties.status].status + ')'
		    + '<br>Reden: ' + feature.properties.motivation
		    .replace(/[^A-Za-z0-9 _.,!"'/()$]/g, '<br>')
		    .replace('None', '')
		    .replace('<br><br>', '<br>');
	    }
	    layer.bindTooltip(popupHTML);
	    layer.on('mouseover', function(e){setCurrObjId(feature.properties.type, feature.properties.id);});
	    layer.on('mouseout', function(e){setCurrObjId('', '');});
	    layer.on('click', layer.closeTooltip);
	}
    };

    for (var activity in gj) {
	var geoJsonDocument = gj[activity];
	if (activity == 'Aanvragen') {
	    continue;
	} else if (activity == 'OoI') {
	    continue;
	} else {
	    // If we render using the Canvas, Points need to be rendered after LineStrings, or
	    // else they become very difficult to click.
	    geoJsonDocument.features.sort(renderingOrderComparator);
	    //var activityName = geoJsonDocument.features[0].properties.activity;
	    var layer = L.geoJSON(geoJsonDocument, geojsonLayerOptions);
	    layer.addTo(mymap); /* show everything by default */
	    overlayMaps[activity] = layer;
	}
    }

    /* get the changerequests ang add a overlay to the back */
    if ('Aanvragen' in gj) {
	var geoJsonDocument = gj['Aanvragen'];
	var activityName = 'Aanvragen';
	var layer = L.geoJSON(geoJsonDocument, geojsonLayerOptions);
	layer.addTo(mymap); /* show everything by default */
	overlayMaps[activityName] = layer;
	layer.bringToBack();
    }

    /* Add Overlay Control */
    control = new L.control.layers([], overlayMaps, {position: 'topleft'}).addTo(mymap);
    $(".leaflet-control-layers-overlays").prepend("<label><u>Kaartlagen</u></label>");
    
    /* Create and add Legend */
    var legend = L.control({position: 'bottomright'});
    legend.onAdd = function (mymap) {
	var div = L.DomUtil.create('div', 'info legend');
	div.style.background = 'rgba(255,255,255, .7)';
	
	div.innerHTML += '<span><strong><u>Objecten/Locaties</u></strong></span><br>';
	for (idx in dynamicLegend['locations']) {
	    var s = dynamicLegend['locations'][idx];
	    div.innerHTML +=
		'<span style="color:' + locStatuses[s].color + ';">&#9679;</span><strong>, </strong><span class="colored-line" style="background-color:'
		+ locStatuses[s].color +'"></span><strong> ' + locStatuses[s].status + '</strong><br>';
	}

	if (!isEmpty(dynamicLegendColors['requests'])) {
	    div.innerHTML += '<strong><u>Aanvragen</u></strong><br>';

	    for (var idx of [1,2,3]) {
		if (dynamicLegendColors['requests'].indexOf(reqStatuses[idx].color) > -1) {
		    div.innerHTML += '<strong>'
			+ '<span style="color:'	+ reqStatuses[idx].color + ';">&#9632;</span>'
			+ ','
			+ '<span style="color:'	+ reqStatuses[idx].color + ';">&#9633;</span>'
			+ ' ' + reqStatuses[idx].status + ' (nieuwe, oude locatie)</strong><br>';}
	    }
	}
	return div;
    };
    legend.addTo(mymap);

    /* process the response after a click and show the popup with it */
    function show_dialog(latlng, data){
	var html, i;

	html = '';

	/* Empty response: clicked too far from any location */
	if (!('html' in data)) {
	    popup = L.popup({'autoClose': true})
		.setLatLng(latlng) //TODO has to be loc coordinates
		.setContent('Niets gevonden rond deze locatie.')
		.openOn(mymap);
	    return;
	}

	/* response with data is an array with tabs (one tab per object)*/
	if (data.html && data.html.length !== 0) {
            if (data.html.length === 1) {
		html += data.html[0];
                reloadGraphs();
            } else {
		/* style is defined in leaflet-popup.css */
		html = '<div><div class="tab" id="popup-tabs">';
		/* indexOf() returns -1 if not found, in this case activate the first tab */
		var selectedIdx = Math.max(0, data.objIds.indexOf(currObjId));
		var active = '';
                for (var i=0; i<data.html.length; i+=1) {
		    active = (i == selectedIdx) ? ' active' : '';
                    html += '<button class="tablinks' + active + '" onclick="openTab(event, ' + i.toString()
			+ ',' + data.latlng[i] + ')">';
		    html += data.tab_titles[i]
			.replace('manhole', 'Put')
			.replace('pipe', 'Streng')
			.replace('drain', 'Kolk')
			.replace('point', 'Point');
                    html += '</button>';
                }
		html += '</div>';

		for (var i=0; i<data.html.length; i+=1) {
		    active = (i == selectedIdx) ? 'block' : 'none';
                    html += '<div class="tabcontent" id="popup-tab-' + i.toString() + '" style="display:' + active +';">';
                    html += data.html[i];
		    html += '</div></div>';
                }
            }
        } else {
            var nothingFoundMessage = '';
            if (lizard_map && lizard_map.nothingFoundMessage) {
                nothingFoundMessage = lizard_map.nothingFoundMessage;
            } else {
                // Backwards compatibility
                nothingFoundMessage = "Er is niets rond deze locatie gevonden.";
            }
            html = nothingFoundMessage;
        }

	/* find max tab height and use it as fixed popup height */
	popup = L.popup({'minWidth': 650,
			 'maxHeight': 500,
			 'autoClose': true,
			 'autoPan': true,
			 'opacity': 0.8})
	    .setLatLng(data.latlng[0])
	    .setContent(html)
	    .openOn(mymap);
	reloadGraphs();
    }

    /* click handler: get cursor coordinates and, if applicable, clicked object id and type,
     send a request to search around the clicked point */
    function onMapClick(e) {
	popup = L.popup().setLatLng(e.latlng);
	if (!currObjId) {
	    popup.setContent('Zoeken naar de dichtsbijzijnde locatie...')
		.openOn(mymap);
	} else {
	    popup.setContent('Ophalen Locatiegegevens...')
		.openOn(mymap);
	}	    
	$.ajax({
	    type: 'get',
	    url: 'get_closest_to',
	    data: {'lat': e.latlng.lat,
		   'lng': e.latlng.lng,
		   'objType': currType,
		   'objId': currObjId,
		   'overlays[]': getActiveOverlayNames()},
	    datatype: 'json',
	    success: function(resp){show_dialog(e.latlng, resp);reloadGraphs();},
	    error: function(jqXHR, textStatus, err){
		console.log("ERR: " + jqXHR + ' ' + err + ', ' + textStatus);}
	});
    }

    mymap.on('click', onMapClick);

    /* when called from a request page ('Bekijk op kaart'-link), show popup */
    if (OoI !== undefined) {
	$.ajax({
	    type: 'get',
	    url: 'get_closest_to',
	    data: {'lat': OoI.features[0].geometry.coordinates[1],
		   'lng': OoI.features[0].geometry.coordinates[0],
		   'objType': OoI.features[0].properties.type,
		   'objId': OoI.features[0].properties.id,
		   'overlays[]': getActiveOverlayNames()},
	    datatype: 'json',
	    success: function(resp){
		setCurrObjId(OoI.features[0].properties.type, OoI.features[0].properties.id);
		ll = new L.LatLng(OoI.features[0].geometry.coordinates[1],
				  OoI.features[0].geometry.coordinates[0])
		mymap.fitBounds(L.latLngBounds([ll]));
		show_dialog(ll, resp);
		reloadGraphs();},
	    error: function(jqXHR, textStatus, err){
		console.log("ERR: " + jqXHR + ' ' + err + ', ' + textStatus);}
	});
    }
}
