from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from typing import List, Optional
from datetime import date, datetime

from app.core.database import get_db
from app.api.routers.auth import get_current_user
from app.models.user import User
from app.models.account import Account
from app.models.supporting import Folder, Note
from pydantic import BaseModel

from app.utils.id_generator import generate_folder_id,generate_note_id

router = APIRouter(prefix="/notes", tags=["Notes"])


# ===== Folder Schemas =====
class FolderCreate(BaseModel):
    account_id: str
    name: str


class FolderUpdate(BaseModel):
    name: str


class FolderResponse(BaseModel):
    id: str
    account_id: str
    name: str
    created_at: datetime
    
    model_config = {"from_attributes": True}


# ===== Note Schemas =====
class NoteCreate(BaseModel):
    account_id: str
    folder_id: Optional[str] = None
    title: str
    content: Optional[str] = None
    tags: Optional[List[str]] = []
    date: date


class NoteUpdate(BaseModel):
    folder_id: Optional[str] = None
    title: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[List[str]] = None


class NoteResponse(BaseModel):
    id: str
    account_id: str
    folder_id: Optional[str]
    title: str
    content: Optional[str]
    tags: List[str]
    date: date
    created_at: datetime
    updated_at: Optional[datetime]
    
    model_config = {"from_attributes": True}


# ===== Folder Endpoints =====
@router.get("/folders", response_model=List[FolderResponse])
async def get_folders(
    account_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get folders."""
    query = select(Folder).join(Account, Folder.account_id == Account.id)
    query = query.where(Account.user_id == current_user.id)
    
    if account_id:
        query = query.where(Folder.account_id == account_id)
    
    result = await db.execute(query.order_by(Folder.name))
    return result.scalars().all()


@router.post("/folders", response_model=FolderResponse, status_code=status.HTTP_201_CREATED)
async def create_folder(
    folder_data: FolderCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new folder."""
    # Verify account belongs to user
    result = await db.execute(
        select(Account).where(
            and_(
                Account.id == folder_data.account_id,
                Account.user_id == current_user.id
            )
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Account not found")
    
    new_folder = Folder(
        id=generate_folder_id(folder_data.account_id),
        account_id=folder_data.account_id,
        name=folder_data.name
    )
    db.add(new_folder)
    await db.commit()
    await db.refresh(new_folder)
    return new_folder


@router.put("/folders/{folder_id}", response_model=FolderResponse)
async def update_folder(
    folder_id: str,
    folder_data: FolderUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update folder."""
    result = await db.execute(
        select(Folder)
        .join(Account, Folder.account_id == Account.id)
        .where(and_(Folder.id == folder_id, Account.user_id == current_user.id))
    )
    folder = result.scalar_one_or_none()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    folder.name = folder_data.name
    await db.commit()
    await db.refresh(folder)
    return folder


@router.delete("/folders/{folder_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_folder(
    folder_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete folder and all its notes."""
    from sqlalchemy import delete as sql_delete
    
    result = await db.execute(
        select(Folder)
        .join(Account, Folder.account_id == Account.id)
        .where(and_(Folder.id == folder_id, Account.user_id == current_user.id))
    )
    folder = result.scalar_one_or_none()
    if not folder:
        raise HTTPException(status_code=404, detail="Folder not found")
    
    # Delete all notes in the folder first using DELETE statement
    await db.execute(
        sql_delete(Note).where(Note.folder_id == folder_id)
    )
    
    # Now delete the folder
    await db.execute(
        sql_delete(Folder).where(Folder.id == folder_id)
    )
    
    await db.commit()


# ===== Note Endpoints =====
@router.get("/", response_model=dict)
async def get_notes(
    account_id: Optional[str] = None,
    folder_id: Optional[str] = None,
    tag: Optional[str] = None,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    limit: int = Query(default=50, le=500),
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get notes with filters and pagination."""
    from sqlalchemy import func
    
    # Build base query
    query = select(Note).join(Account, Note.account_id == Account.id)
    query = query.where(Account.user_id == current_user.id)
    
    if account_id:
        query = query.where(Note.account_id == account_id)
    if folder_id:
        query = query.where(Note.folder_id == folder_id)
    if tag:
        query = query.where(Note.tags.contains([tag]))
    if start_date:
        query = query.where(Note.date >= start_date)
    if end_date:
        query = query.where(Note.date <= end_date)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Paginate
    query = query.order_by(Note.date.desc()).offset(offset).limit(limit)
    
    result = await db.execute(query)
    notes = result.scalars().all()
    
    # Convert to Pydantic models
    note_responses = [NoteResponse.model_validate(note) for note in notes]
    
    return {
        "items": [n.model_dump() for n in note_responses],
        "total": total,
        "page": (offset // limit) + 1,
        "limit": limit,
        "total_pages": (total + limit - 1) // limit if total > 0 else 0
    }


@router.post("/", response_model=NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(
    note_data: NoteCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Create a new note."""
    # Verify account belongs to user
    result = await db.execute(
        select(Account).where(
            and_(
                Account.id == note_data.account_id,
                Account.user_id == current_user.id
            )
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Account not found")
    
    new_note = Note(
        id= generate_note_id(note_data.account_id),
        account_id=note_data.account_id,
        folder_id=note_data.folder_id,
        title=note_data.title,
        content=note_data.content,
        tags=note_data.tags or [],
        date=note_data.date,
    )
    db.add(new_note)
    await db.commit()
    await db.refresh(new_note)
    return new_note


@router.get("/{note_id}", response_model=NoteResponse)
async def get_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Get note by ID."""
    result = await db.execute(
        select(Note)
        .join(Account, Note.account_id == Account.id)
        .where(and_(Note.id == note_id, Account.user_id == current_user.id))
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    return note


@router.put("/{note_id}", response_model=NoteResponse)
async def update_note(
    note_id: str,
    note_data: NoteUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Update note."""
    result = await db.execute(
        select(Note)
        .join(Account, Note.account_id == Account.id)
        .where(and_(Note.id == note_id, Account.user_id == current_user.id))
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    if note_data.folder_id is not None:
        note.folder_id = note_data.folder_id
    if note_data.title is not None:
        note.title = note_data.title
    if note_data.content is not None:
        note.content = note_data.content
    if note_data.tags is not None:
        note.tags = note_data.tags
    
    await db.commit()
    await db.refresh(note)
    return note


@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(
    note_id: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Delete note."""
    result = await db.execute(
        select(Note)
        .join(Account, Note.account_id == Account.id)
        .where(and_(Note.id == note_id, Account.user_id == current_user.id))
    )
    note = result.scalar_one_or_none()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found")
    
    await db.delete(note)
    await db.commit()