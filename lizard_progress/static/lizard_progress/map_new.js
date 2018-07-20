var locStatusColors = {'green': 'Compleet',
		       'red': 'Niet (geheel) aanwezig en niet gepland',
		       'black': 'Gepland, nog niet compleet',
		       'gray': 'Geen onderdeel van werkzaamheden',
		       'brown': 'Nieuw object (automatisch toegevoegd)'
		      };
var reqstatuses = {'1': 'Open',
		     '2': 'Geaccepteerd',
		     '3': 'Geweigerd',
		     '4': 'Ingetrokken',
		     '5': 'Ongeldig'};

var reqStatusColors = ["#blue", "green", "magenta", "magenta", "magenta"];
var ltypes = {'manhole':'Put','pipe':'Streng','drain':'Kolk', 'point': ''};

var reqtypes = {'1': 'Locatiecode verwijderen',
		'2': 'Locatie verplaatsen',
		'3': 'Niewe locatiecode'};

var providers = {
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
    'openinfrawater': {
	tile: 'https://geodata.nationaalgeoregister.nl/tiles/service/wmts/brtachtergrondkaart/EPSG:3857/{z}/{x}/{y}.png',
	attr: '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>, <a href="http://www.openinframap.org/about.html">About OpenInfraMap</a>'
    }
};

/* we want to access the popup from several scopes, 
   temporary ;-) solution is to make it global */
var popup;

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
    window.popup.setLatLng([lat, lng]);
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
function getActiveOverlayNames()
{
    var arr = [];
    $('.leaflet-control-layers-selector:checkbox:checked').each(function(){
	arr.push($(this).parent('div').children('span').text().trim());
    });
    return arr;
}

function featureColor(feat){

    var color = 'black';
    
    if (feat.properties.type == 'location') {
	if (feat.properties.complete) {
	    color = "green";
	} else {
	    if(feat.properties.complete === false) {
		color = "red";
	    } else if(feat.properties.not_part_of_project == true) {
		color = "gray";
	    } else if(feat.properties.new == true) {
		color = "#ababf8";
	    } else {
		color = "orange";
	    }
	}
    }
    if (feat.properties.type == 'request') {
	color = reqStatusColors[feat.properties.status - 1];
    }
    return color;
}
function isEmpty(ob){
   for(var i in ob){ return false;}
  return true;
}

function build_map(gj, extent, OoI) {
    var empty = false;
    if (isEmpty(gj) || isEmpty(extent)) {
	empty = true;
	extent = {'top': 53, 'bottom': 51.5, 'left':4.5, 'right':4.9};
    }

    function renderingOrderComparator(featA, featB){
	return _orderingTable[featA.geometry.loc_type] - _orderingTable[featB.geometry.loc_type];
    }

    var overlayMaps = {};

    function setCurrObjId(type, id){window.currType=type;window.currObjId=id;}
    setCurrObjId('', '');
    
    var mymap = L.map('map_new', {
	fullscreenControl: {
            pseudoFullscreen: true
	},
	preferCanvas: true,
	zoomControl: false
    });
  
    var bounds = [
	[extent.top, extent.left],
	[extent.bottom, extent.right]
    ];
    var _orderingTable = {LineString: 0, Point: 10};

    mymap.fitBounds(bounds);

    var base = providers['osm'];
    var baseLayer = L.tileLayer(base.tile, {
	attribution: base.attr,
	maxZoom: 19
    });
    var baseMaps = {
	"Street map": baseLayer
    };
    baseLayer.addTo(mymap);
    var scale = L.control.scale({imperial: false}).addTo(mymap);

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

    var geojsonLayerOptions = {
	pointToLayer: function(feature, latlng){
	    if (feature.properties.type == 'location') {
		var c = L.circle([latlng['lat'], latlng['lng']], 3);
		return c;
	    } else {
		/* Displace change requests slightly since they might be covered by other markers.
		   It's ok as long as the displacement is << object size.
		   5e-7 lat/lng deg is approx 5.6 cm. */ 
		var c = L.circleMarker([latlng['lat']+.0000005, latlng.lng+.0000005], {
		    radius: 2.5,
		    weight: 3,
		    opacity: .8,
		    fillOpacity: .8});
		var c = L.circle([latlng['lat'], latlng['lng']], 3).addTo(mymap);
		var r = L.rectangle(c.getBounds());
		mymap.removeLayer(c);
		return r;
	    }		
	},
	style: function(feature) {
	    var color = featureColor(feature);
	    return {color: color, fillColor: color, fillOpacity: feature.properties.type == 'location' ? 0.8 : 0.05};
	},
	onEachFeature: function(feature, layer){
	    /* Feature contain essential information only (location code, location type).
	       More about a location is available onclick. */
	    var popupHTML = ltypes[feature.properties.loc_type] + ' '
		+ feature.properties.code;
	    if (feature.properties.type == 'request') {
		popupHTML += '<br>Aanvraag: ' + reqtypes[feature.properties.req_type]
		    + '<br>' + feature.properties.motivation;
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
	layer.bringToFront();
    }
    
    L.Control.Layers.include({
	getActiveOverlays: function () {
	    // Create array for holding active layers
            var active = [];
	    // Iterate all layers in control
            this._layers.forEach(function (obj) {
		// Check if it's an overlay and added to the map
		if (obj.overlay && mymap.hasLayer(obj.layer)) {
		    // Push layer to active array
                    active.push(obj.layer);
		}
            });
	    // Return array
            return active;
	}
    });

    control = new L.control.layers([], overlayMaps, {position: 'topleft'}).addTo(mymap);
    $(".leaflet-control-layers-overlays").prepend("<label><u>Kaartlagen</u></label>");
    
    var legend = L.control({position: 'bottomright'});

    legend.onAdd = function (mymap) {
	var div = L.DomUtil.create('div', 'info legend');
	div.style.background = 'rgba(255,255,255, .6)';
	
	div.innerHTML += '<strong><u>Objecten/Locaties</u></strong><br>';
	for (k in locStatusColors) {
	    div.innerHTML +=
		    '<span style="color:' + k + ';">&#9679;</span><strong> ' + locStatusColors[k] + '</strong><br>';
	}
	div.innerHTML += '<strong><u>Aanvragen</u></strong><br>';
	div.innerHTML += '<span style="color:' + reqStatusColors[0] +';">&#9632;</span><strong> Open</strong><br>';
	div.innerHTML += '<span style="color:' + reqStatusColors[1] +';">&#9632;</span><strong> Geaccepteerd</strong><br>';
	div.innerHTML += '<span style="color:' + reqStatusColors[2] +';">&#9632;</span><strong> Geweigerd / ingetrokken / ongeldig</strong><br>';
	
	return div;
    };
    legend.addTo(mymap);
    
    function show_dialog(latlng, data){
	var html, i;

	html = '';

	if (!('html' in data)) {
	    window.popup = L.popup({'autoClose': true})
		.setLatLng(latlng) //TODO has to be loc coordinates
		.setContent('Niets gevonden rond deze locatie.')
		.openOn(mymap);
	    return;
	}
	
	if (data.html && data.html.length !== 0) {
            if (data.html.length === 1) {
		html += data.html[0];
                reloadGraphs();
            } else {
		html = `<style>
 /* Style the tab */
.tab {
    overflow: hidden;
    border: 1px solid #ccc;
    background-color: 'white';//#f1f1f1;
}

/* Style the buttons that are used to open the tab content */
.tab button {
    background-color: #f1f1f1;
    float: left;
    border: 1px solid #ccc;
    outline: none;
    cursor: pointer;
    padding: 5px 10px;
    transition: 0.3s;
}

/* Change background color of buttons on hover */
.tab button:hover {
    background-color: #ddd;
}

/* Create an active/current tablink class */
.tab button.active {
    background-color: #ccc;
}

/* Style the tab content */
.tabcontent {
//    display: none;
    padding: 6px 10px;
    border: 1px solid #ccc;
    border-top: none;
height:100%;
} 
 </style>`;
		html += '<div><div class="tab" id="popup-tabs">';
		/* indexOf() returns -1 if not found, in this case activate the first tab */
		var selectedIdx = Math.max(0, data.objIds.indexOf(window.currObjId));
		var active = '';
                for (var i=0; i<data.html.length; i+=1) {
		    active = (i == selectedIdx) ? ' active' : '';
                    html += '<button class="tablinks' + active + '" onclick="openTab(event, ' + i.toString()
			+ ',' + data.latlng[i] + ')">';
                    html += data.tab_titles[i]
			.replace('manhole', 'Put')
			.replace('pipe', 'Streng')
			.replace('drain', 'Kolk');
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
	console.log(data.latlng[0]);
	window.popup = L.popup({'minWidth': 650, 'maxHeight': 500, 'autoClose': true, 'autoPan': true})
	    .setLatLng(data.latlng[0])
	    .setContent(html)
	    .openOn(mymap); 
    }    
    function onMapClick(e) {
	window.popup = L.popup().setLatLng(e.latlng);
	if (!window.currObjId) {
	    window.popup.setContent('Zoeken naar de dichtsbijzijnde locatie...')
		.openOn(mymap);
	} else {
	    window.popup.setContent('Ophalen Locatiegegevens...')
		.openOn(mymap);
	}	    
	$.ajax({
	    type: 'get',
	    url: 'get_closest_to',
	    data: {'lat': e.latlng.lat,
		   'lng': e.latlng.lng,
		   'objType': window.currType,
		   'objId': window.currObjId,
		   'overlays[]': getActiveOverlayNames()},
	    datatype: 'json',
	    success: function(resp){show_dialog(e.latlng, resp);reloadGraphs();},
	    error: function(jqXHR, textStatus, err){
		console.log("ERR: " + jqXHR + ' ' + err + ', ' + textStatus);}
	});
    }

    mymap.on('click', onMapClick);

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
		mymap.panTo(ll);
		console.log(ll)
		//mymap.setZoom(18);
		//show_dialog(ll, resp);
		reloadGraphs();},
	    error: function(jqXHR, textStatus, err){
		console.log("ERR: " + jqXHR + ' ' + err + ', ' + textStatus);}
	});
    }
}
