import os
import psycopg2
from psycopg2 import sql
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()
DATABASE_CONNECTION_STRING = os.getenv("DATABASE_CONNECTION_STRING")

if not DATABASE_CONNECTION_STRING:
    print("Error: DATABASE_CONNECTION_STRING must be set in your .env file.")
    exit(1)

# Table creation statements (Postgres dialect)
table_statements = [
    'SET SEARCH_PATH TO "schneider-poc";',
    '''
    CREATE TABLE IF NOT EXISTS person (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        contact_info TEXT,
        legal_representative_id INTEGER,
        FOREIGN KEY (legal_representative_id) REFERENCES person(id)
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS "case" (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL,
        description TEXT,
        defendant_id INTEGER NOT NULL,
        plaintiff_id INTEGER NOT NULL,
        FOREIGN KEY (defendant_id) REFERENCES person(id),
        FOREIGN KEY (plaintiff_id) REFERENCES person(id)
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS note (
        id SERIAL PRIMARY KEY,
        case_id INTEGER NOT NULL,
        author_id INTEGER NOT NULL,
        note_content TEXT NOT NULL,
        timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (case_id) REFERENCES "case"(id),
        FOREIGN KEY (author_id) REFERENCES person(id)
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS document (
        id SERIAL PRIMARY KEY,
        case_id INTEGER NOT NULL,
        file_path TEXT NOT NULL,
        upload_timestamp TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (case_id) REFERENCES "case"(id)
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS tag (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) UNIQUE NOT NULL
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS case_tag (
        case_id INTEGER NOT NULL REFERENCES "case"(id) ON DELETE CASCADE,
        tag_id INTEGER NOT NULL REFERENCES tag(id) ON DELETE CASCADE,
        PRIMARY KEY (case_id, tag_id)
    );
    ''',
    '''
    CREATE TABLE IF NOT EXISTS document_tag (
        document_id INTEGER NOT NULL REFERENCES document(id) ON DELETE CASCADE,
        tag_id INTEGER NOT NULL REFERENCES tag(id) ON DELETE CASCADE,
        PRIMARY KEY (document_id, tag_id)
    );
    '''
]

# Add/alter table statement for state column
alter_case_state = '''
ALTER TABLE "schneider-poc"."case"
ADD COLUMN IF NOT EXISTS state VARCHAR(20) NOT NULL DEFAULT 'active';
'''

# Sample data
def sample_data(cur):
    cur.execute('SET SEARCH_PATH TO "schneider-poc";')

    # Delete sample data if it exists (by unique identifying values)
    # Delete notes and documents first due to foreign key constraints
    cur.execute("""
        DELETE FROM note WHERE note_content = 'Initial meeting with client.';
    """)
    cur.execute("""
        DELETE FROM document WHERE file_path = '/docs/case_a/contract.pdf';
    """)
    cur.execute("""
        DELETE FROM "case" WHERE name = 'Case A';
    """)
    cur.execute("""
        DELETE FROM person WHERE name IN ('Alice Smith', 'Bob Johnson', 'Carol Lawyer');
    """)

    # Insert persons
    cur.execute("""
        INSERT INTO person (name, contact_info) VALUES
        ('Alice Smith', 'alice@example.com'),
        ('Bob Johnson', 'bob@example.com'),
        ('Carol Lawyer', 'carol.lawyer@example.com')
        RETURNING id;
    """)
    person_ids = [row[0] for row in cur.fetchall()]

    # Set legal representative for Alice and Bob
    cur.execute("UPDATE person SET legal_representative_id = %s WHERE id = %s;", (person_ids[2], person_ids[0]))
    cur.execute("UPDATE person SET legal_representative_id = %s WHERE id = %s;", (person_ids[2], person_ids[1]))

    # Insert case
    cur.execute("""
        INSERT INTO "case" (name, description, defendant_id, plaintiff_id, state) VALUES
        ('Case A', 'A sample legal case.', %s, %s, 'active')
        RETURNING id;
    """, (person_ids[0], person_ids[1]))
    case_id = cur.fetchone()[0]

    # Insert note
    cur.execute("""
        INSERT INTO note (case_id, author_id, note_content, timestamp) VALUES
        (%s, %s, %s, %s)
        RETURNING id;
    """, (case_id, person_ids[2], 'Initial meeting with client.', datetime.now()))
    note_id = cur.fetchone()[0]

    # Insert document
    cur.execute("""
        INSERT INTO document (case_id, file_path, upload_timestamp) VALUES
        (%s, %s, %s)
        RETURNING id;
    """, (case_id, '/docs/case_a/contract.pdf', datetime.now()))
    document_id = cur.fetchone()[0]

    return {
        'person_ids': person_ids,
        'case_id': case_id,
        'note_id': note_id,
        'document_id': document_id
    }

def main():
    try:
        with psycopg2.connect(DATABASE_CONNECTION_STRING) as conn:
            with conn.cursor() as cur:
                # Create tables
                for stmt in table_statements:
                    cur.execute(stmt)
                # Add state column if not exists
                cur.execute(alter_case_state)
                conn.commit()
                print("Tables created or verified.")

                # Insert sample data
                ids = sample_data(cur)
                conn.commit()
                print("Sample data inserted:")
                print(ids)

                # Print out the data
                cur.execute('SELECT * FROM person;')
                print("\nPersons:", cur.fetchall())
                cur.execute('SELECT * FROM "case";')
                print("\nCases:", cur.fetchall())
                cur.execute('SELECT * FROM note;')
                print("\nNotes:", cur.fetchall())
                cur.execute('SELECT * FROM document;')
                print("\nDocuments:", cur.fetchall())

    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main() 