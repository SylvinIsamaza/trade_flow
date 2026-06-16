from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_
from typing import Optional, Dict
from datetime import datetime
import json
import random

from app.core.database import get_db
from app.api.routers.auth import get_current_user
from app.models.user import User
from app.models.account import Account
from app.models.account import Trade
from app.models.supporting import Tag
from app.schemas.trade import TradeResponse
from app.utils.import_parser import (
    parse_trade_file,
    parse_tabular_trade_file,
    convert_to_trade_format,
    convert_mapped_row_to_trade_format,
)
from app.utils.id_generator import generate_trade_id, generate_tag_id

router = APIRouter(prefix="/import", tags=["Trade Import"])


@router.post("/trades", response_model=dict)
async def import_trades(
    account_id: str = Form(...),
    import_type: str = Form("metatrader"),
    column_mapping: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Import trades from MT5 report file (HTML, XML, or Excel).
    """
    # Verify account belongs to user
    result = await db.execute(
        select(Account).where(
            and_(
                Account.id == account_id,
                Account.user_id == current_user.id
            )
        )
    )
    account = result.scalar_one_or_none()
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Read file content
    content = await file.read()
    
    parsed_mapping: Optional[Dict[str, str]] = None
    if column_mapping:
        try:
            parsed_mapping = json.loads(column_mapping)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid column mapping JSON"
            )

    # Detect and parse file
    try:
        if import_type == "other":
            if not parsed_mapping:
                raise ValueError("Column mapping is required for Other imports")
            table_data = parse_tabular_trade_file(content, file.filename)
            positions = [
                convert_mapped_row_to_trade_format(row, parsed_mapping, account_id)
                for row in table_data["rows"]
            ]
        else:
            positions = parse_trade_file(content, file.filename)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    if not positions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No positions found in the file"
        )
    
    # Convert and create trades
    created_trades = []
    errors = []
    
    # Tag type mapping for the 4 tag arrays
    tag_type_mapping = {
        "setups": "SETUP",
        "general_tags": "GENERAL",
        "exit_tags": "EXIT",
        "process_tags": "PROCESS",
    }
    
    # Default colors for tags
    default_colors = ["#5e5ce6", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#ec4899", "#06b6d4", "#84cc16"]
    
    async def get_or_create_tag(db: AsyncSession, account_id: str, tag_name: str, tag_type: str, strategy_id: Optional[str] = None) -> str:
        """Search for tag by name and type, create if not found."""
        if not tag_name:
            return None
            
        # Search for existing tag
        result = await db.execute(
            select(Tag).where(
                and_(
                    Tag.account_id == account_id,
                    Tag.name == tag_name,
                    Tag.type == tag_type
                )
            )
        )
        existing_tag = result.scalar_one_or_none()
        
        if existing_tag:
            return existing_tag.id
        
        # Create new tag
        new_tag = Tag(
            id=generate_tag_id(account_id),
            account_id=account_id,
            name=tag_name,
            type=tag_type,
            strategy_id=strategy_id,
            color=random.choice(default_colors),
        )
        db.add(new_tag)
        await db.flush()  # Get the ID without committing
        
        return new_tag.id
    
    for idx, position in enumerate(positions):
        try:
            trade_data = position if import_type == "other" else convert_to_trade_format(position, account_id)
            
            # Parse executed_at datetime
            executed_at_dt = datetime.fromisoformat(trade_data["executed_at"]) if trade_data.get("executed_at") else datetime.now()
            
            # Parse closed_at datetime if available
            closed_at_dt = None
            if trade_data.get("closed_at"):
                try:
                    closed_at_dt = datetime.fromisoformat(trade_data["closed_at"])
                except (ValueError, TypeError):
                    closed_at_dt = None
            
            # Process tags - get or create tag IDs
            setups_ids = []
            for tag_name in (trade_data.get("setups") or []):
                tag_id = await get_or_create_tag(db, account_id, tag_name, "SETUP")
                if tag_id:
                    setups_ids.append(tag_id)
            
            general_tags_ids = []
            for tag_name in (trade_data.get("general_tags") or []):
                tag_id = await get_or_create_tag(db, account_id, tag_name, "GENERAL")
                if tag_id:
                    general_tags_ids.append(tag_id)
            
            exit_tags_ids = []
            for tag_name in (trade_data.get("exit_tags") or []):
                tag_id = await get_or_create_tag(db, account_id, tag_name, "EXIT")
                if tag_id:
                    exit_tags_ids.append(tag_id)
            
            process_tags_ids = []
            for tag_name in (trade_data.get("process_tags") or []):
                tag_id = await get_or_create_tag(db, account_id, tag_name, "PROCESS")
                if tag_id:
                    process_tags_ids.append(tag_id)
            
            new_trade = Trade(
                id=generate_trade_id(account_id, executed_at_dt),
                account_id=trade_data["account_id"],
                symbol=trade_data["symbol"],
                side=trade_data["side"],
                ticket=trade_data.get("ticket"),
                entry_price=trade_data["entry_price"],
                exit_price=trade_data["exit_price"],
                close_price=trade_data["close_price"],
                quantity=trade_data["quantity"],
                pnl=trade_data["pnl"],
                commission=trade_data["commission"],
                swap=trade_data["swap"],
                duration=trade_data["duration"],
                trade_type=trade_data["trade_type"],
                execution_type=trade_data["execution_type"],
                status=trade_data["status"],
                stop_loss=trade_data["stop_loss"],
                take_profit=trade_data["take_profit"],
                setups=setups_ids,
                general_tags=general_tags_ids,
                exit_tags=exit_tags_ids,
                process_tags=process_tags_ids,
                notes=trade_data["notes"],
                executed_at=executed_at_dt,
                closed_at=closed_at_dt,
                date=trade_data["date"],
                time=trade_data["time"],
                close_time=trade_data["close_time"],
                session=trade_data.get("session"),
                higher_timeframe_bias=trade_data.get("higher_timeframe_bias"),
                trend_structure=trade_data.get("trend_structure"),
                key_levels=trade_data.get("key_levels"),
                entry_model=trade_data.get("entry_model"),
                reason_for_entry=trade_data.get("reason_for_entry"),
                confirmation_used=trade_data.get("confirmation_used"),
                dollar_amount_risked=trade_data.get("dollar_amount_risked"),
                percentage_risked=trade_data.get("percentage_risked"),
                energy_level=trade_data.get("energy_level"),
                emotions=trade_data.get("emotions"),
                confidence_level=trade_data.get("confidence_level"),
                forcing_trades=trade_data.get("forcing_trades"),
                sleep_quality=trade_data.get("sleep_quality"),
                distractions=trade_data.get("distractions"),
                actual_rr_achieved=trade_data.get("actual_rr_achieved"),
                pips_gained_lost=trade_data.get("pips_gained_lost"),
                followed_plan=trade_data.get("followed_plan"),
                entered_too_early=trade_data.get("entered_too_early"),
                moved_sl=trade_data.get("moved_sl"),
                closed_early_from_fear=trade_data.get("closed_early_from_fear"),
                greed_affected_tp=trade_data.get("greed_affected_tp"),
                what_actually_happened=trade_data.get("what_actually_happened"),
                setup_worked_as_expected=trade_data.get("setup_worked_as_expected"),
                abnormal_volatility=trade_data.get("abnormal_volatility"),
                news_event_involved=trade_data.get("news_event_involved"),
                screenshot_annotations=trade_data.get("screenshot_annotations"),
                trade_commentary=trade_data.get("trade_commentary"),
            )
            
            db.add(new_trade)
            created_trades.append(new_trade)
            
        except Exception as e:
            errors.append(f"Row {idx + 1}: {str(e)}")
    
    # Commit all trades
    if created_trades:
        await db.commit()
        # Refresh to get IDs
        for trade in created_trades:
            await db.refresh(trade)
    
    return {
        "success": True,
        "imported_count": len(created_trades),
        "error_count": len(errors),
        "errors": errors[:10] if errors else [],  # Limit to 10 errors
        "trades": [
            {
                "id": t.id,
                "symbol": t.symbol,
                "side": t.side,
                "pnl": float(t.pnl),
                "date": str(t.date)
            }
            for t in created_trades[:5]  # Return first 5 as preview
        ]
    }


@router.post("/trades/preview", response_model=dict)
async def preview_import(
    account_id: str = Form(...),
    import_type: str = Form("metatrader"),
    column_mapping: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Preview trades from MT5 report without importing.
    """
    print("Previewing import - file received:", current_user.id)
    # Verify account belongs to user
    result = await db.execute(
        select(Account).where(
            and_(
                Account.id == account_id,
                Account.user_id == current_user.id
            )
        )
    )
    account = result.scalar_one_or_none()
 
    
    if not account:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Account not found"
        )
    
    # Read file content
    content = await file.read()
    
    parsed_mapping: Optional[Dict[str, str]] = None
    if column_mapping:
        try:
            parsed_mapping = json.loads(column_mapping)
        except json.JSONDecodeError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid column mapping JSON"
            )

    # Detect and parse file
    try:
        if import_type == "other":
            table_data = parse_tabular_trade_file(content, file.filename)
            if not parsed_mapping:
                return {
                    "needs_mapping": True,
                    "columns": table_data["columns"],
                    "sample_rows": table_data["rows"][:5],
                    "total_positions": len(table_data["rows"]),
                    "preview": []
                }
            positions = [
                convert_mapped_row_to_trade_format(row, parsed_mapping, account_id)
                for row in table_data["rows"]
            ]
        else:
            positions = parse_trade_file(content, file.filename)
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    
    # Convert first 10 for preview
    preview_trades = []
    for position in positions[:10]:
        trade_data = position if import_type == "other" else convert_to_trade_format(position, account_id)
        preview_trades.append({
            "symbol": trade_data["symbol"],
            "side": trade_data["side"],
            "ticket": trade_data.get("ticket"),
            "entry_price": trade_data["entry_price"],
            "exit_price": trade_data["exit_price"],
            "pnl": trade_data["pnl"],
            "date": trade_data["date"],
            "status": trade_data["status"],
            'volume': trade_data["quantity"],
            'commission': trade_data["commission"],
            'swap': trade_data["swap"],
            'duration': trade_data["duration"],
            'trade_type': trade_data["trade_type"],
            'execution_type': trade_data["execution_type"],
            'stop_loss': trade_data["stop_loss"],
            'take_profit': trade_data["take_profit"],
            'setups': trade_data["setups"],
            'general_tags': trade_data["general_tags"],
            'exit_tags': trade_data["exit_tags"],
            'process_tags': trade_data["process_tags"],
            'notes': trade_data["notes"],
        })
    
    return {
        "needs_mapping": False,
        "total_positions": len(positions),
        "preview": preview_trades
    }
