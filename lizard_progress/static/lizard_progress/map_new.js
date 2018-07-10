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
    const reqtypes = {'1': 'Locatiecode verwijderen',
		      '2': 'Locatie verplaatsen',
		      '3': 'Niewe locatiecode'};
    const reqstatuses = {'1': 'Open',
			 '2': 'Geaccepteerd',
			 '3': 'Geweigerd',
			 '4': 'Ingetrokken',
			 '5': 'Ongeldig'};
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
	//setup_movable_dialog();
	if (!('html' in loc_info)) {
	    var popup = L.popup({'maxWidth': 500, 'autoClose': true})
		.setLatLng(latlng) //TODO has to be loc coordinates
		.setContent('Niets gevonden rond deze locatie.')
		.openOn(mymap);
	    return;
	}
	
	var popupHTML = loc_info.html;

	latlng = L.latLng(loc_info.lat, loc_info.lng);
	var popup = L.popup({'maxWidth': 500, 'autoClose': true})
	    .setLatLng(latlng)
	    .setContent(popupHTML)
	    .openOn(mymap);
    }
    function onMapClick(e) {
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
