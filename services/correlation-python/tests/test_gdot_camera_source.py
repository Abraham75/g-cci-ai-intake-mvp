from gcci.gdot_camera_source import parse_gdot_camera_geojson


def test_parse_gdot_camera_geojson_normalizes_valid_point_feature():
    body = {
        "type": "FeatureCollection",
        "features": [
            {
                "id": 42,
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [-84.37, 33.91]},
                "properties": {
                    "OBJECTID": 42,
                    "DEVICE_NAME": "I-285 at Roswell Rd",
                    "ROADWAY": "I-285",
                    "DIRECTION": "WB",
                    "IMAGE_URL": "https://example.test/camera.jpg",
                },
            }
        ],
    }

    cameras = parse_gdot_camera_geojson(body)
    assert len(cameras) == 1
    camera = cameras[0]
    assert camera.id == "gdot-arcgis:42"
    assert camera.roadway == "I-285"
    assert camera.direction == "WB"
    assert camera.point.latitude == 33.91
    assert camera.point.longitude == -84.37
    assert camera.provenance is not None
    assert camera.provenance.source_system == "GDOT_ARCGIS_CAMERA"
    assert camera.provenance.raw_sha256


def test_parse_gdot_camera_geojson_drops_invalid_geometry():
    body = {
        "features": [
            {"geometry": None, "properties": {"OBJECTID": 1}},
            {
                "geometry": {"type": "Point", "coordinates": [999, 999]},
                "properties": {"OBJECTID": 2},
            },
        ]
    }
    assert parse_gdot_camera_geojson(body) == []
