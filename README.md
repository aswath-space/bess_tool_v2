# ⚡ PV-BESS Revenue Optimization Tool

**Quantify revenue potential for solar + battery storage using real market data.**

[![Streamlit](https://img.shields.io/badge/Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io)
[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)

---

## 🌟 Features

- **PV Baseline Analysis**: Calculate solar generation revenue with cannibalization effects
- **Battery Optimization**: Linear programming optimization for energy arbitrage
- **Financial Analysis**: IRR, NPV, payback period with degradation modeling
- **Real Market Data**: ENTSO-E electricity prices + PVGIS solar irradiation
- **Data Export**: Download all analysis data as CSV + JSON in ZIP format

---

## 🚀 Quick Start

### Option 1: Streamlit Cloud (Recommended)

1. **Fork** this repository
2. Go to [share.streamlit.io](https://share.streamlit.io)
3. Click **"New app"**
4. Select your forked repository
5. **Main file**: `streamlit_app.py`
6. Click **"Advanced settings"** → **"Secrets"**
7. Add your ENTSO-E API key:
   ```toml
   [entsoe]
   api_key = "your-api-key-here"
   ```
8. Click **"Deploy"**

### Option 2: Local Development

```bash
# 1. Clone the repository
git clone <your-repo-url>
cd bess_tool_01-main

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure your API key
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# Edit .streamlit/secrets.toml and add your ENTSO-E API key

# 4. Run the app
streamlit run streamlit_app.py
```

---

## 🔑 Getting an ENTSO-E API Key

1. Register at [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/)
2. Log in and go to **Account Settings**
3. Navigate to **"Web API Security Token"**
4. Generate and copy your API key
5. Add it to your secrets configuration

---

## 📁 Project Structure

```
bess_tool_01-main/
├── streamlit_app.py          # Main Streamlit application
├── requirements.txt           # Python dependencies
├── backend/
│   └── app/
│       └── services/          # Business logic (PV, ENTSO-E, optimization)
├── ui/                        # UI components (stages 1, 2, 3)
└── .streamlit/
    ├── config.toml            # Streamlit configuration
    └── secrets.toml.example   # Secrets template
```

---

## 🛠️ Technology Stack

- **Frontend**: Streamlit
- **Data**: ENTSO-E API, PVGIS API
- **Optimization**: CVXPY (Linear Programming)
- **Visualization**: Plotly
- **Financial Modeling**: numpy-financial

---

## 📊 Usage

### Stage 1: PV Baseline
1. Enter location (city search or coordinates)
2. Configure PV system (capacity, tilt, azimuth, cost)
3. Click "Calculate Baseline"
4. Review cannibalization analysis

### Stage 2: Battery Optimization
1. Accept smart battery defaults or customize
2. Click "Optimize with Battery"
3. Review revenue increase and operations timeline

### Stage 3: Financial Analysis
1. Set financial parameters (discount rate, degradation)
2. Review IRR, NPV, payback period
3. Download all data as ZIP

---

## 🔒 Environment Variables

### For Local Development

Create `.streamlit/secrets.toml`:
```toml
[entsoe]
api_key = "your-entsoe-api-key"
```

### For Streamlit Cloud

Add in app settings → Secrets:
```toml
[entsoe]
api_key = "your-entsoe-api-key"
```

---

## 🐛 Troubleshooting

### "ENTSO-E API Key not found"
- **Local**: Make sure `.streamlit/secrets.toml` exists with your API key
- **Cloud**: Check app settings → Secrets is configured correctly

### "Module not found" errors
```bash
pip install -r requirements.txt --upgrade
```

### Data fetch timeout
- ENTSO-E API can be slow for large date ranges
- Default: fetches last 365 days of hourly data (~8,760 data points)

---

## 📄 License

This project is provided as-is for educational and research purposes.

---

## 🙏 Credits

- **Market Data**: [ENTSO-E Transparency Platform](https://transparency.entsoe.eu/)
- **Solar Data**: [PVGIS](https://re.jrc.ec.europa.eu/pvg_tools/en/)
- **Optimization**: [CVXPY](https://www.cvxpy.org/)
- **Built with**: [Streamlit](https://streamlit.io)

---

## 📧 Support

For issues or questions, please open an issue on GitHub.

---

**Made with ⚡ by Your Team | © 2025**
