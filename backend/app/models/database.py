"""
Database module for Supabase integration.

This module provides the Supabase client and database operations
for the Fake Productivity Detector backend.
"""

import json
import logging
import os
import sqlite3
from typing import Any, Dict, List, Optional
from datetime import date, datetime
import uuid
from collections import defaultdict

from supabase import create_client, Client

from ..config import settings, TableNames

# Configure logging
logger = logging.getLogger(__name__)

# In-memory storage for when Supabase table isn't available
# This allows history to work during the session for demo purposes
_in_memory_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

# In-memory storage for agent authenticity records when the Supabase
# agent_authenticity_records table isn't available. Module-level so it
# persists across requests (each request creates a new AgentAuthenticityDB).
_agent_in_memory_store: Dict[str, List[Dict[str, Any]]] = defaultdict(list)

# Persistent SQLite fallback path used when the Supabase table is unavailable.
# This ensures agent records survive backend restarts (unlike in-memory only).
_AGENT_FALLBACK_SQLITE_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "..", "data", "agent_fallback.db"
)


class SupabaseClient:
    """
    Supabase database client wrapper.
    
    Provides methods for CRUD operations on the productivity_analysis table
    and other database operations.
    """
    
    _instance: Optional[Client] = None
    
    @classmethod
    def get_client(cls) -> Optional[Client]:
        """
        Get or create Supabase client instance (singleton pattern).
        
        Returns:
            Client: Supabase client instance, or None if not configured
        """
        if cls._instance is None:
            if not settings.supabase_url or not settings.supabase_key:
                logger.warning(
                    "Supabase URL/Key not configured. Using in-memory storage. "
                    "Set SUPABASE_URL and SUPABASE_KEY environment variables."
                )
                return None
            try:
                cls._instance = create_client(
                    settings.supabase_url,
                    settings.supabase_key
                )
                logger.info("Supabase client initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Supabase client: {e}")
                return None
        return cls._instance
    
    @classmethod
    def reset_client(cls) -> None:
        """Reset the client instance (useful for testing)."""
        cls._instance = None


class ProductivityAnalysisDB:
    """
    Database operations for productivity analysis records.
    
    Handles all CRUD operations for the productivity_analysis table.
    """
    
    def __init__(self):
        """Initialize with Supabase client."""
        self.client = SupabaseClient.get_client()
        self.table = TableNames.PRODUCTIVITY_ANALYSIS
        self._use_memory = self.client is None
    
    async def create_analysis(
        self,
        user_id: str,
        user_name: str,
        task_hours: float,
        idle_hours: float,
        social_media_usage: float,
        break_frequency: int,
        tasks_completed: int,
        productivity_score: float,
        category_rule_based: str,
        category_ml: Optional[str] = None,
        suggestions: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """
        Create a new productivity analysis record.
        
        Args:
            user_id: User identifier
            user_name: User display name
            task_hours: Hours spent on tasks
            idle_hours: Hours spent idle
            social_media_usage: Hours on social media
            break_frequency: Number of breaks taken
            tasks_completed: Number of tasks completed
            productivity_score: Calculated productivity score
            category_rule_based: Rule-based category classification
            category_ml: ML model category classification
            suggestions: List of improvement suggestions
            
        Returns:
            Dict containing the created record
        """
        try:
            record = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "user_name": user_name,
                "task_hours": task_hours,
                "idle_hours": idle_hours,
                "social_media_usage": social_media_usage,
                "break_frequency": break_frequency,
                "tasks_completed": tasks_completed,
                "productivity_score": productivity_score,
                "category_rule_based": category_rule_based,
                "category_ml": category_ml,
                "suggestions": suggestions or [],
                "created_at": datetime.utcnow().isoformat()
            }
            
            if self._use_memory:
                return await self._fallback_create(record)
            
            response = self.client.table(self.table).insert(record).execute()
            logger.info(f"Created analysis record for user {user_id}")
            return response.data[0] if response.data else record
            
        except Exception as e:
            logger.error(f"Error creating analysis record: {e}")
            # Fallback to KV store if main table doesn't exist
            return await self._fallback_create(record)
    
    async def _fallback_create(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """
        Fallback when productivity_analysis table is not accessible.
        
        Stores the record in-memory so history works during the session.
        
        Args:
            record: Record to store
            
        Returns:
            Dict containing the record
        """
        user_id = record.get("user_id", "unknown")
        _in_memory_history[user_id].insert(0, record)  # Insert at beginning (newest first)
        logger.info(f"Stored analysis in-memory for user {user_id}. Total records: {len(_in_memory_history[user_id])}")
        return record
    
    async def get_user_history(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get productivity history for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of records to return
            offset: Number of records to skip
            
        Returns:
            List of analysis records
        """
        try:
            if self._use_memory:
                return await self._fallback_get_history(user_id)
            
            response = self.client.table(self.table)\
                .select("*")\
                .eq("user_id", user_id)\
                .order("created_at", desc=True)\
                .limit(limit)\
                .offset(offset)\
                .execute()
            
            return response.data or []
            
        except Exception as e:
            logger.warning(f"Main table query failed, trying KV store: {e}")
            return await self._fallback_get_history(user_id)
    
    async def _fallback_get_history(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Fallback when database is not accessible.
        
        Returns history from in-memory storage.
        
        Args:
            user_id: User identifier
            
        Returns:
            List of analysis records from in-memory storage
        """
        history = _in_memory_history.get(user_id, [])
        logger.info(f"Retrieved {len(history)} records from in-memory storage for user {user_id}")
        return history
    
    async def delete_user_history(self, user_id: str) -> int:
        """
        Delete all productivity history for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of deleted records
        """
        try:
            if self._use_memory:
                return await self._fallback_delete_history(user_id)
            
            # Try main table first
            response = self.client.table(self.table)\
                .delete()\
                .eq("user_id", user_id)\
                .execute()
            
            deleted_count = len(response.data) if response.data else 0
            logger.info(f"Deleted {deleted_count} records for user {user_id}")
            return deleted_count
            
        except Exception as e:
            logger.warning(f"Main table delete failed, trying KV store: {e}")
            return await self._fallback_delete_history(user_id)
    
    async def _fallback_delete_history(self, user_id: str) -> int:
        """
        Fallback when database is not accessible.
        
        Deletes history from in-memory storage.
        
        Args:
            user_id: User identifier
            
        Returns:
            Number of records deleted from in-memory storage
        """
        count = len(_in_memory_history.get(user_id, []))
        _in_memory_history[user_id] = []
        logger.info(f"Deleted {count} records from in-memory storage for user {user_id}")
        return count
    
    async def get_analytics_summary(self, user_id: str) -> Dict[str, Any]:
        """
        Get analytics summary for a user.
        
        Args:
            user_id: User identifier
            
        Returns:
            Dict containing analytics summary
        """
        history = await self.get_user_history(user_id, limit=1000)
        
        if not history:
            return {
                "total_analyses": 0,
                "average_score": 0,
                "highest_score": 0,
                "lowest_score": 0,
                "category_distribution": {
                    "Highly Productive": 0,
                    "Moderately Productive": 0,
                    "Fake Productivity": 0
                },
                "trend": 0,
                "recent_analyses": [],
                "avg_task_hours": 0,
                "avg_tasks_completed": 0,
                "avg_idle_hours": 0,
                "avg_social_media_hours": 0,
                "avg_break_frequency": 0
            }

        scores = [h.get("productivity_score", h.get("score", 0)) for h in history]
        categories = [h.get("category_rule_based", h.get("category", "Unknown")) for h in history]
        task_hours = [h.get("task_hours", 0) for h in history]
        tasks_completed = [h.get("tasks_completed", 0) for h in history]
        idle_hours = [h.get("idle_hours", 0) for h in history]
        social_media_hours = [h.get("social_media_usage", h.get("social_media_hours", 0)) for h in history]
        break_frequency = [h.get("break_frequency", 0) for h in history]

        # Calculate trend (comparing recent vs older)
        if len(scores) >= 2:
            mid = len(scores) // 2
            recent_avg = sum(scores[:mid]) / mid if mid > 0 else 0
            older_avg = sum(scores[mid:]) / (len(scores) - mid) if (len(scores) - mid) > 0 else 0
            trend = recent_avg - older_avg
        else:
            trend = 0

        def safe_avg(lst):
            return round(sum(lst) / len(lst), 2) if lst and any(x is not None for x in lst) else 0

        return {
            "total_analyses": len(history),
            "average_score": round(sum(scores) / len(scores), 2) if scores else 0,
            "highest_score": round(max(scores), 2) if scores else 0,
            "lowest_score": round(min(scores), 2) if scores else 0,
            "category_distribution": {
                "Highly Productive": categories.count("Highly Productive"),
                "Moderately Productive": categories.count("Moderately Productive"),
                "Fake Productivity": categories.count("Fake Productivity")
            },
            "trend": round(trend, 2),
            "recent_analyses": history[:10],
            "avg_task_hours": safe_avg(task_hours),
            "avg_tasks_completed": safe_avg(tasks_completed),
            "avg_idle_hours": safe_avg(idle_hours),
            "avg_social_media_hours": safe_avg(social_media_hours),
            "avg_break_frequency": safe_avg(break_frequency)
        }


# ==================== Agent Authenticity DB ====================

class _AgentSQLiteFallback:
    """
    Minimal SQLite-backed store used when the Supabase
    agent_authenticity_records table is unavailable.

    Provides persistent storage so history survives backend restarts
    during development / when the migration hasn't been applied yet.
    """

    def __init__(self, db_path: str = _AGENT_FALLBACK_SQLITE_PATH) -> None:
        self.db_path = db_path
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._init_db()

    def _init_db(self) -> None:
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS agent_authenticity (
                        id TEXT PRIMARY KEY,
                        user_id TEXT NOT NULL,
                        date TEXT NOT NULL,
                        authenticity_score REAL NOT NULL,
                        avg_typing_speed REAL,
                        avg_mouse_velocity REAL,
                        top_window_categories TEXT DEFAULT '[]',
                        created_at TEXT,
                        UNIQUE(user_id, date)
                    )
                    """
                )
                conn.commit()
        except Exception as e:
            logger.warning(f"Could not init SQLite fallback for agent records: {e}")

    def upsert(self, record: Dict[str, Any]) -> Dict[str, Any]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                # Parse JSON-serialized fields back into Python objects for the caller
                parsed = dict(record)
                if isinstance(parsed.get("top_window_categories"), str):
                    try:
                        parsed["top_window_categories"] = json.loads(parsed["top_window_categories"])
                    except (json.JSONDecodeError, TypeError):
                        parsed["top_window_categories"] = []

                conn.execute(
                    """
                    INSERT INTO agent_authenticity
                        (id, user_id, date, authenticity_score, avg_typing_speed,
                         avg_mouse_velocity, top_window_categories, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, date) DO UPDATE SET
                        authenticity_score = excluded.authenticity_score,
                        avg_typing_speed = excluded.avg_typing_speed,
                        avg_mouse_velocity = excluded.avg_mouse_velocity,
                        top_window_categories = excluded.top_window_categories,
                        created_at = excluded.created_at
                    """,
                    (
                        parsed.get("id", str(uuid.uuid4())),
                        parsed.get("user_id", ""),
                        parsed.get("date", ""),
                        parsed.get("authenticity_score", 0),
                        parsed.get("avg_typing_speed"),
                        parsed.get("avg_mouse_velocity"),
                        json.dumps(parsed.get("top_window_categories") or []),
                        parsed.get("created_at", datetime.utcnow().isoformat()),
                    ),
                )
                conn.commit()
            return parsed
        except Exception as e:
            logger.error(f"SQLite fallback upsert failed: {e}")
            return record

    def get_history(self, user_id: str, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(
                    """
                    SELECT * FROM agent_authenticity
                    WHERE user_id = ?
                    ORDER BY date DESC
                    LIMIT ? OFFSET ?
                    """,
                    (user_id, limit, offset),
                ).fetchall()

                cols = [d[0] for d in conn.execute("SELECT * FROM agent_authenticity LIMIT 0").description]
                records = [dict(zip(cols, row)) for row in rows]

                for r in records:
                    if isinstance(r.get("top_window_categories"), str):
                        try:
                            r["top_window_categories"] = json.loads(r["top_window_categories"])
                        except (json.JSONDecodeError, TypeError):
                            r["top_window_categories"] = []
                return records
        except Exception as e:
            logger.error(f"SQLite fallback history fetch failed: {e}")
            return []

    def get_latest(self, user_id: str) -> Optional[Dict[str, Any]]:
        records = self.get_history(user_id, limit=1)
        return records[0] if records else None


class AgentAuthenticityDB:
    """
    Database operations for agent authenticity records.

    Handles CRUD operations for the agent_authenticity_records table.
    """

    def __init__(self):
        """Initialize with Supabase client."""
        self.client = SupabaseClient.get_client()
        self.table = "agent_authenticity_records"
        self._use_memory = self.client is None
        # Shared in-memory fallback (module-level so it survives across requests)
        self._memory_store: Dict[str, List[Dict[str, Any]]] = _agent_in_memory_store
        # Persistent SQLite fallback (survives restarts even when Supabase table is missing)
        self._sqlite_fallback = _AgentSQLiteFallback()

    async def upsert_authenticity(
        self,
        user_id: str,
        event_date: date,
        authenticity_score: float,
        avg_typing_speed: Optional[float] = None,
        avg_mouse_velocity: Optional[float] = None,
        top_window_categories: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        Upsert an agent authenticity record for a user + date.

        If a record for the same (user_id, date) already exists, updates it.

        Args:
            user_id: User identifier
            event_date: Date of the recorded data
            authenticity_score: Calculated score (0-100)
            avg_typing_speed: Mean inter-key interval (ms)
            avg_mouse_velocity: Mean mouse velocity (px/s)
            top_window_categories: List of {category, seconds} dicts

        Returns:
            Dict of the stored record
        """
        record = {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "date": event_date.isoformat() if hasattr(event_date, 'isoformat') else str(event_date),
            "authenticity_score": authenticity_score,
            "avg_typing_speed": avg_typing_speed,
            "avg_mouse_velocity": avg_mouse_velocity,
            "top_window_categories": json.dumps(top_window_categories or []),
            "created_at": datetime.utcnow().isoformat(),
        }

        try:
            if self._use_memory:
                # Also persist to SQLite so records survive backend restarts
                self._sqlite_fallback.upsert(record)
                return self._memory_upsert(record)

            # Try to find existing record
            existing = self.client.table(self.table)\
                .select("id")\
                .eq("user_id", user_id)\
                .eq("date", record["date"])\
                .execute()

            if existing.data and len(existing.data) > 0:
                # Update existing
                existing_id = existing.data[0]["id"]
                response = self.client.table(self.table)\
                    .update(record)\
                    .eq("id", existing_id)\
                    .execute()
            else:
                # Insert new
                response = self.client.table(self.table).insert(record).execute()

            return response.data[0] if response.data else record

        except Exception as e:
            logger.warning(f"Agent DB upsert failed, persisting to SQLite fallback: {e}")
            # Store in both SQLite (persistent) and memory (fast reads)
            self._sqlite_fallback.upsert(record)
            return self._memory_upsert(record)

    def _memory_upsert(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback upsert using in-memory storage."""
        user_id = record.get("user_id", "unknown")
        event_date = record.get("date", "")

        # Parse any JSON-serialized fields back into Python objects for frontend use
        if isinstance(record.get("top_window_categories"), str):
            try:
                record["top_window_categories"] = json.loads(record["top_window_categories"])
            except (json.JSONDecodeError, TypeError):
                record["top_window_categories"] = []

        # Find and replace existing, or append
        existing_records = self._memory_store.get(user_id, [])
        for i, r in enumerate(existing_records):
            if r.get("date") == event_date:
                existing_records[i] = record
                return record

        existing_records.insert(0, record)
        self._memory_store[user_id] = existing_records
        return record

    async def get_user_authenticity_history(
        self,
        user_id: str,
        limit: int = 100,
        offset: int = 0,
    ) -> List[Dict[str, Any]]:
        """
        Get authenticity history for a user.

        Args:
            user_id: User identifier
            limit: Max records
            offset: Pagination offset

        Returns:
            List of authenticity records sorted by date DESC
        """
        try:
            if self._use_memory:
                # Read from SQLite fallback first (persistent across restarts),
                # then merge with any in-memory records not yet persisted.
                sqlite_records = self._sqlite_fallback.get_history(user_id, limit=limit, offset=offset)
                memory_records = self._memory_store.get(user_id, [])
                if sqlite_records:
                    # Merge: SQLite is authoritative; add any memory-only entries
                    by_date = {r.get("date"): r for r in sqlite_records}
                    for r in memory_records:
                        by_date.setdefault(r.get("date"), r)
                    merged = sorted(by_date.values(), key=lambda x: x.get("date", ""), reverse=True)
                    return merged[offset:offset + limit]
                return memory_records[offset:offset + limit]

            response = self.client.table(self.table)\
                .select("*")\
                .eq("user_id", user_id)\
                .order("date", desc=True)\
                .limit(limit)\
                .offset(offset)\
                .execute()

            records = response.data or []

            # If Supabase returned no records (RLS may be blocking anon keys,
            # or this is a fresh deployment), fall back to the persistent
            # SQLite store so dashboard history still works.
            if not records:
                sqlite_records = self._sqlite_fallback.get_history(user_id, limit=limit, offset=offset)
                if sqlite_records:
                    logger.info(f"Supabase returned no records; using {len(sqlite_records)} from SQLite fallback")
                    return sqlite_records

            return records

        except Exception as e:
            logger.warning(f"Agent history fetch failed, using SQLite fallback: {e}")
            records = self._sqlite_fallback.get_history(user_id, limit=limit, offset=offset)
            if records:
                return records

            records = self._memory_store.get(user_id, [])[offset:offset + limit]
            # Parse JSON-serialized fields back into Python objects for the frontend
            for r in records:
                if isinstance(r.get("top_window_categories"), str):
                    try:
                        r["top_window_categories"] = json.loads(r["top_window_categories"])
                    except (json.JSONDecodeError, TypeError):
                        r["top_window_categories"] = []
            return records

    async def get_latest_authenticity(self, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get the most recent authenticity record for a user.

        Args:
            user_id: User identifier

        Returns:
            Latest record or None
        """
        try:
            if self._use_memory:
                return self._sqlite_fallback.get_latest(user_id)
            records = await self.get_user_authenticity_history(user_id, limit=1)
            return records[0] if records else None
        except Exception:
            return None


def get_db() -> ProductivityAnalysisDB:
    """
    Dependency injection for database instance.

    Returns:
        ProductivityAnalysisDB: Database instance
    """
    return ProductivityAnalysisDB()


def get_agent_db() -> AgentAuthenticityDB:
    """
    Dependency injection for agent database instance.

    Returns:
        AgentAuthenticityDB: Agent database instance
    """
    return AgentAuthenticityDB()