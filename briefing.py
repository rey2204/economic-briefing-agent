import os
import requests
import boto3
from datetime import datetime, timedelta

# Load credentials from GitHub Secrets
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SES_CLIENT = boto3.client("ses", region_name="us-east-2")

# Target publication sources for macroeconomic intelligence
SOURCES = [
    {"name": "US Bureau of Economic Analysis (BEA)", "url": "https://www.bea.gov/data"},
    {"name": "Eurostat", "url": "https://ec.europa.eu/eurostat"},
    {"name": "IMF World Economic Outlook", "url": "https://www.imf.org/en/Publications/WEO"},
    {"name": "World Bank Global Economic Prospects", "url": "https://www.worldbank.org/en/publication/global-economic-prospects"},
    {"name": "Federal Reserve Economic Data (FRED)", "url": "https://fred.stlouisfed.org"},
    {"name": "Peterson Institute (PIIE)", "url": "https://www.piie.com"},
    {"name": "Kiel Institute for the World Economy", "url": "https://www.ifw-kiel.de"},
    {"name": "UNCTAD", "url": "https://unctad.org"},
    {"name": "JPMorgan Global Research", "url": "https://www.jpmorgan.com/insights/markets-and-economy/economy"},
    {"name": "Goldman Sachs Insights", "url": "https://www.goldmansachs.com/what-we-do/research"},
    {"name": "Bank of America Institute", "url": "https://institute.bankofamerica.com/"},
    {"name": "Deutsche Bank Research", "url": "https://corporates.db.com/solutions/investment-bank-solutions/Research/"},
    {"name": "PIMCO Insights", "url": "https://www.pimco.com/us/en/insights"},
    {"name": "AllianceBernstein", "url": "https://www.alliancebernstein.com/en/category/economics"},
    {"name": "Allianz Economic Research", "url": "https://www.allianz.com/en/economic_research.html"},
    {"name": "Wells Fargo Economic Insights", "url": "https://www.wellsfargo.com/cib/insights/economics/"},
    {"name": "U.S. Bank Economic Insights", "url": "https://www.usbank.com/wealth-management/financial-perspectives/market-and-economic-outlook.html"},
    {"name": "Moody's Analytics Economic View", "url": "https://www.economy.com"},
    {"name": "RBC Economics", "url": "https://thoughtleadership.rbc.com/economics/"},
    {"name": "Deloitte Insights", "url": "https://www2.deloitte.com/us/en/insights/economy.html"},
    {"name": "The Conference Board", "url": "https://www.conference-board.org/research/economy"},
    {"name": "FocusEconomics", "url": "https://www.focus-economics.com"},
    {"name": "National Bureau of Economic Research (NBER)", "url": "https://www.nber.org"},
    {"name": "Trading Economics", "url": "https://tradingeconomics.com"},
    {"name": "Observatory of Economic Complexity", "url": "https://oec.world"}
]

def main():
    collected_data = []
    print("Collecting publication data...")
    
    for source in SOURCES:
        print(f"Reading {source['name']}...")
        try:
            reader_url = f"https://r.jina.ai/{source['url']}"
            response = requests.get(reader_url, headers={"User-Agent": "Mozilla/5.0"}, timeout=20)
            if response.status_code == 200:
                content = response.text[:4000]
                collected_data.append(f"### SOURCE: {source['name']} ({source['url']})\n{content}\n")
        except Exception as e:
            print(f"Failed to fetch {source['url']}: {e}")

    compiled_context = "\n".join(collected_data)

    # Calculate rolling 7-day window
    current_date = datetime.now()
    start_date = current_date - timedelta(days=7)
    date_str_current = current_date.strftime("%B %d, %Y")
    date_str_start = start_date.strftime("%B %d, %Y")

    prompt = f"""You are an executive economic intelligence analyst. 
Based ONLY on the following source materials, synthesize this week's developments into an Axios-style briefing.

STRICT RECENCY REQUIREMENT: Today is {date_str_current}. You must ONLY include developments, reports, and data releases published between {date_str_start} and {date_str_current}. Actively discard and ignore any working papers, reports, or data points published prior to {date_str_start} (such as older static publications), even if they appear prominently on landing pages. If a source only contains older materials, omit it entirely.

Formatting guidelines:
1. Lead with the single most critical overarching macroeconomic development under a 'The Big Picture' section.
2. Follow with 3 to 5 key developments using concise bullet points.
3. Organize remaining analysis under clear thematic headers (Inflation, Monetary Policy, Trade, Labor, etc.).
4. Minimize academic or technical jargon; keep statements clear and impactful.
5. Provide explicit citations and URLs for every data point or finding.
6. Return your output as clean, semantic HTML (<p>, <ul>, <li>, <strong>, <h3>). Do not use Markdown backticks.

SOURCE DATA:
{compiled_context}
"""

    print("Generating briefing with Claude...")
    claude_response_raw = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={
            "x-api-key": ANTHROPIC_API_KEY,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        },
        json={
            "model": "claude-sonnet-5",
            "max_tokens": 16000,
            "messages": [{"role": "user", "content": prompt}]
        },
        timeout=300
    )
    
    claude_response = claude_response_raw.json()

    # Verify API response validity
    if "error" in claude_response:
        print(f"ANTHROPIC API ERROR: {claude_response['error']}")
        return

    # Extract text block while bypassing internal thinking blocks
    briefing_html = ""
    for block in claude_response.get("content", []):
        if block.get("type") == "text":
            briefing_html = block.get("text", "")
            break

    if not briefing_html:
        print("ERROR: No text content returned by Anthropic API.")
        return

    subject = f"Economic Intelligence Briefing — {date_str_current}"

    full_email_html = f"""
    <!DOCTYPE html>
    <html>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 800px; margin: auto; padding: 20px;">
        <div style="border-bottom: 2px solid #0052cc; padding-bottom: 8px; margin-bottom: 24px;">
            <h1 style="font-size: 24px; margin: 0; color: #111;">{subject}</h1>
            <p style="color: #666; font-size: 14px; margin: 4px 0 0;">Weekly Macroeconomic Synthesis</p>
        </div>
        {briefing_html}
    </body>
    </html>
    """

    print("Sending email...")
    SES_CLIENT.send_email(
        Source="adam.karson@gmail.com",
        Destination={"ToAddresses": ["adam.karson@expeditors.com", "adam.karson@gmail.com"]},
        Message={
            "Subject": {"Data": subject},
            "Body": {"Html": {"Data": full_email_html}}
        }
    )
    print("Briefing delivered successfully.")

if __name__ == "__main__":
    main()
