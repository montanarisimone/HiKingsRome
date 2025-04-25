#!/usr/bin/env python3
import sqlite3
import json
import os
import re
import time
import threading
from functools import wraps

# Timeout configurabile per le query (in secondi)
QUERY_TIMEOUT = 5
# Limite di righe massime per i risultati
MAX_ROWS = 200

class TimeoutError(Exception):
    """Eccezione sollevata quando una query impiega troppo tempo"""
    pass

def timeout(seconds):
    """Decoratore per impostare un timeout su una funzione"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            result = [TimeoutError('Query timeout')]
            
            def target():
                try:
                    result[0] = func(*args, **kwargs)
                except Exception as e:
                    result[0] = e
            
            thread = threading.Thread(target=target)
            thread.daemon = True
            thread.start()
            thread.join(seconds)
            
            if isinstance(result[0], Exception):
                raise result[0]
            return result[0]
        return wrapper
    return decorator

class DBQueryUtils:
    """Utility class for executing database queries for admin purposes"""
    
    # File per salvare le query predefinite
    CUSTOM_QUERIES_FILE = 'admin_custom_queries.json'
    
    @staticmethod
    def get_connection():
        """Get a connection to the SQLite database"""
        db_path = 'hiky_bot.db'
        if not os.path.exists(db_path):
            raise FileNotFoundError(f"Database file {db_path} not found.")
        
        conn = sqlite3.connect(db_path)
        # Configure to return rows as dictionaries
        conn.row_factory = sqlite3.Row
        return conn
    
    @staticmethod
    def is_select_query(query):
        """Verifica che la query sia di tipo SELECT e non contenga altre operazioni DML"""
        # Rimuovi commenti e spazi bianchi per una migliore analisi
        clean_query = re.sub(r'--.*?\n', ' ', query)
        clean_query = re.sub(r'/\*.*?\*/', ' ', clean_query, flags=re.DOTALL)
        clean_query = clean_query.strip().lower()
        
        # Verifica che inizi con SELECT
        if not clean_query.startswith('select'):
            return False
        
        # Verifica che non contenga parole chiave DML proibite
        forbidden_keywords = [
            'insert', 'update', 'delete', 'drop', 'alter', 'create', 
            'pragma', 'attach', 'detach', 'vacuum'
        ]
        
        # Pattern per individuare parole intere
        for keyword in forbidden_keywords:
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, clean_query):
                return False
        
        return True
    
    @staticmethod
    @timeout(QUERY_TIMEOUT)
    def execute_query(query, params=None):
        """Execute a database query with timeout and row limit"""
        if not DBQueryUtils.is_select_query(query):
            return {
                'success': False,
                'error': 'Solo query SELECT sono permesse per motivi di sicurezza.'
            }
        
        conn = None
        try:
            conn = DBQueryUtils.get_connection()
            cursor = conn.cursor()
            
            start_time = time.time()
            
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            # Fetch rows with limit
            rows = cursor.fetchmany(MAX_ROWS + 1)  # Fetch one more to check if we hit the limit
            
            hit_limit = len(rows) > MAX_ROWS
            if hit_limit:
                rows = rows[:MAX_ROWS]  # Truncate to limit
            
            # Get column names
            column_names = [description[0] for description in cursor.description]
            
            # Convert rows to list of dicts
            result_rows = []
            for row in rows:
                result_rows.append({column: row[column] for column in column_names})
            
            execution_time = time.time() - start_time
            
            return {
                'success': True,
                'rows': result_rows,
                'column_names': column_names,
                'row_count': len(result_rows),
                'hit_limit': hit_limit,
                'execution_time': execution_time
            }
        
        except sqlite3.Error as e:
            return {
                'success': False,
                'error': f"SQLite error: {str(e)}"
            }
        finally:
            if conn:
                conn.close()
    
    @staticmethod
    def get_all_tables():
        """Get a list of all tables in the database"""
        query = """
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name
        """
        return DBQueryUtils.execute_query(query)
    
    @staticmethod
    def get_future_hikes():
        """Get a list of upcoming hikes"""
        query = """
        SELECT 
            h.id, h.hike_name, h.hike_date, h.max_participants, h.difficulty,
            h.latitude, h.longitude, h.is_active,
            (SELECT COUNT(*) FROM registrations r WHERE r.hike_id = h.id) as current_participants
        FROM hikes h
        WHERE h.hike_date >= date('now')
        ORDER BY h.hike_date ASC
        """
        return DBQueryUtils.execute_query(query)
    
    @staticmethod
    def get_all_users():
        """Get a list of all users"""
        query = """
        SELECT * FROM users
        ORDER BY registration_timestamp DESC
        """
        return DBQueryUtils.execute_query(query)
    
    @staticmethod
    def load_custom_queries():
        """Load custom queries from file"""
        if not os.path.exists(DBQueryUtils.CUSTOM_QUERIES_FILE):
            return []
        
        try:
            with open(DBQueryUtils.CUSTOM_QUERIES_FILE, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return []
        except FileNotFoundError:
            return []
    
    @staticmethod
    def save_custom_query(name, query):
        """Save a custom query to the file"""
        custom_queries = DBQueryUtils.load_custom_queries()
        
        # Check if query with this name already exists
        for existing_query in custom_queries:
            if existing_query.get('name') == name:
                existing_query['query'] = query
                break
        else:
            # Add new query
            custom_queries.append({
                'name': name,
                'query': query
            })
        
        # Save to file
        with open(DBQueryUtils.CUSTOM_QUERIES_FILE, 'w') as f:
            json.dump(custom_queries, f, indent=2)
        
        return True
    
    @staticmethod
    def delete_custom_query(name):
        """Delete a custom query from the file"""
        custom_queries = DBQueryUtils.load_custom_queries()
        custom_queries = [q for q in custom_queries if q.get('name') != name]
        
        # Save to file
        with open(DBQueryUtils.CUSTOM_QUERIES_FILE, 'w') as f:
            json.dump(custom_queries, f, indent=2)
        
        return True
