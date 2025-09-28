"""Tests for emergency detection functionality."""

import pytest

from clinicai.app.utils.emergency import (
    is_emergency,
    analyze_emergency_context,
    should_escalate_to_human,
    get_emergency_response,
)


class TestEmergencyDetection:
    """Test emergency detection functionality."""

    def test_emergency_keywords_detection(self):
        """Test detection of emergency keywords."""
        emergency_messages = [
            "estou com dor no peito",
            "não consigo respirar direito",
            "sinto falta de ar",
            "acho que vou desmaiar",
            "estou com sangramento intenso",
            "tive uma convulsão",
            "sinto fraqueza súbita",
            "perdi a consciência",
        ]
        
        for message in emergency_messages:
            assert is_emergency(message), f"Failed to detect emergency in: {message}"

    def test_non_emergency_messages(self):
        """Test that normal messages are not flagged as emergency."""
        normal_messages = [
            "estou com dor de cabeça",
            "sinto um pouco de cansaço",
            "tenho tosse há alguns dias",
            "dor nas costas quando acordo",
            "febre baixa ontem",
            "mal estar geral",
            "dor de barriga depois de comer",
        ]
        
        for message in normal_messages:
            assert not is_emergency(message), f"False positive for: {message}"

    def test_emergency_with_intensity(self):
        """Test emergency detection with intensity patterns."""
        intensity_messages = [
            "dor no peito nível 10",
            "dor 10/10",
            "febre 40 graus",
            "temperatura 39.5",
        ]
        
        for message in intensity_messages:
            assert is_emergency(message), f"Failed to detect high intensity: {message}"

    def test_case_insensitive_detection(self):
        """Test that detection is case insensitive."""
        cases = [
            "DOR NO PEITO",
            "Falta de Ar",
            "SANGRAMENTO INTENSO",
            "desmaio",
        ]
        
        for message in cases:
            assert is_emergency(message), f"Case sensitivity issue: {message}"

    def test_partial_matches_not_emergency(self):
        """Test that partial matches don't trigger false positives."""
        partial_messages = [
            "sem dor",
            "não tenho falta de energia",
            "descarto sangramento",
            "nunca desmaiei",
        ]
        
        for message in partial_messages:
            assert not is_emergency(message), f"False positive for partial: {message}"

    def test_emergency_context_analysis(self):
        """Test detailed emergency context analysis."""
        emergency_text = "estou com dor no peito muito forte"
        
        analysis = analyze_emergency_context(emergency_text)
        
        assert analysis["is_emergency"] is True
        assert "dor no peito" in analysis["detected_keywords"]
        assert "muito" in analysis["severity_indicators"]

    def test_empty_input(self):
        """Test handling of empty or None input."""
        assert not is_emergency("")
        assert not is_emergency(None)

    def test_escalation_logic(self):
        """Test escalation to human logic."""
        # Emergency should escalate
        assert should_escalate_to_human("dor no peito")
        
        # Normal message should not escalate
        assert not should_escalate_to_human("dor de cabeça leve")
        
        # Repeated urgency should escalate
        context = ["preciso urgente", "é urgente", "muito urgente"]
        assert should_escalate_to_human("quando posso ser atendido", context)

    def test_emergency_response_message(self):
        """Test emergency response message format."""
        response = get_emergency_response()
        
        assert "192" in response
        assert "pronto-socorro" in response.lower()
        assert "emergência" in response.lower()
        assert len(response) > 50  # Should be a substantial message

    def test_synonyms_detection(self):
        """Test detection of emergency synonyms."""
        synonym_messages = [
            "estou sufocando",
            "não consigo respirar, estou engasgado",
            "sinto queimação no peito",
            "formigamento no braço esquerdo",
            "lábios estão roxos",
        ]
        
        for message in synonym_messages:
            assert is_emergency(message), f"Failed to detect synonym: {message}"

    def test_complex_emergency_scenarios(self):
        """Test complex emergency scenarios."""
        complex_scenarios = [
            "acorda com dor forte no peito e falta de ar",
            "depois de cair, sinto fraqueza súbita e tontura",
            "vômito com sangue há 30 minutos",
            "convulsão que durou 2 minutos",
        ]
        
        for scenario in complex_scenarios:
            assert is_emergency(scenario), f"Failed complex scenario: {scenario}"

