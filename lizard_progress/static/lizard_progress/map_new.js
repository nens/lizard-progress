function build_map(gj, extent) {
    const baseLayer = L.tileLayer('http://{s}.tile.osm.org/{z}/{x}/{y}.png', {
	attribution: '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors',
	maxZoom: 22
    });

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
    mymap.fitBounds(bounds);
    baseLayer.addTo(mymap);

    function styler(feature) {
	if (feature.properties.complete === true) {
            return {color: "green", fillColor: 'green'};
	} else if(feature.properties.complete === false) {
            return {color: "red", fillColor: 'red' };
	} else {
            return {color: "orange", fillColor: 'orange'};
	}
    };

    var scale = L.control.scale().addTo(mymap);
    const ltypes = {'manhole':'Put','pipe':'Streng','drain':'Kolk'};
    var geojsonCircleOptions = {
	radius: 5,
	weight: 1,
	opacity: 1,
	fillOpacity: 0.5
    };

    function pointToLayer (feature, latlng) {
	return L.circleMarker(latlng, geojsonCircleOptions);
    }
    const geojsonLayerOptions = {
	pointToLayer: pointToLayer,
	style: styler,
	onEachFeature: function (feature, layer) {

	    var popupHTML = '<h3><b>' + ltypes[feature.properties.type] + ' '
		+ feature.properties.code + '</b></h3>' 
		+ 'Opdrachtnemer: ' + feature.properties.contractor 
		+ '<br>Werkzaamheid: ' + feature.properties.activity;
	    layer.bindPopup(
		popupHTML
	    );
	}
    }

    const _orderingTable = {LineString: 0, Point: 10};

    function renderingOrderComparator(featA, featB) {
	return _orderingTable[featA.geometry.type] - _orderingTable[featB.geometry.type];
    }
    var geoJsonDocument = gj;
    // If we render using the Canvas, Points need to be rendered after LineStrings, or
    // else they become very difficult to click.
    geoJsonDocument.features.sort(renderingOrderComparator);
    var locationLayer = L.geoJSON(geoJsonDocument, geojsonLayerOptions);
    locationLayer.addTo(mymap);

    const baseMaps = {
	"Street map": baseLayer
    };
    const overlayMaps = {
	"Locations": locationLayer
    };
    L.control.layers(baseMaps, overlayMaps).addTo(mymap);
}
