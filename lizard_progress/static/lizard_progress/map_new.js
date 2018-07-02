function setup_movable_dialog() {
    // used by open_popup
    $('body').append('<div id="movable-dialog"><div id="movable-dialog-content"></div></div>');
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

    // make an exception for iPad
    if (isAppleMobile) {
        // dragging on touchscreens isn't practical
        options.draggable = false;
        // resizing neither
        options.resizable = false;
        // make width 90% of the entire window
        options.width = $(window).width() * 0.9;
        // make height 80% of the entire window
        options.height = $(window).height() * 0.8;
    }

    $('#movable-dialog').dialog(options);
}
function build_map(gj, extent) {
    function setCurrLocId(id){window.currLocationId = id;}
    setCurrLocId('');
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
	    } else if(true) {
		return {color: "black", fillColor: 'black'};
	    } else {
		return {color: "orange", fillColor: 'orange'};
	    }
	},
	onEachFeature: function(feature, layer){
	    /* showing essentioal information: location code, location type */
	    var popupHTML = ltypes[feature.properties.loc_type] + ' '
		+ feature.properties.code;
	    // setCurrLocId(feature.properties.loc_id);
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
	}
    }

    L.control.layers([], overlayMaps).addTo(mymap);

    function show_dialog(latlng, loc_info){
	//setup_movable_dialog();
	
	var popupHTML = '<h3><b>' + ltypes[loc_info.loc_type] + ' '
	    + loc_info.code + '</b></h3>' 
	    + 'Opdrachtnemer: ' + loc_info.contractor 
	    + '<br>Werkzaamheid: ' + loc_info.activity;
	if ('files' in loc_info) {
	    popupHTML += '<br><br>Bestanden:<br>';
	    popupHTML += '<table><tr><th><b>Bestand</b></th><th><b>Upload</b></th></tr>';
	    loc_info['files'].forEach(function(el){
		var d = new Date(el.when);
		popupHTML += '<tr><td>' + el.name + '</td><td>'
		    + d.getDate() + '-' + d.getMonth()+1 + '-' + d.getFullYear() + '</td></tr>';
	    });
	    popupHTML += '</table>';
	    if (loc_info.requests.length > 0) {
		for (var cr in loc_info.requests) {
		    var req = loc_info.requests[cr];
		    popupHTML += '<h3>Aanvraag (' + req['status'] + ')</h3><br>';
		    popupHTML += '<a href=' + req['url']
			+ '>Klik hier voor meer details (aanvraagpagina)</a><br>'
			+ '<dl class="dl-horizontal">'
			+ '<dt>Type<dt><dd>' + req['req_type'] + '</dd>'
			+ '<dt>Locatie<dt><dd>' + loc_info['code'] + '</dd>'
			+ '<dt>Werkzaamheid<dt><dd>' + loc_info['activity'] + '</dd>'
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
	} else {
	    popupHTML += '<br><br>Er is voor deze locatie nog geen data aanwezig in het systeem.';
	}
	var popup = L.popup({'maxWidth': 500, 'autoClose': true})
	    .setLatLng(latlng) //TODO has to be loc coordinates
	    .setContent(popupHTML)
	    .openOn(mymap);
    }
    function onMapClick(e) {
	var popup = L.popup().setLatLng(e.latlng);
	if (!window.currLocationId) {
	    popup.setContent('Zoeken naar de dichtsbijzijnde locatie...')
		.openOn(mymap);
	} else {
	    //popup.setContent('Ophalen Locatiegegevens...')
		//.openOn(mymap);
	}	    
	$.ajax({
	    type: 'get',
	    url: 'get_closest_to',
	    data: {'lat': e.latlng.lat, 'lng': e.latlng.lng, 'locId': window.currLocationId},
	    datatype: 'json',
	    success: function(resp){show_dialog(e.latlng, resp);},
	    error: function(jqXHR, textStatus, err){
		console.log("ERR: " + jqXHR + ' ' + err + ', ' + textStatus);}
	});
    }

    mymap.on('click', onMapClick);  
}
