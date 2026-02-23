"""
MT5 Trade Import Parser
Parses trades from HTML, XML, and Excel reports exported from MetaTrader 5
"""
from typing import List, Dict, Optional
from datetime import datetime
import io
import zipfile
import re

# Optional imports - will raise error if not installed
try:
    from bs4 import BeautifulSoup
    BS4_AVAILABLE = True
except ImportError:
    BS4_AVAILABLE = False

try:
    import xml.etree.ElementTree as ET
    XML_AVAILABLE = True
except ImportError:
    XML_AVAILABLE = False

try:
    import pandas as pd
    PANDAS_AVAILABLE = True
except ImportError:
    PANDAS_AVAILABLE = False


def parse_positions_from_mt5_html(content: bytes) -> List[Dict]:
    """
    Parse the 'Positions' table from an MT5 Trade History HTML report.
    Handles UTF-8, UTF-16, and other encodings automatically.
    """
    if not BS4_AVAILABLE:
        raise ImportError("beautifulsoup4 is required for HTML parsing. Install with: pip install beautifulsoup4")
    
    soup = BeautifulSoup(content, "html.parser")

    positions_header = soup.find("th", string=lambda s: s and "Positions" in s)
    if not positions_header:
        raise ValueError("Positions section not found in the report.")

    table = positions_header.find_parent("table")
    rows = table.find_all("tr")

    data = []
    in_positions = False
    header_row_found = False

    for row in rows:
        # Skip section headers (th elements with just section names)
        if row.find("th") and "Positions" in row.text:
            in_positions = True
            header_row_found = False
            continue
        
        if row.find("th") and "Orders" in row.text:
            break

        if not in_positions:
            continue

        # Skip rows that are header rows (have th elements or are the actual header row)
        # The header row in MT5 reports has bold (b) elements in td cells
        if row.find("th"):
            continue
            
        # Check if this looks like a header row (contains text like Time, Position, Symbol, etc.)
        row_text = row.get_text().lower()
        if "time" in row_text and "position" in row_text and "symbol" in row_text:
            header_row_found = True
            continue
            
        if header_row_found:
            # Skip the actual header row (first data row after header detection)
            header_row_found = False
            continue

        cells = row.find_all("td")
        if not cells:
            continue

        # Filter out hidden cells and empty values
        values = [
            cell.get_text(strip=True)
            for cell in cells
            if cell.get_text(strip=True) and "hidden" not in cell.get("class", [])
        ]

        if len(values) >= 3:
            # Check if first value looks like a date (our data rows start with dates like "2026.02.10")
            first_val = values[0] if values else ""
            if not first_val or not first_val[0].isdigit():
                continue
            position_data = {
                "open_time": values[0],
                "position": values[1],
                "symbol": values[2],
                "type": values[3],
                "volume": values[4],
                "open_price": values[5],
                "stop_loss": values[6],
                "take_profit": values[7],
                "close_time": values[8],
                "close_price": values[9],
                "commission": values[10],
                "swap": values[11],
                "profit": values[12],
            }
            data.append(position_data)

    return data


def parse_positions_from_mt5_xml(content: bytes) -> List[Dict]:
    """
    Parse the 'Positions' section from an MT5 XML report.
    """
    if not XML_AVAILABLE:
        raise ImportError("xml.etree.ElementTree is required for XML parsing")
    
    tree = ET.fromstring(content)
    data = []

    positions_section = tree.find(".//Positions")
    if positions_section is None:
        raise ValueError("Positions section not found in XML report.")

    for position in positions_section.findall("Position"):
        position_data = {
            "open_time": position.findtext("Time"),
            "position": position.findtext("Position"),
            "symbol": position.findtext("Symbol"),
            "type": position.findtext("Type"),
            "volume": position.findtext("Volume"),
            "open_price": position.findtext("Price"),
            "stop_loss": position.findtext("SL"),
            "take_profit": position.findtext("TP"),
            "close_time": position.findtext("TimeClose"),
            "close_price": position.findtext("PriceClose"),
            "commission": position.findtext("Commission"),
            "swap": position.findtext("Swap"),
            "profit": position.findtext("Profit"),
        }
        data.append(position_data)

    return data


def parse_positions_from_mt5_excel(content: bytes) -> List[Dict]:
    """
    Parse the 'Positions' section from an MT5 Excel (.xlsx) report.
    """
    if not PANDAS_AVAILABLE:
        raise ImportError("pandas is required for Excel parsing. Install with: pip install pandas openpyxl")
    
    df = pd.read_excel(io.BytesIO(content), header=None)

    # Find the row index where "Positions" appears
    positions_row_index = df[df.apply(
        lambda row: row.astype(str).str.contains("Positions", case=False).any(), 
        axis=1
    )].index

    if len(positions_row_index) == 0:
        raise ValueError("Positions section not found in Excel report.")

    start_index = positions_row_index[0] + 2  # Skip title and header rows

    data = []

    for i in range(start_index, len(df)):
        row = df.iloc[i]

        # Stop when we reach another section like Orders
        if row.astype(str).str.contains("Orders", case=False).any():
            break

        if row.isna().all():
            continue

        row_values = row.tolist()

        if len(row_values) >= 13:
            position_data = {
                "open_time": row_values[0],
                "position": row_values[1],
                "symbol": row_values[2],
                "type": row_values[3],
                "volume": row_values[4],
                "open_price": row_values[5],
                "stop_loss": row_values[6],
                "take_profit": row_values[7],
                "close_time": row_values[8],
                "close_price": row_values[9],
                "commission": row_values[10],
                "swap": row_values[11],
                "profit": row_values[12],
            }
            data.append(position_data)

    return data


def parse_trade_file(content: bytes, filename: str) -> List[Dict]:
    """
    Auto-detect file type and parse accordingly.
    """
    ext = filename.lower().split('.')[-1]
    
    if ext == 'html' or ext == 'htm':
        return parse_positions_from_mt5_html(content)
    elif ext == 'xml':
        return parse_positions_from_mt5_xml(content)
    elif ext == 'xlsx' or ext == 'xls':
        return parse_positions_from_mt5_excel(content)
    else:
        raise ValueError(f"Unsupported file format: {ext}")


def _safe_parse_num(val) -> float:
    """Safely parse a numeric value from string, handling edge cases."""
    if val is None:
        return 0.0
    # Convert to string and strip
    val_str = str(val).strip()
    if not val_str or val_str == "-" or val_str == "":
        return 0.0
    # Remove commas and try to convert
    try:
        return float(val_str.replace(",", ""))
    except (ValueError, AttributeError):
        return 0.0


def convert_to_trade_format(position: Dict, account_id: str) -> Dict:
    """
    Convert MT5 position data to our Trade model format.
    """
    # Validate required fields
    if not position.get("open_time") or not position.get("symbol"):
        raise ValueError(f"Invalid position data: missing required fields - {position}")
    
    # Parse datetime
    try:
        executed_at = datetime.strptime(str(position["open_time"]), "%Y.%m.%d %H:%M:%S")
    except (ValueError, TypeError):
        executed_at = datetime.now()
    
    try:
        close_time = datetime.strptime(str(position["close_time"]), "%Y.%m.%d %H:%M:%S") if position.get("close_time") else None
    except (ValueError, TypeError):
        close_time = None
    
    # Calculate duration
    duration = "0"
    if close_time:
        duration_delta = close_time - executed_at
        hours, remainder = divmod(int(duration_delta.total_seconds()), 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours > 0:
            duration = f"{hours}h {minutes}m"
        else:
            duration = f"{minutes}m"
    
    # Determine status
    profit = _safe_parse_num(position.get("profit"))
    status = "WIN" if profit > 0 else "LOSS" if profit < 0 else "BE"
    
    # Get trade type
    trade_type_raw = str(position.get("type", "")).lower().strip()
    if "limit" in trade_type_raw:
        trade_type = "Limit"
    elif "stop" in trade_type_raw:
        trade_type = "Stop"
    else:
        trade_type = "Day Trade"
    
    # Get execution type
    execution_type = "Market" if not any(x in trade_type_raw for x in ["limit", "stop"]) else "Limit" if "limit" in trade_type_raw else "Stop"
    
    # Extract time strings
    entry_time_str = executed_at.strftime("%H:%M") if executed_at else "00:00"
    close_time_str = close_time.strftime("%H:%M") if close_time else "00:00"
    
    return {
        "account_id": account_id,
        "symbol": str(position.get("symbol", "")).strip(),
        "side": "SHORT" if trade_type_raw == "sell" else "LONG",
        "entry_price": _safe_parse_num(position.get("open_price")),
        "exit_price": _safe_parse_num(position.get("close_price")),
        "close_price": _safe_parse_num(position.get("close_price")),
        "quantity": _safe_parse_num(position.get("volume")),
        "pnl": profit,
        "commission": _safe_parse_num(position.get("commission")),
        "swap": _safe_parse_num(position.get("swap")),
        "duration": duration,
        "trade_type": trade_type,
        "execution_type": execution_type,
        "status": status,
        "stop_loss": _safe_parse_num(position.get("stop_loss")),
        "take_profit": _safe_parse_num(position.get("take_profit")),
        "setups": [],
        "general_tags": [],
        "exit_tags": [],
        "process_tags": [],
        "notes": None,
        "executed_at": executed_at.isoformat() if executed_at else datetime.now().isoformat(),
        "closed_at": close_time.isoformat() if close_time else None,
        "date": executed_at.date().isoformat() if executed_at else datetime.now().date().isoformat(),
        "time": entry_time_str,
        "close_time": close_time_str,
    }