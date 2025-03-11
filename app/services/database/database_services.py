# app/services/database_services.py
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session
from app.models.database_models.user import User
from app.models.database_models.counsellor_message_history import CounsellorMessageHistory
from app.models.database_models.user_prompt import UserPrompt
from app.models.llm_models import ChatRequest
from app.services.llm.llm_services import chat_logic
from sentence_transformers import SentenceTransformer
from sqlalchemy import desc, asc, exists, text, Table, MetaData
import re
