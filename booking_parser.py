import re
from urllib.parse import urlparse, parse_qs
from bs4 import BeautifulSoup


def clean_text(value: str) -> str:
    return ' '.join(value.split()) if value else ''


def _first_text(node, testid: str) -> str:
    el = node.find(attrs={'data-testid': testid})
    return clean_text(el.get_text(' ', strip=True)) if el else ''


def _query_meta(raw_html: str):
    soup = BeautifulSoup(raw_html, 'html.parser')
    source_comment = ''
    for c in soup.find_all(string=lambda s: s and 'saved from url=' in s):
        source_comment = str(c)
        break

    # Chrome save comment is easiest to read via regex because the URL is wrapped.
    m = re.search(r'https://www\.booking\.com/[^\s>]+', raw_html)
    url = m.group(0).replace('&amp;', '&') if m else ''
    q = parse_qs(urlparse(url).query) if url else {}

    def one(key, default=''):
        return q.get(key, [default])[0]

    return {
        'Destination': clean_text(one('ss', '')),
        'Check-in': one('checkin'),
        'Check-out': one('checkout'),
        'Adults': one('group_adults'),
        'Children': one('group_children'),
        'Rooms': one('no_rooms'),
    }


def extract_hotels(raw_html: str):
    soup = BeautifulSoup(raw_html, 'html.parser')
    meta = _query_meta(raw_html)
    rows = []
    seen = set()

    for card in soup.find_all(attrs={'data-testid': 'property-card'}):
        hotel = _first_text(card, 'title')
        if not hotel or hotel in seen:
            continue
        seen.add(hotel)

        price = _first_text(card, 'price-and-discounted-price')
        if not price:
            # Fallback to availability block; take last GBP amount, usually current price.
            info = _first_text(card, 'availability-rate-information')
            prices = re.findall(r'£\s*[\d,]+(?:\.\d{1,2})?', info)
            price = prices[-1] if prices else ''

        room = _first_text(card, 'recommended-units')
        # Strip bed-count copy from room where possible.
        room = re.sub(r'\s+(?:\d+\s+)?(?:double|single|large double|sofa|twin|king|queen) beds?.*$', '', room, flags=re.I)
        room = clean_text(room)

        card_text = clean_text(card.get_text(' ', strip=True))
        breakfast = bool(re.search(r'breakfast included|free .*breakfast|with breakfast', card_text, re.I))
        meal_plan = 'Breakfast included' if breakfast else 'Not stated'
        cancellation = 'Free cancellation' if re.search(r'free cancellation', card_text, re.I) else 'Not stated'
        taxes = _first_text(card, 'taxes-and-charges') or ('Includes taxes and charges' if 'Includes taxes and charges' in card_text else '')

        link = card.find(attrs={'data-testid': 'title-link'})
        href = link.get('href', '') if link else ''
        property_slug = ''
        mm = re.search(r'/hotel/[^/]+/([^.?/]+)', href)
        if mm:
            property_slug = mm.group(1)

        rows.append({
            **meta,
            'Hotel Name': hotel,
            'Lowest Price': price,
            'Room Type': room,
            'Meal Plan': meal_plan,
            'Cancellation': cancellation,
            'Taxes/Charges': taxes,
            'Booking Property Slug': property_slug,
        })

    return rows
