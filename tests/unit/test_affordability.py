from app.services.affordability import calculate_affordability

def test_calculate_affordability_buy_affordable():
    result = calculate_affordability(
        income=100000,
        property_price=400000,
        buy_or_rent="buy",
        deposit_percent=20
    )
    assert result["affordable"] is True
    assert result["max_price"] == 530000.0  # (100k * 4.5) + (400k * 0.2)
    assert result["ratio"] == 4.0

def test_calculate_affordability_buy_unaffordable():
    result = calculate_affordability(
        income=50000,
        property_price=400000,
        buy_or_rent="buy",
        deposit_percent=20
    )
    assert result["affordable"] is False
    assert result["max_price"] == 305000.0  # (50k * 4.5) + (400k * 0.2)
    assert result["ratio"] == 8.0

def test_calculate_affordability_rent_affordable():
    result = calculate_affordability(
        income=60000,
        property_price=1200,
        buy_or_rent="rent"
    )
    assert result["affordable"] is True
    assert result["max_price"] == 1500.0  # (60k / 12) * 0.3
    assert result["ratio"] == 0.24 # 1200 / 5000

def test_calculate_affordability_rent_unaffordable():
    result = calculate_affordability(
        income=40000,
        property_price=1500,
        buy_or_rent="rent"
    )
    assert result["affordable"] is False
    assert result["max_price"] == 1000.0  # (40k / 12) * 0.3
    assert result["ratio"] == 0.45 # 1500 / 3333.33

def test_calculate_affordability_zero_income():
    result = calculate_affordability(
        income=0,
        property_price=1000,
        buy_or_rent="rent"
    )
    assert result["affordable"] is False
    assert result["ratio"] == 0
