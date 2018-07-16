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
    var flot_graph_data_url = $graph.attr('data-flot-graph-data-url');
    var image_graph_url = $graph.attr('data-image-graph-url');
    var graph_type;
    graph_type = (flot_graph_data_url) ? 'flot' : 'image';
    var url = (graph_type == 'flot') ? flot_graph_data_url : image_graph_url;

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

        // show a message when loading has failed
        var on_error = function () {
            on_loaded();
            $graph.html('Fout bij het laden van de gegevens. Te veel data. Pas uw tijdsperiode aan of exporteer de tijdreeks.');
        };

        // for flot graphs, grab the JSON data and call Flot
        if (graph_type == 'flot') {
            $.ajax({
                url: url,
                method: 'GET',
                dataType: 'json',
                success: function (response) {
                    on_loaded();

                    // tab might have been hidden in the meantime
                    // so check if element is visible again:
                    // we can't draw on an invisible surface
                    if ($graph.is(':hidden')) return;

                    var plot = flotGraphLoadData($graph, response);
                    on_drawn();
                    //bindPanZoomEvents($graph);
                },
                timeout: 20000,
                error: on_error
            });
        }
        // for static image graphs, just load the image as <img> element
        else if (graph_type == 'image') {
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
}
function getActiveOverlayNames()
{
    var arr = [];
    $('.leaflet-control-layers-selector:checkbox:checked').each(function(){
	arr.push($(this).parent('div').children('span').text().trim());
    });
    return arr;
}

function build_map(gj, extent) {
    function setCurrObjId(type, id){window.currType=type;window.currObjId=id;}
    setCurrObjId('', '');
    const ltypes = {'manhole':'Put','pipe':'Streng','drain':'Kolk', 'point': ''};
    const reqtypes = {'1': 'Locatiecode verwijderen',
		      '2': 'Locatie verplaatsen',
		      '3': 'Niewe locatiecode'};
    const reqstatuses = {'1': 'Open',
			 '2': 'Geaccepteerd',
			 '3': 'Geweigerd',
			 '4': 'Ingetrokken',
			 '5': 'Ongeldig'};
    const reqStatusColors = ["#000099", "#1b9387", "#da70d6", "#da70d6", "gray"];
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

    const geojsonLayerOptions = {
	pointToLayer: function(feature, latlng){
	    if (feature.properties.type == 'location') {
		return L.circleMarker(latlng, {
		    radius: 6,
		    weight: 1,
		    opacity: .4,
		    fillOpacity: .4});
	    } else {
		var fillOpacity = feature.properties.status; 
		return L.circleMarker(latlng, {
		    radius: 5+3,
		    weight: 3,
		    opacity: .4,
		    fillOpacity: .4});
	    }		
	},
	style: function(feature) {
	    var color = "black";
	    if (feature.properties.type == 'location') {
		if (feature.properties.complete) {
		    color = "green";
		} else if(feature.properties.complete === false) {
		    color = "red";
		} else {
		    color = "orange";
		}
	    } else if (feature.properties.type == 'request') {
		color = reqStatusColors[feature.properties.status - 1];
	    }
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

    function renderingOrderComparator(featA, featB){
	return _orderingTable[featA.geometry.loc_type] - _orderingTable[featB.geometry.loc_type];
    }

    var overlayMaps = {};
    for (var activity in gj) {
	var geoJsonDocument = gj[activity];
	if ('Aanvragen' != activity) {
	    console.log(activity);
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

    control = new L.control.layers([], overlayMaps).addTo(mymap);
    
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
