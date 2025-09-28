#!/usr/bin/env python3
"""
Script para limpar bancos de dados.
"""

import sqlite3
import os

def clean_databases():
    """Limpa todos os bancos de dados."""
    
    # Limpar clinicai.db
    if os.path.exists('clinicai.db'):
        print('🔧 Limpando clinicai.db...')
        conn = sqlite3.connect('clinicai.db')
        cursor = conn.cursor()
        
        # Verificar tabelas existentes
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = cursor.fetchall()
        print(f'   Tabelas encontradas: {[t[0] for t in tables]}')
        
        # Limpar cada tabela
        for table in tables:
            table_name = table[0]
            try:
                cursor.execute(f'DELETE FROM {table_name}')
                print(f'   ✅ Tabela {table_name} limpa')
            except Exception as e:
                print(f'   ⚠️ Erro limpando {table_name}: {e}')
        
        conn.commit()
        conn.close()
        print('✅ clinicai.db limpo!')
    else:
        print('📄 clinicai.db não encontrado')
    
    # Remover triage_data.db
    if os.path.exists('triage_data.db'):
        os.remove('triage_data.db')
        print('✅ triage_data.db removido!')
    else:
        print('📄 triage_data.db não encontrado')
    
    print('\n🎉 Limpeza concluída!')
    print('   Todos os dados de triagem foram removidos.')
    print('   O sistema está pronto para novos testes.')

if __name__ == "__main__":
    clean_databases()
