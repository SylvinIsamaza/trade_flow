"""
MT5 Trade Import Parser
Parses trades from HTML, XML, and Excel reports exported from MetaTrader 5
"""
from typing import List, Dict, Optional, Any
from datetime import datetime
import io
import zipfile
import re
import csv

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
            first_val = values[0] if values and values[0] is not None else ""
            if not first_val or not str(first_val)[0].isdigit():
                continue

            # Ensure we have at least 13 columns expected by MT5 positions table
            if len(values) < 13:
                values += [None] * (13 - len(values))

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


def parse_tabular_trade_file(content: bytes, filename: str) -> Dict[str, Any]:
    """
    Parse a generic CSV/Excel file into columns and row dictionaries.
    Used by the "Other" import flow where users map source columns manually.
    """
    ext = filename.lower().split('.')[-1]

    def json_safe(value):
        if value is None:
            return None
        if isinstance(value, datetime):
            return value.isoformat()
        if PANDAS_AVAILABLE:
            try:
                if pd.isna(value):
                    return None
                if hasattr(value, "isoformat"):
                    return value.isoformat()
            except Exception:
                pass
        if isinstance(value, (int, float, str, bool)):
            return value
        return str(value)

    if ext in ["xlsx", "xls"]:
        if not PANDAS_AVAILABLE:
            raise ImportError("pandas is required for Excel parsing. Install with: pip install pandas openpyxl")
        df = pd.read_excel(io.BytesIO(content))
        df = df.where(pd.notna(df), None)
        columns = [str(col).strip() for col in df.columns]
        rows = [
            {str(key).strip(): json_safe(value) for key, value in row.items()}
            for row in df.to_dict(orient="records")
        ]
        return {"columns": columns, "rows": rows}

    if ext == "csv":
        text = content.decode("utf-8-sig", errors="replace")
        sample = text[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample)
        except csv.Error:
            dialect = csv.excel
        reader = csv.DictReader(io.StringIO(text), dialect=dialect)
        columns = [str(col).strip() for col in (reader.fieldnames or [])]
        rows = [
            {str(key).strip(): json_safe(value) for key, value in row.items()}
            for row in reader
        ]
        return {"columns": columns, "rows": rows}

    raise ValueError(f"Unsupported file format for custom import: {ext}")


def _safe_parse_num(val) -> float:
    """Safely parse a numeric value from string, handling edge cases."""
    if val is None:
        return 0.0
    # Numeric types
    if isinstance(val, (int, float)):
        try:
            return float(val)
        except Exception:
            return 0.0
    # pandas NA handling
    if PANDAS_AVAILABLE:
        try:
            if pd.isna(val):
                return 0.0
        except Exception:
            pass

    s = str(val).strip()
    if not s or s == "-":
        return 0.0

    # Handle numbers in parentheses as negatives e.g. (1,234.56)
    negative = False
    if s.startswith("(") and s.endswith(")"):
        negative = True
        s = s[1:-1].strip()

    # Remove currency symbols and non-number characters except dot, comma and minus
    s = re.sub(r"[^0-9.,\-]", "", s)
    # Remove thousands separators
    s = s.replace(",", "")
    if not s:
        return 0.0
    try:
        value = float(s)
        return -value if negative else value
    except ValueError:
        return 0.0


def _safe_parse_bool(val) -> Optional[bool]:
    if val is None:
        return None
    val_str = str(val).strip().lower()
    if val_str in ["true", "yes", "y", "1", "checked"]:
        return True
    if val_str in ["false", "no", "n", "0", "unchecked"]:
        return False
    return None


def _safe_parse_datetime(val) -> Optional[datetime]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val
    if PANDAS_AVAILABLE:
        try:
            parsed = pd.to_datetime(val)
            if not pd.isna(parsed):
                return parsed.to_pydatetime()
        except Exception:
            pass
    val_str = str(val).strip()
    for fmt in [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%d",
        "%Y.%m.%d %H:%M:%S",
        "%Y.%m.%d %H:%M",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%m/%d/%Y",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
    ]:
        try:
            return datetime.strptime(val_str, fmt)
        except ValueError:
            continue
    return None


def _split_list_value(val) -> List[str]:
    if val is None:
        return []
    if isinstance(val, list):
        return [str(item).strip() for item in val if str(item).strip()]
    return [
        part.strip()
        for part in re.split(r"[,;|]", str(val))
        if part.strip()
    ]


def _mapped_value(row: Dict, column_mapping: Dict[str, str], field: str):
    column = column_mapping.get(field)
    if not column:
        return None
    return row.get(column)


def convert_mapped_row_to_trade_format(row: Dict, column_mapping: Dict[str, str], account_id: str) -> Dict:
    """
    Convert a user-mapped generic row to our Trade model format.
    Mapping format is { trade_field: source_column_name }.
    """
    symbol = str(_mapped_value(row, column_mapping, "symbol") or "").strip()
    if not symbol:
        raise ValueError("Missing required symbol")

    side_raw = str(_mapped_value(row, column_mapping, "side") or "").strip().lower()
    side = "SHORT" if side_raw in ["short", "sell", "s"] else "LONG"

    executed_at = _safe_parse_datetime(_mapped_value(row, column_mapping, "executed_at"))
    date_value = _safe_parse_datetime(_mapped_value(row, column_mapping, "date"))
    time_value = str(_mapped_value(row, column_mapping, "time") or "").strip()
    if not executed_at and date_value:
        executed_at = date_value
        if time_value:
            time_dt = _safe_parse_datetime(f"{date_value.date().isoformat()} {time_value}")
            if time_dt:
                executed_at = time_dt
    if not executed_at:
        executed_at = datetime.now()

    closed_at = _safe_parse_datetime(_mapped_value(row, column_mapping, "closed_at"))
    close_time_value = str(_mapped_value(row, column_mapping, "close_time") or "").strip()
    if not closed_at and close_time_value:
        close_dt = _safe_parse_datetime(f"{executed_at.date().isoformat()} {close_time_value}")
        if close_dt:
            closed_at = close_dt

    pnl = _safe_parse_num(_mapped_value(row, column_mapping, "pnl"))
    mapped_status = str(_mapped_value(row, column_mapping, "status") or "").strip().upper()
    status = mapped_status if mapped_status in ["WIN", "LOSS", "BE"] else "WIN" if pnl > 0 else "LOSS" if pnl < 0 else "BE"

    return {
        "account_id": account_id,
        "symbol": symbol,
        "side": side,
        "entry_price": _safe_parse_num(_mapped_value(row, column_mapping, "entry_price")),
        "exit_price": _safe_parse_num(_mapped_value(row, column_mapping, "exit_price")),
        "close_price": _safe_parse_num(_mapped_value(row, column_mapping, "close_price")) or _safe_parse_num(_mapped_value(row, column_mapping, "exit_price")),
        "quantity": _safe_parse_num(_mapped_value(row, column_mapping, "quantity")),
        "pnl": pnl,
        "commission": _safe_parse_num(_mapped_value(row, column_mapping, "commission")),
        "swap": _safe_parse_num(_mapped_value(row, column_mapping, "swap")),
        "duration": str(_mapped_value(row, column_mapping, "duration") or ""),
        "trade_type": str(_mapped_value(row, column_mapping, "trade_type") or "Day Trade"),
        "execution_type": str(_mapped_value(row, column_mapping, "execution_type") or "Market"),
        "status": status,
        "stop_loss": _safe_parse_num(_mapped_value(row, column_mapping, "stop_loss")),
        "take_profit": _safe_parse_num(_mapped_value(row, column_mapping, "take_profit")),
        "session": _mapped_value(row, column_mapping, "session"),
        "higher_timeframe_bias": _mapped_value(row, column_mapping, "higher_timeframe_bias"),
        "trend_structure": _mapped_value(row, column_mapping, "trend_structure"),
        "key_levels": _mapped_value(row, column_mapping, "key_levels"),
        "entry_model": _mapped_value(row, column_mapping, "entry_model"),
        "reason_for_entry": _mapped_value(row, column_mapping, "reason_for_entry"),
        "confirmation_used": _mapped_value(row, column_mapping, "confirmation_used"),
        "dollar_amount_risked": _safe_parse_num(_mapped_value(row, column_mapping, "dollar_amount_risked")),
        "percentage_risked": _safe_parse_num(_mapped_value(row, column_mapping, "percentage_risked")),
        "energy_level": int(_safe_parse_num(_mapped_value(row, column_mapping, "energy_level"))) if _mapped_value(row, column_mapping, "energy_level") is not None else None,
        "emotions": _mapped_value(row, column_mapping, "emotions"),
        "confidence_level": int(_safe_parse_num(_mapped_value(row, column_mapping, "confidence_level"))) if _mapped_value(row, column_mapping, "confidence_level") is not None else None,
        "forcing_trades": _safe_parse_bool(_mapped_value(row, column_mapping, "forcing_trades")),
        "sleep_quality": _mapped_value(row, column_mapping, "sleep_quality"),
        "distractions": _mapped_value(row, column_mapping, "distractions"),
        "actual_rr_achieved": _safe_parse_num(_mapped_value(row, column_mapping, "actual_rr_achieved")),
        "pips_gained_lost": _safe_parse_num(_mapped_value(row, column_mapping, "pips_gained_lost")),
        "followed_plan": _safe_parse_bool(_mapped_value(row, column_mapping, "followed_plan")),
        "entered_too_early": _safe_parse_bool(_mapped_value(row, column_mapping, "entered_too_early")),
        "moved_sl": _safe_parse_bool(_mapped_value(row, column_mapping, "moved_sl")),
        "closed_early_from_fear": _safe_parse_bool(_mapped_value(row, column_mapping, "closed_early_from_fear")),
        "greed_affected_tp": _safe_parse_bool(_mapped_value(row, column_mapping, "greed_affected_tp")),
        "what_actually_happened": _mapped_value(row, column_mapping, "what_actually_happened"),
        "setup_worked_as_expected": _safe_parse_bool(_mapped_value(row, column_mapping, "setup_worked_as_expected")),
        "abnormal_volatility": _safe_parse_bool(_mapped_value(row, column_mapping, "abnormal_volatility")),
        "news_event_involved": _mapped_value(row, column_mapping, "news_event_involved"),
        "screenshot_annotations": _mapped_value(row, column_mapping, "screenshot_annotations"),
        "trade_commentary": _mapped_value(row, column_mapping, "trade_commentary"),
        "setups": _split_list_value(_mapped_value(row, column_mapping, "setups")),
        "general_tags": _split_list_value(_mapped_value(row, column_mapping, "general_tags")),
        "exit_tags": _split_list_value(_mapped_value(row, column_mapping, "exit_tags")),
        "process_tags": _split_list_value(_mapped_value(row, column_mapping, "process_tags")),
        "notes": _mapped_value(row, column_mapping, "notes"),
        "executed_at": executed_at.isoformat(),
        "closed_at": closed_at.isoformat() if closed_at else None,
        "date": executed_at.date().isoformat(),
        "time": executed_at.strftime("%H:%M"),
        "close_time": closed_at.strftime("%H:%M") if closed_at else close_time_value or None,
    }


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
