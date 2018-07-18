const locStatusColors = {'green': 'Compleet',
		       'red': 'Niet (geheel) aanwezig en niet gepland',
		       'black': 'Gepland, nog niet compleet',
		       'gray': 'Geen onderdeel van werkzaamheden',
		       '#ababf8': 'Nieuw object (automatisch toegevoegd)',
		      }
const reqstatuses = {'1': 'Open',
		     '2': 'Geaccepteerd',
		     '3': 'Geweigerd',
		     '4': 'Ingetrokken',
		     '5': 'Ongeldig'};

const reqStatusColors = ["#33aaff", "#119cca", "#c301fe", "#c301fe", "#c301fe"];
const ltypes = {'manhole':'Put','pipe':'Streng','drain':'Kolk', 'point': ''};

const reqtypes = {'1': 'Locatiecode verwijderen',
		  '2': 'Locatie verplaatsen',
		  '3': 'Niewe locatiecode'};

function reloadGraphs(max_image_width, callback, force=true) {
    // New Flot graphs
    $('.dynamic-graph').each(function () {
        reloadDynamicGraph($(this), callback, force);
    });
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

function build_map(gj, extent) {
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
    
    const mymap = L.map('map_new', {
	fullscreenControl: {
            pseudoFullscreen: true
	},
	preferCanvas: true
    });
    const bounds = [
	[extent.top, extent.left],
	[extent.bottom, extent.right]
    ];
    const _orderingTable = {LineString: 0, Point: 10};

    mymap.fitBounds(bounds);

    const baseLayer = L.tileLayer('http://{s}.tile.osm.org/{z}/{x}/{y}.png', {
	attribution: '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors',
	maxZoom: 22
    });
    const baseMaps = {
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

    const geojsonLayerOptions = {
	pointToLayer: function(feature, latlng){
	    if (feature.properties.type == 'location') {
		return L.circleMarker(latlng, {
		    radius: 4,
		    weight: 1,
		    opacity: .8,
		    fillOpacity: .8});
	    } else {
		/* Displace change requests slightly since they might be covered by other markers.
		   It's ok as long as the displacement is << object size.
		   5e-7 lat/lng deg is approx 5.6 cm. */ 
		return L.circleMarker([latlng['lat']+.0000005, latlng.lng+.0000005], {
		    radius: 4,
		    weight: 3,
		    opacity: .8,
		    fillOpacity: .8});
	    }		
	},
	style: function(feature) {
	    var color = featureColor(feature);
	    return {color: color, fillColor: color};
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
	if ('Aanvragen' != activity) {
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
    var geoJsonDocument = gj['Aanvragen'];
    var activityName = 'Aanvragen';
    var layer = L.geoJSON(geoJsonDocument, geojsonLayerOptions);
    layer.addTo(mymap); /* show everything by default */
    overlayMaps[activityName] = layer;
    layer.bringToBack();

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

    var ribx = true;
    if (ribx) {
	var legend = L.control({position: 'bottomright'});

	legend.onAdd = function (mymap) {
	    var div = L.DomUtil.create('div', 'info legend');
	    div.style.background = 'rgba(255,255,255, .6)';
	    
	    div.innerHTML += '<strong><u>Objecten/Locaties</u></strong><br>';
	    for (k in locStatusColors) {
		div.innerHTML +=
		    '<font color="' + k + '">&#11044;</font><strong> ' + locStatusColors[k] + '</strong><br>';
	    }
	    div.innerHTML += '<strong><u>Aanvragen</u></strong><br>';
	    div.innerHTML += '<font color="#33aaff">&#11044;</font><strong> Open</strong><br>';
	    div.innerHTML += '<font color="#119cca">&#11044;</font><strong> Geaccepteerd</strong><br>';
	    div.innerHTML += '<font color="#c301fe">&#11044;</font><strong> Geweigerd / ingetrokken / ongeldig</strong><br>';
	    
	    return div;
	};
	legend.addTo(mymap);
    }
    
    function show_dialog(latlng, loc_info){
	var html, i;

	html = ''; // '<div id="movable-dialog"><div id="movable-dialog-content">';

	var options = {
            autoOpen: false,
            title: '',
            width: 650,
            height: 480,
            zIndex: 10000,
            close: function (event, ui) {
		// clear contents on close
		$('#movable-dialog-content').empty();
            }
	};

	// $('#movable-dialog').dialog(options);


	//setup_movable_dialog();
	if (!('html' in loc_info)) {
	    var popup = L.popup({'autoClose': true})
		.setLatLng(latlng) //TODO has to be loc coordinates
		.setContent('Niets gevonden rond deze locatie.')
		.openOn(mymap);
	    return;
	}
	
	latlng = L.latLng(loc_info.lat, loc_info.lng);

	var data = loc_info;
	/* Copypaste from lizard_map/lizard_map.js */
	if (data.html && data.html.length !== 0) {
            // We got at least 1 result back.
            if (data.html.length === 1) {
                // Just copy the contents directly into the target div.
                $("#movable-dialog-content").html(data.html[0]);
		html += data.html[0];
		// Have the graphs fetch their data.
                reloadGraphs();
            } else {
                // Build up html with tabs.
                html += '<div id="popup-tabs"><ul>';
                for (i = 0; i < data.html.length; i += 1) {
                    html += '<li><a href="#popup-tab-' + (i + 1) + '">';
                    html += data.tab_titles[i].replace('manhole', 'Put').replace('pipe', 'Streng').replace('drain', 'Kolk');
                    html += '</a></li>';
                }
                html += '</ul>';
                for (i = 0; i < data.html.length; i += 1) {
                    html += '<div id="popup-tab-' + (i + 1) + '">';
                    html += data.html[i];
                    html += '</div>';
                }
                html += '</div>';

                // Copy the prepared HTML to the target div.
                $("#movable-dialog-content").html(html);

                // Call jQuery UI Tabs to actually instantiate some tabs.
                $("#popup-tabs").tabs({
                    idPrefix: 'popup-tab',
                    selected: 0,
                    show: function (event, ui) {
                        // Have the graphs fetch their data.
                        reloadGraphs();
                    },
                    create: function (event, ui) {
                        // Have the graphs fetch their data.
                        reloadGraphs();
                    }
                });
            }
            $("#popup-subtabs").tabs({
                idPrefix: 'popup-subtab',
                selected: 0
            });
            //$(".add-snippet").snippetInteraction();
        }
        else {
            var nothingFoundMessage = '';
            if (lizard_map && lizard_map.nothingFoundMessage) {
                nothingFoundMessage = lizard_map.nothingFoundMessage;
            }
            else {
                // Backwards compatibility
                nothingFoundMessage = "Er is niets rond deze locatie gevonden.";
            }
            $("#movable-dialog-content").html(nothingFoundMessage);
        }
	/* END Copypaste */

	var popup = L.popup({'minWidth': 650, 'maxHeight': 480, 'autoClose': true, 'autoPan': true})
	    .setLatLng(latlng)
	    .setContent(html /*+ '</div></div>'*/)
	    .openOn(mymap); 
	//mymap.setView(latlng);
	$('#movable-dialog').dialog();
	$("#popup-tabs").tabs({
            idPrefix: 'popup-tab',
            selected: 0,
            show: function (event, ui) {
                // Have the graphs fetch their data.
                reloadGraphs();
            },
            create: function (event, ui) {
                // Have the graphs fetch their data.
                reloadGraphs();
            }
        });
    }
    
    function onMapClick(e) {
	var popup = L.popup().setLatLng(e.latlng);
	if (!window.currObjId) {
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
}
