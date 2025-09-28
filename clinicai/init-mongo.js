// MongoDB initialization script for ClinicAI
db = db.getSiblingDB('clinicai');

// Create collections
db.createCollection('messages');
db.createCollection('triages');
db.createCollection('users');

// Create indexes for performance
db.messages.createIndex({ "phone_hash": 1 });
db.messages.createIndex({ "timestamp": -1 });
db.messages.createIndex({ "message_id": 1 }, { unique: true });
db.messages.createIndex({ "direction": 1, "timestamp": -1 });

db.triages.createIndex({ "phone_hash": 1 }, { unique: true });
db.triages.createIndex({ "status": 1 });
db.triages.createIndex({ "emergency_flag": 1 });
db.triages.createIndex({ "created_at": -1 });
db.triages.createIndex({ "updated_at": -1 });

db.users.createIndex({ "phone_hash": 1 }, { unique: true });
db.users.createIndex({ "phone": 1 }, { unique: true });
db.users.createIndex({ "last_seen_at": -1 });

print('ClinicAI database initialized successfully');

