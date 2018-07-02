function build_map(gj, extent) {
    const ltypes = {'manhole':'Put','pipe':'Streng','drain':'Kolk'};
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

    var scale = L.control.scale().addTo(mymap);

    const geojsonLayerOptions = {
	pointToLayer: function(feature, latlng){
	    return L.circleMarker(latlng, {
		radius: 5,
		weight: 1,
		opacity: 1,
		fillOpacity: 0.5
	    });
	},
	style: function(feature) {
	    if (feature.properties.complete === true) {
		return {color: "green", fillColor: 'green'};
	    } else if(feature.properties.complete === false) {
		return {color: "red", fillColor: 'red' };
	    } else {
		return {color: "orange", fillColor: 'orange'};
	    }
	}
    };
    function renderingOrderComparator(featA, featB){
	return _orderingTable[featA.geometry.type] - _orderingTable[featB.geometry.type];
    }

    var overlayMaps = {};
    for (var activity in gj) {
	var geoJsonDocument = gj[activity];
	// If we render using the Canvas, Points need to be rendered after LineStrings, or
	// else they become very difficult to click.
	geoJsonDocument.features.sort(renderingOrderComparator);
	var activityName = geoJsonDocument.features[0].properties.activity;
	var layer = L.geoJSON(geoJsonDocument, geojsonLayerOptions);
	layer.addTo(mymap); /* show everything by default */
	overlayMaps[activityName] = layer;
    }

    L.control.layers([], overlayMaps).addTo(mymap);

    function show_dialog(latlng, loc_info){
	var popupHTML = '<h3><b>' + ltypes[loc_info.type] + ' '
	    + loc_info.code + '</b></h3>' 
	    + 'Opdrachtnemer: ' + loc_info.contractor 
	    + '<br>Werkzaamheid: ' + loc_info.activity;
	if ('files' in loc_info) {
	    popupHTML += '<br><br>Bestanden:<br>';
	    popupHTML += '<table><tr><th><b>Bestand</b></th><th><b>Upload</b></th></tr>';
	    loc_info['files'].forEach(function(el){
		var d = new Date(el.when);
		popupHTML += '<tr><td>' + el.name + '</td><td>'
		    + d.getDate() + '-' + d.getMonth() + '-' + d.getFullYear() + '</td></tr>';
	    });
	    popupHTML += '</table>';
	} else {
	    popupHTML += '<br><br>Er is voor deze locatie nog geen data aanwezig in het systeem.';
	}
	var popup = L.popup({'maxWidth': 500, 'autoClose': false})
	    .setLatLng(latlng) //TODO has to be loc coordinates
	    .setContent(popupHTML)
	    .openOn(mymap);
    }
    function onMapClick(e) {
	var popup = L.popup()
	    .setLatLng(e.latlng) //TODO has to be loc coordinates
	    .setContent('Zoeken naar de dichtsbijzijnde locatie...')
	    .openOn(mymap);
	$.ajax({
	    type: 'get',
	    url: 'get_closest_to',
	    data: {'lat': e.latlng.lat, 'lng': e.latlng.lng},
	    datatype: 'json',
	    success: function(resp){show_dialog(e.latlng, resp);},
	    error: function(jqXHR, textStatus, err){
		console.log("ERR: " + jqXHR + ' ' + err + ', ' + textStatus);}
	});
    }
    mymap.on('click', onMapClick);  
}
