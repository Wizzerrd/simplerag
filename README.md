```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r <(tr ',' '\n' < requirements.txt)
sudo apt-get update
sudo apt-get install postgresql postgresql-server-dev-all
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
sudo make install
cd ..
sudo service postgresql start
sudo -u postgres psql
```

```sql
CREATE EXTENSION vector;
CREATE DATABASE rag_db;
\c rag_db
CREATE TABLE documents (
    id SERIAL PRIMARY KEY,
    content TEXT,
    embedding VECTOR(1536) -- Adjust size based on your embedding dimension
);
```