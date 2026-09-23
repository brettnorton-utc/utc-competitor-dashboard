# UTC Competitor Price Dashboard POC

A small Streamlit proof of concept that compares saved hotel results pages from UTC / Travel Compositor and Booking.com.

## What it does

- Upload a UTC results `.htm/.html` file
- Upload a Booking.com results `.html` file for the same search
- Extract hotel names, prices and rate details
- Fuzzy-match hotels across the two sites
- Show headline savings KPIs, chart and comparison table
- Download matched results as CSV

## Deploy on Streamlit Community Cloud

1. Create a new GitHub repository.
2. Upload these five files to the repository root:
   - `app.py`
   - `utc_parser.py`
   - `booking_parser.py`
   - `matcher.py`
   - `requirements.txt`
3. In Streamlit Community Cloud choose **Create app** / **Deploy an app**.
4. Select your GitHub repository and branch.
5. Set **Main file path** to `app.py`.
6. Deploy.

No secrets or API keys are needed for this manual-upload POC.

## Local run (optional)

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Important POC caveat

The headline comparison uses each site's cheapest displayed rate. That proves price extraction and hotel matching, but it is not necessarily a strict like-for-like comparison because room type, board basis, cancellation terms or other conditions may differ. Those fields are retained in the output to support a later like-for-like matching layer.
