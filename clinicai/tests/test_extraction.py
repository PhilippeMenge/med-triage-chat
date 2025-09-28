"""Tests for LLM slot extraction functionality."""

import pytest
from unittest.mock import AsyncMock, patch

from clinicai.app.schemas import LLMExtraction, TriageSlots
from clinicai.app.llm import GeminiLLMClient


class TestSlotExtraction:
    """Test LLM slot extraction functionality."""

    @pytest.fixture
    def llm_client(self):
        """Create LLM client for testing."""
        with patch('clinicai.app.llm.genai.configure'):
            with patch('clinicai.app.llm.genai.GenerativeModel'):
                client = GeminiLLMClient()
                return client

    def test_llm_extraction_schema_validation(self):
        """Test LLM extraction schema validation."""
        # Valid extraction
        valid_data = {
            "chief_complaint": "dor de cabeça",
            "symptoms": "dor latejante na testa",
            "duration": "3 dias",
            "frequency": "constante",
            "intensity": "7",
            "history": "hipertensão",
            "measures_taken": "tomei paracetamol",
            "found_emergency": False
        }
        
        extraction = LLMExtraction(**valid_data)
        assert extraction.chief_complaint == "dor de cabeça"
        assert extraction.intensity == "7"
        assert not extraction.found_emergency

    def test_llm_extraction_with_nulls(self):
        """Test extraction with missing fields."""
        partial_data = {
            "chief_complaint": "febre",
            "symptoms": None,
            "duration": "2 dias",
            "found_emergency": False
        }
        
        extraction = LLMExtraction(**partial_data)
        assert extraction.chief_complaint == "febre"
        assert extraction.symptoms is None
        assert extraction.duration == "2 dias"

    def test_triage_slots_completion_check(self):
        """Test triage slots completion detection."""
        # Complete slots
        complete_slots = TriageSlots(
            chief_complaint="dor",
            symptoms="dor forte",
            duration="1 dia",
            frequency="constante",
            intensity="8",
            history="nenhum",
            measures_taken="repouso"
        )
        
        assert complete_slots.is_complete()
        assert len(complete_slots.get_missing_slots()) == 0

    def test_triage_slots_incomplete(self):
        """Test incomplete triage slots."""
        incomplete_slots = TriageSlots(
            chief_complaint="dor",
            symptoms="dor forte",
            duration=None,
            frequency=None,
            intensity="8",
            history=None,
            measures_taken=None
        )
        
        assert not incomplete_slots.is_complete()
        missing = incomplete_slots.get_missing_slots()
        assert "duration" in missing
        assert "frequency" in missing
        assert "history" in missing
        assert "measures_taken" in missing

    @pytest.mark.asyncio
    async def test_mock_slot_extraction(self, llm_client):
        """Test slot extraction with mocked LLM response."""
        mock_response = AsyncMock()
        mock_response.text = '''
        {
            "chief_complaint": "dor de cabeça",
            "symptoms": "dor latejante",
            "duration": "2 dias",
            "frequency": "pela manhã",
            "intensity": "6",
            "history": null,
            "measures_taken": "paracetamol",
            "found_emergency": false
        }
        '''
        
        with patch.object(llm_client.model, 'generate_content', return_value=mock_response):
            extraction = await llm_client.extract_slots("tenho dor de cabeça há 2 dias")
            
            assert extraction.chief_complaint == "dor de cabeça"
            assert extraction.symptoms == "dor latejante"
            assert extraction.duration == "2 dias"
            assert extraction.intensity == "6"
            assert not extraction.found_emergency

    @pytest.mark.asyncio
    async def test_emergency_detection_in_extraction(self, llm_client):
        """Test emergency detection during slot extraction."""
        mock_response = AsyncMock()
        mock_response.text = '''
        {
            "chief_complaint": "dor no peito",
            "symptoms": "dor forte no peito",
            "duration": "agora",
            "frequency": null,
            "intensity": "10",
            "history": null,
            "measures_taken": null,
            "found_emergency": true
        }
        '''
        
        with patch.object(llm_client.model, 'generate_content', return_value=mock_response):
            extraction = await llm_client.extract_slots("estou com dor forte no peito")
            
            assert extraction.found_emergency is True
            assert extraction.chief_complaint == "dor no peito"
            assert extraction.intensity == "10"

    @pytest.mark.asyncio
    async def test_malformed_json_handling(self, llm_client):
        """Test handling of malformed JSON from LLM."""
        mock_response = AsyncMock()
        mock_response.text = "This is not valid JSON content"
        
        with patch.object(llm_client.model, 'generate_content', return_value=mock_response):
            extraction = await llm_client.extract_slots("test message")
            
            # Should return empty extraction on error
            assert extraction.chief_complaint is None
            assert not extraction.found_emergency

    @pytest.mark.asyncio
    async def test_partial_json_extraction(self, llm_client):
        """Test extraction from partial JSON response."""
        mock_response = AsyncMock()
        mock_response.text = '''
        Aqui está a análise:
        {
            "chief_complaint": "tosse",
            "symptoms": "tosse seca",
            "duration": "1 semana",
            "found_emergency": false
        }
        Essa é minha análise.
        '''
        
        with patch.object(llm_client.model, 'generate_content', return_value=mock_response):
            extraction = await llm_client.extract_slots("tenho tosse há uma semana")
            
            assert extraction.chief_complaint == "tosse"
            assert extraction.duration == "1 semana"
            assert not extraction.found_emergency

    def test_intensity_normalization(self):
        """Test intensity value normalization."""
        test_cases = [
            ("10", "10"),
            ("dor muito forte", "dor muito forte"),  # Keep as string if not numeric
            ("8/10", "8/10"),
            ("nível 7", "nível 7"),
        ]
        
        for input_intensity, expected in test_cases:
            extraction = LLMExtraction(intensity=input_intensity)
            assert extraction.intensity == expected

    @pytest.mark.asyncio
    async def test_conversation_context_handling(self, llm_client):
        """Test extraction with conversation context."""
        mock_response = AsyncMock()
        mock_response.text = '''
        {
            "chief_complaint": "dor nas costas",
            "symptoms": "dor lombar irradiando",
            "duration": "3 dias",
            "frequency": "constante",
            "intensity": null,
            "history": "trabalho de escritório",
            "measures_taken": null,
            "found_emergency": false
        }
        '''
        
        conversation_history = [
            "user: tenho dor nas costas",
            "assistant: pode me descrever melhor?",
            "user: é uma dor que irradia para a perna"
        ]
        
        with patch.object(llm_client.model, 'generate_content', return_value=mock_response):
            extraction = await llm_client.extract_slots(
                "começou há 3 dias e trabalho muito no computador",
                conversation_history=conversation_history
            )
            
            assert extraction.chief_complaint == "dor nas costas"
            assert extraction.duration == "3 dias"
            assert extraction.history == "trabalho de escritório"

    def test_slot_field_mapping(self):
        """Test that all required slot fields are properly defined."""
        slots = TriageSlots()
        
        expected_fields = {
            "chief_complaint",
            "symptoms", 
            "duration",
            "frequency",
            "intensity",
            "history",
            "measures_taken"
        }
        
        actual_fields = set(slots.model_fields.keys())
        assert actual_fields == expected_fields

