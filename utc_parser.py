#!/usr/bin/env python3
import argparse
import csv
import html
import re
from pathlib import Path
from bs4 import BeautifulSoup


def reconstruct_if_view_source(text: str) -> str:
    """Chrome 'view-source' saves the source inside a table. Reconstruct the real page HTML."""
    soup = BeautifulSoup(text, 'html.parser')
    cells = soup.select('td.line-content')
    if cells:
        return '\n'.join(c.get_text('', strip=False) for c in cells)
    return text


def search_meta(raw_html: str):
    decoded = html.unescape(raw_html)
    def pick(key):
        m = re.search(rf'["\']{re.escape(key)}["\']\s*:\s*["\']([^"\']+)', decoded)
        return m.group(1) if m else ''
    return {
        'Check-in': pick('startDate'),
        'Check-out': pick('endDate'),
        'Adults': pick('adults'),
        'Children': pick('children'),
        'Destination': pick('destinationName'),
    }


def clean_text(value: str) -> str:
    return ' '.join(value.split()) if value else ''


def extract_hotels(raw_html: str):
    soup = BeautifulSoup(raw_html, 'html.parser')
    meta = search_meta(raw_html)

    # TravelC renders desktop + mobile versions of each hotel card.
    # Keep one card per hotel, preferring the desktop c-extended card.
    candidates = soup.select('[data-hotelname]')
    seen = set()
    rows = []

    desktop = [c for c in candidates if 'c-extended' in (c.get('class') or [])]
    cards = desktop if desktop else candidates

    for card in cards:
        hotel = clean_text(card.get('data-hotelname', ''))
        if not hotel or hotel in seen:
            continue
        seen.add(hotel)

        price = clean_text(card.get('data-hotel-totalprice', '') or card.get('data-hotel-totalPrice', ''))

        room_type = ''
        meal_plan = ''

        # The cheapest combination summary sits in this block on TravelC hotel cards.
        summary_blocks = card.select('.u-line-height--1.clr--darkest-gray')
        for block in summary_blocks:
            bed = block.find('i', class_=lambda c: c and 'fa-bed-front' in c)
            if not bed:
                continue
            b = block.find('b')
            if b:
                room_type = clean_text(b.get_text(' ', strip=True))

            # Board basis is the next direct pb-5 div (icons vary by board type).
            for child in block.find_all('div', recursive=False):
                classes = child.get('class') or []
                if 'pb-5' in classes and not child.find('i', class_=lambda c: c and 'fa-bed-front' in c):
                    meal_plan = clean_text(child.get_text(' ', strip=True))
                    if meal_plan:
                        break
            break

        # Fallbacks if markup changes slightly.
        if not room_type:
            text = card.get_text(' | ', strip=True)
            m = re.search(r'\|\s*([^|]+?)\s*\|\s*(ROOM ONLY|WITH BREAKFAST|BREAKFAST|HALF BOARD|FULL BOARD|ALL INCLUSIVE)\s*\|', text, re.I)
            if m:
                room_type = clean_text(m.group(1))
                meal_plan = clean_text(m.group(2))

        rows.append({
            **meta,
            'Hotel Name': hotel,
            'Lowest Price': price,
            'Room Type': room_type,
            'Meal Plan': meal_plan,
        })

    return rows


def main():
    ap = argparse.ArgumentParser(description='Extract UTC/Travel Compositor hotel search results to CSV')
    ap.add_argument('input', help='Saved UTC results HTML/HTM file (including Chrome view-source saves)')
    ap.add_argument('-o', '--output', default='utc_results.csv', help='Output CSV path')
    args = ap.parse_args()

    src = Path(args.input)
    raw = src.read_text(encoding='utf-8', errors='ignore')
    raw = reconstruct_if_view_source(raw)
    rows = extract_hotels(raw)

    if not rows:
        raise SystemExit('No hotel result cards found.')

    fields = ['Destination', 'Check-in', 'Check-out', 'Adults', 'Children', 'Hotel Name', 'Lowest Price', 'Room Type', 'Meal Plan']
    with open(args.output, 'w', newline='', encoding='utf-8-sig') as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)

    print(f'Extracted {len(rows)} hotels -> {args.output}')

if __name__ == '__main__':
    main()
