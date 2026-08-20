from src.ingestion.user_upload import infer_upload_metadata

SAMPLE_CSV = """county_fips,year,median_income,category
17019,2022,54000,urban
17021,2022,48000,rural
17023,2022,61000,urban
17025,2022,39000,rural
17027,2022,52000,urban
17029,2022,44000,rural
17031,2022,58000,urban
17033,2022,41000,rural
17035,2022,55000,urban
17037,2022,43000,rural
"""


def test_infers_geography_time_and_measures():
    result = infer_upload_metadata(SAMPLE_CSV)
    assert "county_fips" in result.detected_geography_columns
    assert "year" in result.detected_time_columns
    assert "median_income" in result.detected_numeric_measures
    assert "category" in result.detected_categorical_columns
    assert result.row_count == 10
    assert result.warnings == []


def test_empty_file_returns_warning():
    result = infer_upload_metadata("")
    assert "empty" in result.warnings[0].lower()


def test_no_geography_produces_warning():
    csv_text = "measure_a,measure_b\n1,2\n3,4\n"
    result = infer_upload_metadata(csv_text)
    assert any("geographic" in w.lower() for w in result.warnings)


def test_lat_lon_detected_as_point_geography():
    csv_text = "latitude,longitude,value\n41.8,-87.6,5\n42.0,-87.9,7\n"
    result = infer_upload_metadata(csv_text)
    assert result.detected_lat_lon is True
