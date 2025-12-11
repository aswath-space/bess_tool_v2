# Manual Price Data Upload Template
# ===================================
# Format: CSV with timestamp index and 'price' column
# Units: EUR/MWh
# Frequency: Hourly

# Example structure:
# timestamp,price
# 2024-01-01 00:00:00+00:00,45.32
# 2024-01-01 01:00:00+00:00,42.18
# 2024-01-01 02:00:00+00:00,38.95
# ...

# Instructions:
# 1. Name your file: {ZONE_CODE}.csv (e.g., DE_LU.csv, FR.csv)
# 2. Place in: backend/data/prices/
# 3. Use UTC timezone for timestamps
# 4. Ensure hourly data (8760 hours for full year)

# For fallback data (when zone-specific not available):
# - Name file: fallback.csv
# - Use same format as above
