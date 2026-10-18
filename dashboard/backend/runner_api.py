import sys
import os
import importlib.util
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import tempfile
import shutil
import orjson
import zipfile
import io

from prosperity4bt.runner import run_backtest
from prosperity4bt.file_reader import FileSystemReader
from prosperity4bt.models import BacktestResult, TradeMatchingMode

def serialize_backtest_result(result: BacktestResult) -> Dict[str, Any]:
    """Converts a BacktestResult object into a JSON-serializable dictionary."""
    return {
        "round_num": result.round_num,
        "day_num": result.day_num,
        "sandbox_logs": [
            {
                "timestamp": log.timestamp,
                "sandbox_log": log.sandbox_log,
                "lambda_log": log.lambda_log
            } for log in result.sandbox_logs
        ],
        "activity_logs": [
            {
                "timestamp": log.timestamp,
                "columns": log.columns
            } for log in result.activity_logs
        ],
        "trades": [
            {
                "timestamp": trade.trade.timestamp,
                "symbol": trade.trade.symbol,
                "price": trade.trade.price,
                "quantity": trade.trade.quantity,
                "buyer": trade.trade.buyer,
                "seller": trade.trade.seller
            } for trade in result.trades
        ]
    }

def process_data_package(files: List[Tuple[str, str]]) -> Dict[str, str]:
    """
    Processes a list of (filename, content) tuples and identifies prices, trades, and observations.
    Returns a dict with 'prices', 'trades', 'observations'.
    """
    data = {"prices": None, "trades": None, "observations": None}
    
    for filename, content in files:
        fname = filename.lower()
        if "prices" in fname and fname.endswith(".csv"):
            data["prices"] = content
        elif "trades" in fname and fname.endswith(".csv"):
            data["trades"] = content
        elif "observations" in fname and fname.endswith(".csv"):
            data["observations"] = content
            
    return data

def extract_zip_contents(zip_bytes: bytes) -> List[Tuple[str, str]]:
    """Extracts CSV files from a zip archive."""
    files = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as z:
        for name in z.namelist():
            if name.endswith(".csv"):
                with z.open(name) as f:
                    try:
                        files.append((name, f.read().decode("utf-8")))
                    except UnicodeDecodeError:
                        continue # Skip binary/non-text files
    return files

def run_custom_backtest(
    trader_code: str,
    data_package: Dict[str, str],
    round_num: int = 2,
    day_num: int = 1
) -> Dict[str, Any]:
    """Runs a backtest using provided code and data, returning serialized results."""
    
    prices_csv = data_package.get("prices")
    trades_csv = data_package.get("trades")
    observations_csv = data_package.get("observations")
    
    if not prices_csv:
        raise ValueError("Could not find a valid prices CSV file in the uploaded data.")
    
    # Create a temporary directory for execution
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        
        # 1. Setup Data Directory structure expected by prosperity4bt
        round_dir = tmp_path / f"round{round_num}"
        round_dir.mkdir()
        
        # Sanitize CSVs (remove trailing empty lines which crash the parser)
        def sanitize_csv(content):
            if not content: return None
            lines = [line.strip() for line in content.splitlines() if line.strip()]
            return "\n".join(lines)

        prices_csv = sanitize_csv(prices_csv)
        trades_csv = sanitize_csv(trades_csv)
        observations_csv = sanitize_csv(observations_csv)

        # Save CSVs with names expected by read_day_data
        (round_dir / f"prices_round_{round_num}_day_{day_num}.csv").write_text(prices_csv)
        
        if trades_csv:
            (round_dir / f"trades_round_{round_num}_day_{day_num}.csv").write_text(trades_csv)
        else:
            (round_dir / f"trades_round_{round_num}_day_{day_num}.csv").write_text("timestamp;buyer;seller;symbol;currency;price;quantity")
            
        if observations_csv:
            (round_dir / f"observations_round_{round_num}_day_{day_num}.csv").write_text(observations_csv)
        else:
            (round_dir / f"observations_round_{round_num}_day_{day_num}.csv").write_text("timestamp,bidPrice,askPrice,transportFees,exportTariff,importTariff,sugarPrice,sunlightIndex")

        # 2. Setup Trader script
        trader_file = tmp_path / "trader.py"
        trader_file.write_text(trader_code)
        
        # 3. Import Trader class dynamically
        spec = importlib.util.spec_from_file_location("trader_module", str(trader_file))
        trader_module = importlib.util.module_from_spec(spec)
        
        # Setup path and datamodel for the trader
        old_path = sys.path.copy()
        sys.path.append(tmp_dir)
        
        from prosperity4bt import datamodel
        sys.modules["datamodel"] = datamodel
        
        try:
            spec.loader.exec_module(trader_module)
            
            if not hasattr(trader_module, "Trader"):
                raise ValueError("Uploaded Python file does not contain a 'Trader' class.")
            
            trader_instance = trader_module.Trader()
            
            # 4. Initialize FileSystemReader and run
            file_reader = FileSystemReader(tmp_path)
            
            result = run_backtest(
                trader=trader_instance,
                file_reader=file_reader,
                round_num=round_num,
                day_num=day_num,
                print_output=False,
                trade_matching_mode=TradeMatchingMode.all,
                no_names=True,
                show_progress_bar=False
            )
            
            return serialize_backtest_result(result)
            
        finally:
            # Clean up sys.path and modules to avoid conflicts in subsequent runs
            sys.path = old_path
            if "trader_module" in sys.modules:
                del sys.modules["trader_module"]
