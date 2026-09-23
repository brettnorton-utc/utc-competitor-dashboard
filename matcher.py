import re
from rapidfuzz import fuzz, process


def price_to_float(value):
    if value is None:
        return None
    m = re.search(r'-?\d[\d,]*(?:\.\d+)?', str(value))
    return float(m.group(0).replace(',', '')) if m else None


def normalize_name(name: str) -> str:
    s = (name or '').lower()
    s = s.replace('&', ' and ')
    # Standardise common brand/location noise without over-normalising.
    replacements = {
        'doubletree by hilton hotel': 'doubletree by hilton',
        'radisson blu hotel': 'radisson blu',
        'hotel leeds city centre': 'leeds',
        'city center': 'city centre',
        ' by ihg': '',
    }
    for a, b in replacements.items():
        s = s.replace(a, b)
    s = re.sub(r'[^a-z0-9]+', ' ', s)
    return ' '.join(s.split())


def match_hotels(utc_rows, booking_rows, threshold=72):
    booking_lookup = {normalize_name(r['Hotel Name']): r for r in booking_rows}
    booking_names = list(booking_lookup.keys())
    used = set()
    matches = []

    for u in utc_rows:
        un = normalize_name(u['Hotel Name'])
        best = process.extractOne(un, booking_names, scorer=fuzz.token_set_ratio)
        if not best:
            continue
        bn, score, _ = best
        b = booking_lookup[bn]

        # Prevent one Booking.com property from being used twice.
        if bn in used or score < threshold:
            continue

        up = price_to_float(u.get('Lowest Price'))
        bp = price_to_float(b.get('Lowest Price'))
        if up is None or bp is None:
            continue

        used.add(bn)
        saving = bp - up
        saving_pct = (saving / bp * 100) if bp else 0
        status = 'UTC cheaper' if saving > 0.005 else ('Booking.com cheaper' if saving < -0.005 else 'Same price')
        confidence = 'High' if score >= 90 else ('Medium' if score >= 80 else 'Review')

        matches.append({
            'UTC Hotel': u['Hotel Name'],
            'Booking.com Hotel': b['Hotel Name'],
            'Match Score': round(score, 1),
            'Match Confidence': confidence,
            'UTC Price': up,
            'Booking.com Price': bp,
            'Saving £': round(saving, 2),
            'Saving %': round(saving_pct, 1),
            'Result': status,
            'UTC Room': u.get('Room Type', ''),
            'Booking.com Room': b.get('Room Type', ''),
            'UTC Meal Plan': u.get('Meal Plan', ''),
            'Booking.com Meal Plan': b.get('Meal Plan', ''),
            'Booking Cancellation': b.get('Cancellation', ''),
            'Booking Taxes/Charges': b.get('Taxes/Charges', ''),
        })

    return matches
