import pandas as pd
import streamlit as st

from utc_parser import reconstruct_if_view_source, extract_hotels as extract_utc
from booking_parser import extract_hotels as extract_booking
from matcher import match_hotels

st.set_page_config(page_title='UTC Competitor Price Dashboard', page_icon='✈️', layout='wide')

st.title('UTC Competitor Price Dashboard')
st.caption('Proof of concept: compare saved UTC Travel Compositor and Booking.com hotel search results.')

with st.sidebar:
    st.header('Files')
    utc_file = st.file_uploader('UTC results HTML', type=['html', 'htm', 'mhtml'])
    booking_file = st.file_uploader('Booking.com results HTML', type=['html', 'htm'])
    threshold = st.slider('Hotel match threshold', 60, 100, 72, help='Higher values are stricter. Review medium/low-confidence matches.')

if not utc_file or not booking_file:
    st.info('Upload one saved UTC results page and one saved Booking.com results page for the same destination, dates and guest mix.')
    st.stop()

utc_raw = utc_file.getvalue().decode('utf-8', errors='ignore')
utc_raw = reconstruct_if_view_source(utc_raw)
booking_raw = booking_file.getvalue().decode('utf-8', errors='ignore')

utc_rows = extract_utc(utc_raw)
booking_rows = extract_booking(booking_raw)

if not utc_rows:
    st.error('No UTC hotel cards were found in this file.')
    st.stop()
if not booking_rows:
    st.error('No Booking.com property cards were found in this file.')
    st.stop()

matches = match_hotels(utc_rows, booking_rows, threshold=threshold)
if not matches:
    st.warning('No hotel matches met the current threshold. Try lowering the match threshold or check that both files are for the same search.')
    st.stop()

df = pd.DataFrame(matches)

# Search summary from parsed UTC data.
m = utc_rows[0]
search_bits = [x for x in [m.get('Destination'), f"{m.get('Check-in')} → {m.get('Check-out')}" if m.get('Check-in') else '', f"{m.get('Adults')} adults" if m.get('Adults') else '', f"{m.get('Children')} children" if m.get('Children') else ''] if x]
st.subheader(' · '.join(search_bits))

compared = len(df)
utc_cheaper = int((df['Saving £'] > 0).sum())
booking_cheaper = int((df['Saving £'] < 0).sum())
same = compared - utc_cheaper - booking_cheaper
utc_total = df['UTC Price'].sum()
booking_total = df['Booking.com Price'].sum()
total_saving = booking_total - utc_total
weighted_pct = total_saving / booking_total * 100 if booking_total else 0
avg_saving = df['Saving £'].mean()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric('Hotels compared', f'{compared}')
c2.metric('UTC cheaper', f'{utc_cheaper}/{compared}', f'{utc_cheaper/compared*100:.0f}%')
c3.metric('Total saving', f'£{total_saving:,.0f}', f'{weighted_pct:.1f}%')
c4.metric('Average saving', f'£{avg_saving:,.2f}')
c5.metric('Booking.com cheaper', f'{booking_cheaper}/{compared}')

st.markdown('### Price comparison')
chart_df = df.sort_values('Saving £', ascending=True).set_index('UTC Hotel')[['Saving £']]
st.bar_chart(chart_df, horizontal=True, use_container_width=True)

st.markdown('### Matched hotels')
display = df.sort_values('Saving £', ascending=False).copy()
display['UTC Price'] = display['UTC Price'].map(lambda x: f'£{x:,.2f}')
display['Booking.com Price'] = display['Booking.com Price'].map(lambda x: f'£{x:,.2f}')
display['Saving £'] = display['Saving £'].map(lambda x: f'£{x:,.2f}')
display['Saving %'] = display['Saving %'].map(lambda x: f'{x:.1f}%')
st.dataframe(display, use_container_width=True, hide_index=True)

with st.expander('Extraction / matching diagnostics'):
    d1, d2, d3 = st.columns(3)
    d1.metric('UTC hotels extracted', len(utc_rows))
    d2.metric('Booking.com hotels extracted', len(booking_rows))
    d3.metric('Matched hotels', compared)
    st.caption('POC warning: headline figures compare each site’s cheapest displayed result. Room, board and cancellation terms may differ. Review match confidence and rate details before treating a comparison as like-for-like.')

csv = df.to_csv(index=False).encode('utf-8-sig')
st.download_button('Download comparison CSV', data=csv, file_name='utc_booking_comparison.csv', mime='text/csv')
