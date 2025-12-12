def macro_regime(slope, cpi_yoy, real_yield):
    score = 0

    # Yield curve
    if slope < 0:
        score += 2
    elif slope < 0.3:
        score += 1

    # Inflation
    if cpi_yoy > 4:
        score += 2
    elif cpi_yoy > 2:
        score += 1

    # Real yield
    if real_yield > 1:
        score += 1

    # Classification
    if score <= 1:
        return "Green (Goldilocks)"
    elif score <= 3:
        return "Yellow (Caution)"
    else:
        return "Red (Macro Stress)"
