"""Database connection and operations for MongoDB."""

import logging
from datetime import datetime
from typing import Optional

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo.errors import DuplicateKeyError

from .config import settings
from .schemas import MessageDocument, TriageDocument, TriageSlots, UserDocument

logger = logging.getLogger(__name__)


class Database:
    """MongoDB database wrapper."""

    def __init__(self) -> None:
        """Initialize database connection."""
        self.client: Optional[AsyncIOMotorClient] = None
        self.db: Optional[AsyncIOMotorDatabase] = None

    async def connect(self) -> None:
        """Connect to MongoDB."""
        try:
            self.client = AsyncIOMotorClient(settings.mongodb_uri)
            self.db = self.client[settings.mongodb_db]
            
            # Test connection
            await self.client.admin.command("ping")
            logger.info("Connected to MongoDB successfully")
            
            # Create indexes
            await self._create_indexes()
            
        except Exception as e:
            logger.error(f"Failed to connect to MongoDB: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from MongoDB."""
        if self.client:
            self.client.close()
            logger.info("Disconnected from MongoDB")

    async def _create_indexes(self) -> None:
        """Create database indexes for performance."""
        if not self.db:
            return

        # Messages collection indexes
        await self.db.messages.create_index("phone_hash")
        await self.db.messages.create_index("timestamp")
        await self.db.messages.create_index("message_id", unique=True)

        # Triages collection indexes
        await self.db.triages.create_index("phone_hash", unique=True)
        await self.db.triages.create_index("status")
        await self.db.triages.create_index("created_at")

        # Users collection indexes
        await self.db.users.create_index("phone_hash", unique=True)
        await self.db.users.create_index("phone", unique=True)

        logger.info("Database indexes created successfully")

    # Message operations
    async def save_message(self, message: MessageDocument) -> str:
        """Save a message to the database."""
        if not self.db:
            raise RuntimeError("Database not connected")

        try:
            result = await self.db.messages.insert_one(message.model_dump())
            logger.info(f"Message saved: {message.message_id}")
            return str(result.inserted_id)
        except DuplicateKeyError:
            logger.warning(f"Duplicate message ID: {message.message_id}")
            return ""
        except Exception as e:
            logger.error(f"Failed to save message: {e}")
            raise

    async def get_messages_by_phone(
        self, phone_hash: str, limit: int = 50
    ) -> list[MessageDocument]:
        """Get messages for a phone number."""
        if not self.db:
            raise RuntimeError("Database not connected")

        try:
            cursor = (
                self.db.messages.find({"phone_hash": phone_hash})
                .sort("timestamp", -1)
                .limit(limit)
            )
            messages = []
            async for doc in cursor:
                doc["_id"] = str(doc["_id"])
                messages.append(MessageDocument(**doc))
            return messages
        except Exception as e:
            logger.error(f"Failed to get messages: {e}")
            raise

    # Triage operations
    async def get_triage(self, phone_hash: str) -> Optional[TriageDocument]:
        """Get current triage for a phone number."""
        if not self.db:
            raise RuntimeError("Database not connected")

        try:
            doc = await self.db.triages.find_one({"phone_hash": phone_hash})
            if doc:
                doc["_id"] = str(doc["_id"])
                return TriageDocument(**doc)
            return None
        except Exception as e:
            logger.error(f"Failed to get triage: {e}")
            raise

    async def create_triage(self, phone_hash: str) -> TriageDocument:
        """Create a new triage for a phone number."""
        if not self.db:
            raise RuntimeError("Database not connected")

        now = datetime.utcnow()
        triage = TriageDocument(
            phone_hash=phone_hash,
            status="open",
            slots=TriageSlots(),
            emergency_flag=False,
            created_at=now,
            updated_at=now,
            last_message_at=now,
        )

        try:
            await self.db.triages.insert_one(triage.model_dump())
            logger.info(f"New triage created for phone_hash: {phone_hash}")
            return triage
        except DuplicateKeyError:
            # Triage already exists, fetch it
            existing = await self.get_triage(phone_hash)
            if existing:
                return existing
            raise
        except Exception as e:
            logger.error(f"Failed to create triage: {e}")
            raise

    async def update_triage(
        self,
        phone_hash: str,
        slots: Optional[TriageSlots] = None,
        status: Optional[str] = None,
        emergency_flag: Optional[bool] = None,
    ) -> Optional[TriageDocument]:
        """Update an existing triage."""
        if not self.db:
            raise RuntimeError("Database not connected")

        update_data = {"updated_at": datetime.utcnow(), "last_message_at": datetime.utcnow()}
        
        if slots:
            update_data["slots"] = slots.model_dump()
        if status:
            update_data["status"] = status
            if status == "closed":
                update_data["closed_at"] = datetime.utcnow()
        if emergency_flag is not None:
            update_data["emergency_flag"] = emergency_flag

        try:
            result = await self.db.triages.find_one_and_update(
                {"phone_hash": phone_hash},
                {"$set": update_data},
                return_document=True,
            )
            if result:
                result["_id"] = str(result["_id"])
                logger.info(f"Triage updated for phone_hash: {phone_hash}")
                return TriageDocument(**result)
            return None
        except Exception as e:
            logger.error(f"Failed to update triage: {e}")
            raise

    # User operations
    async def create_or_update_user(self, phone: str, phone_hash: str) -> UserDocument:
        """Create or update user information."""
        if not self.db:
            raise RuntimeError("Database not connected")

        now = datetime.utcnow()
        user_data = {
            "phone": phone,
            "phone_hash": phone_hash,
            "last_seen_at": now,
        }

        try:
            result = await self.db.users.find_one_and_update(
                {"phone_hash": phone_hash},
                {
                    "$set": user_data,
                    "$setOnInsert": {"created_at": now},
                },
                upsert=True,
                return_document=True,
            )
            result["_id"] = str(result["_id"])
            return UserDocument(**result)
        except Exception as e:
            logger.error(f"Failed to create/update user: {e}")
            raise


# Global database instance
db = Database()

