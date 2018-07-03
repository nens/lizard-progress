function getActiveOverlayNames()
{
    var arr = [];
    $('.leaflet-control-layers-selector:checkbox:checked').each(function(){
	arr.push($(this).parent('div').children('span').text().trim());
    });
    return arr;
}

function build_map(gj, extent) {
    function setCurrLocId(id){window.currLocationId = id;}
    setCurrLocId('');
    const ltypes = {'manhole':'Put','pipe':'Streng','drain':'Kolk'};
    const reqStatusColors = ["#000099", "#1b9387", "#da70d6"];
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
		radius: 5,
		weight: 1,
		opacity: .4,
		fillOpacity: .4});
	    } else {
		var fillOpacity = feature.properties.status; 
		return L.circleMarker(latlng, {
		    radius: 5+2,
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
	    layer.bindTooltip(popupHTML);
	    layer.on('mouseover', function(e){setCurrLocId(feature.properties.loc_id);});
	    layer.on('mouseout', function(e){setCurrLocId('');});
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
	    // If we render using the Canvas, Points need to be rendered after LineStrings, or
	    // else they become very difficult to click.
	    geoJsonDocument.features.sort(renderingOrderComparator);
	    var activityName = geoJsonDocument.features[0].properties.activity;
	    var layer = L.geoJSON(geoJsonDocument, geojsonLayerOptions);
	    layer.addTo(mymap); /* show everything by default */
	    overlayMaps[activityName] = layer;
	} else {
	    var activityName = 'Aanvragen';
	    var layer = L.geoJSON(geoJsonDocument, geojsonLayerOptions);
	    layer.addTo(mymap); /* show everything by default */
	    overlayMaps[activityName] = layer;
	    layer.bringToFront();
	}
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

    control = new L.control.layers([], overlayMaps).addTo(mymap);
    
    function show_dialog(latlng, loc_info){
	//setup_movable_dialog();
	if (!('type' in loc_info)) {
	    var popup = L.popup({'maxWidth': 500, 'autoClose': true})
		.setLatLng(latlng) //TODO has to be loc coordinates
		.setContent('Niets gevonden rond deze locatie.')
		.openOn(mymap);
	    return;
	}
	
	var popupHTML = '<h3><b>' + ltypes[loc_info.loc_type] + ' '
	    + loc_info.code + '</b></h3> '
	    + 'Opdrachtnemer: ' + loc_info.activities[0].contractor /* TODO: probably a tab per activity */
	    + '<br>Werkzaamheid: ' + loc_info.activities.map(function(a){return a['name'];}).join(',<br>');
	if ('files' in loc_info) {
	    popupHTML += '<br><br>Bestanden:<br>';
	    popupHTML += '<table><tr><th><b>Bestand</b></th><th><b>Upload</b></th></tr>';
	    loc_info['files'].forEach(function(el){
		var d = new Date(el.when);
		popupHTML += '<tr><td>' + el.name + '</td><td>'
		    + d.getDate() + '-' + d.getMonth()+1 + '-' + d.getFullYear() + '</td></tr>';
	    });
	    popupHTML += '</table>';
	} else {
	    popupHTML += '<br><br>Er is voor deze locatie nog geen data aanwezig in het systeem.';
	}
	
	if (loc_info.requests.length > 0) {
	    for (var cr in loc_info.requests) {
		var req = loc_info.requests[cr];
		popupHTML += '<h3>Aanvraag (' + req['status'] + ')</h3><br>';
		popupHTML += '<a href=' + req['url']
		    + '>Klik hier voor meer details (aanvraagpagina)</a><br>'
		    + '<dl class="dl-horizontal">'
		    + '<dt>Type<dt><dd>' + req['req_type'] + '</dd>'
		    + '<dt>Locatie<dt><dd>' + loc_info['code'] + '</dd>'
		    + '<dt>Werkzaamheid<dt><dd>' + req['activity'] + '</dd>'
		    + '<dt>Motivatie</dt><dd>' + req['motivation'] + '</dd></dl>'
		    + '<dt>Goedkeuring</dt><dd>'
		    + '<dd><form action="' + req['url'] + '/acceptance" method="post">'
		    + '<input name="csrfmiddlewaretoken" value="QXoOefkj5e25nCahMiTWp4l05HnXrfOe" type="hidden">' 
		    + '<input name="wantoutputas" value="json" type="hidden">'
		    + '<input name="accept" id="hidden-accept" value="" type="hidden">'
		    + '<input name="refuse" id="hidden-refuse" value="" type="hidden">'
		    + '<button onclick="ajax_submit(this);" type="button" data-hidden-id="#hidden-accept" class="btn btn-success ajaxsubmit">Goedkeuren</button>'
		    + '<br><button onclick="ajax_submit(this);" type="button" data-hidden-id="#hidden-refuse" class="btn btn-danger ajaxsubmit">Afkeuren</button>'
		    + 'Reden: <input name="reason" value="" type="text">'
		    + '<br><span style="color: red" id="submit-errors"></span>';
	    }
	}
	
	var popup = L.popup({'maxWidth': 500, 'autoClose': true})
	    .setLatLng(latlng) //TODO has to be loc coordinates
	    .setContent(popupHTML)
	    .openOn(mymap);
    }
    function onMapClick(e) {
	console.log(getActiveOverlayNames());
	var popup = L.popup().setLatLng(e.latlng);
	if (!window.currLocationId) {
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
		   'locId': window.currLocationId,
		   'overlays[]': getActiveOverlayNames()},
	    datatype: 'json',
	    success: function(resp){show_dialog(e.latlng, resp);},
	    error: function(jqXHR, textStatus, err){
		console.log("ERR: " + jqXHR + ' ' + err + ', ' + textStatus);}
	});
    }

    mymap.on('click', onMapClick);  
}
