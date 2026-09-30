from app.geography import is_real_location


def test_recognizes_real_cities_and_countries():
	assert is_real_location('Tokyo')
	assert is_real_location('paris')
	assert is_real_location('Philadelphia')
	assert is_real_location('Japan')


def test_recognizes_us_states_by_name_and_code():
	assert is_real_location('New York')
	assert is_real_location('NY')
	assert is_real_location('ny') is False  # codes are matched case-sensitively


def test_rejects_non_geographic_text():
	assert is_real_location('Alamofire') is False
	assert is_real_location('Phat Philly') is False
	assert is_real_location('') is False
	assert is_real_location('   ') is False
