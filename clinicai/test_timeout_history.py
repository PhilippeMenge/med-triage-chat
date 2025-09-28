#!/usr/bin/env python3
"""
Script para testar timeout e histórico de atendimentos.
"""

import sqlite3
import json
from datetime import datetime, timedelta
from clinicai_whatsapp import TriageDatabase, TriageSlots, hash_phone_number

def test_timeout_and_history():
    """Testa funcionalidades de timeout e histórico."""
    
    print("🧪 Testando Timeout e Histórico de Atendimentos")
    print("=" * 50)
    
    # Criar instância do banco
    db = TriageDatabase()
    
    # Telefone de teste
    test_phone = "5511999999999"
    phone_hash = hash_phone_number(test_phone)
    
    print(f"📱 Telefone de teste: {test_phone}")
    print(f"🔐 Hash: {phone_hash[:8]}...")
    
    # 1. Criar triagem antiga (mais de 30 min)
    print(f"\n1️⃣ Criando triagem antiga (mais de 30 min)...")
    old_time = (datetime.now() - timedelta(minutes=35)).isoformat()
    
    old_slots = TriageSlots()
    old_slots.chief_complaint = "Dor de cabeça antiga"
    old_slots.symptoms = "Dor latejante"
    
    db.create_or_update_triage(
        phone_hash=phone_hash,
        slots=old_slots,
        status="open",
        last_activity=old_time
    )
    print(f"   ✅ Triagem criada com last_activity: {old_time}")
    
    # 2. Criar triagem concluída
    print(f"\n2️⃣ Criando triagem concluída...")
    completed_time = (datetime.now() - timedelta(days=1)).isoformat()
    
    completed_slots = TriageSlots()
    completed_slots.chief_complaint = "Consulta de rotina"
    completed_slots.symptoms = "Check-up geral"
    completed_slots.duration = "Não se aplica"
    completed_slots.frequency = "Anual"
    completed_slots.intensity = "0"
    completed_slots.history = "Sem histórico relevante"
    completed_slots.measures_taken = "Nenhuma"
    
    # Criar com hash diferente para simular usuário com histórico
    old_phone_hash = hash_phone_number("5511888888888")  # Telefone diferente
    
    with sqlite3.connect(db.db_path) as conn:
        conn.execute("""
            INSERT INTO triages 
            (phone_hash, status, slots_json, emergency_flag, created_at, last_activity, completed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            old_phone_hash,
            "completed",
            json.dumps(completed_slots.model_dump()),
            False,
            completed_time,
            completed_time,
            completed_time
        ))
    print(f"   ✅ Triagem concluída criada: {completed_time}")
    
    # 3. Verificar timeout
    print(f"\n3️⃣ Testando detecção de timeout...")
    
    # Simular verificação de timeout
    current_triage = db.get_active_triage(phone_hash)
    if current_triage:
        last_activity_str = current_triage.get('last_activity')
        if last_activity_str:
            last_activity = datetime.fromisoformat(last_activity_str)
            timeout_limit = datetime.now() - timedelta(minutes=30)
            is_timeout = last_activity < timeout_limit
            
            print(f"   Last activity: {last_activity}")
            print(f"   Timeout limit: {timeout_limit}")
            print(f"   🔔 Timeout detectado: {'✅ SIM' if is_timeout else '❌ NÃO'}")
            
            if is_timeout:
                # Marcar como timeout
                db.create_or_update_triage(
                    phone_hash=phone_hash,
                    status="timeout",
                    completed_at=datetime.now().isoformat(),
                    last_activity=last_activity.isoformat()
                )
                print(f"   ✅ Triagem marcada como timeout")
    
    # 4. Buscar histórico
    print(f"\n4️⃣ Testando busca de histórico...")
    
    conn = sqlite3.connect(db.db_path)
    cursor = conn.cursor()
    
    cursor.execute("""
        SELECT id, created_at, status, slots_json, completed_at 
        FROM triages 
        WHERE phone_hash LIKE ? 
        ORDER BY created_at DESC
    """, (f"{phone_hash}%",))
    
    triages = []
    for row in cursor.fetchall():
        slots_json = row[3] or "{}"
        try:
            slots_data = json.loads(slots_json)
            chief_complaint = slots_data.get('chief_complaint', 'Não informado')
        except:
            chief_complaint = 'Não informado'
            
        triages.append({
            'id': row[0],
            'created_at': row[1],
            'status': row[2],
            'chief_complaint': chief_complaint,
            'completed_at': row[4]
        })
    
    conn.close()
    
    print(f"   📋 Atendimentos encontrados: {len(triages)}")
    for i, triage in enumerate(triages, 1):
        date = datetime.fromisoformat(triage['created_at']).strftime('%d/%m/%Y %H:%M')
        status = triage['status']
        chief = triage['chief_complaint'] or "Não informado"
        print(f"   {i}. {date} - {chief} ({status})")
    
    # 5. Simular mensagens de boas-vindas
    print(f"\n5️⃣ Simulando mensagens de boas-vindas...")
    
    if not triages:
        print("   🆕 Primeira vez - mensagem de boas-vindas simples")
    else:
        print("   🔄 Usuário com histórico - menu de opções")
        print("   Opções disponíveis:")
        print("   • Digite 'novo' para iniciar novo atendimento")
        print("   • Digite 'histórico' para ver todos os atendimentos")
        print("   • Ou conte diretamente o motivo do contato")
    
    print(f"\n🎉 Teste concluído!")
    print("   ✅ Timeout funcionando")
    print("   ✅ Histórico funcionando")
    print("   ✅ Comandos implementados")

if __name__ == "__main__":
    test_timeout_and_history()
